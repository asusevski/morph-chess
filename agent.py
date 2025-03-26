import subprocess
import re
import os
import time
import sys
import json
from typing import Dict, Any, Tuple, List, Optional
import requests
from huggingface_hub import InferenceClient
import os
import random


client = InferenceClient(
    provider="fireworks-ai",
    api_key=os.environ["HF_API_KEY"],
)


class ChessLLMAgent:
    def __init__(self, chess_script_path: str):
        """
        Initialize the LLM chess agent.
        
        Args:
            chess_script_path: Path to the chess game Python script
        """
        self.chess_script_path = chess_script_path
        self.game_id = None
        self.process = None
        self.board_state = ""
        self.evaluation = 0.0
        self.turn = ""
        self.in_check = False
        self.game_over = False
        self.valid_moves = []
    
    def start_new_game(self, autosave: bool = True) -> None:
        """Start a new chess game process with optional autosave."""
        cmd = [sys.executable, self.chess_script_path]
        if autosave:
            cmd.append("--autosave")
        
        # Start the chess process
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Get initial output including game ID
        output = ""
        while "Your move" not in output and not self.process.poll():
            line = self.process.stdout.readline()
            output += line
            
            # Extract game ID
            if "New game started with ID:" in line:
                self.game_id = line.split("ID:")[1].strip()
                
        # Parse the initial board state
        self._parse_output(output)
    
    def load_game(self, save_file: str, autosave: bool = True) -> None:
        """Load a saved chess game."""
        cmd = [sys.executable, self.chess_script_path, "--load", save_file]
        if autosave:
            cmd.append("--autosave")
            
        # Start the chess process
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Get initial output
        output = ""
        while "Your move" not in output and not self.process.poll():
            line = self.process.stdout.readline()
            output += line
            
            # Extract game ID
            if "Loaded game with ID:" in line:
                self.game_id = line.split("ID:")[1].strip()
                
        # Parse the initial board state
        self._parse_output(output)
    
    def _parse_output(self, output: str) -> None:
        """Parse the chess game output to extract board state and other information."""
        # Extract the board representation (8x8 grid with pieces)
        board_pattern = r' 8 .*\n 7 .*\n 6 .*\n 5 .*\n 4 .*\n 3 .*\n 2 .*\n 1 .*\n    a b c d e f g h'
        board_match = re.search(board_pattern, output)
        if board_match:
            self.board_state = board_match.group(0)
        
        # Extract turn information
        turn_match = re.search(r'Current turn: (White|Black)', output)
        if turn_match:
            self.turn = turn_match.group(1)
        
        # Extract evaluation
        eval_match = re.search(r'Evaluation: ([+-]?[\d.]+|\+∞|-∞)', output)
        if eval_match:
            eval_str = eval_match.group(1)
            if eval_str == "+∞":
                self.evaluation = float('inf')
            elif eval_str == "-∞":
                self.evaluation = float('-inf')
            else:
                self.evaluation = float(eval_str)
        
        # Check if in check
        self.in_check = "is in CHECK" in output
        
        # Check if game is over
        self.game_over = "Game over" in output
        
        # Extract valid moves if they're in the output
        if "Valid moves:" in output:
            moves_section = output.split("Valid moves:")[1].split("Total legal moves:")[0]
            self.valid_moves = []
            for line in moves_section.strip().split('\n'):
                if "→" in line:
                    piece_info, destinations = line.split("→")
                    from_square = piece_info.strip().split("at")[1].strip()
                    to_squares = [sq.strip() for sq in destinations.strip().split(',')]
                    for to_square in to_squares:
                        self.valid_moves.append(f"{from_square}{to_square}")
    
    def get_valid_moves(self) -> List[str]:
        """Get a list of valid moves in UCI format."""
        # Send 'moves' command to the chess process
        self._send_command("moves")
        output = self._read_until_prompt()
        self._parse_output(output)
        return self.valid_moves
    
    def _send_command(self, command: str) -> None:
        """Send a command to the chess process."""
        if self.process and self.process.poll() is None:
            self.process.stdin.write(f"{command}\n")
            self.process.stdin.flush()
    
    def _read_until_prompt(self) -> str:
        """Read output from the chess process until a new prompt appears."""
        output = ""
        while True:
            line = self.process.stdout.readline()
            output += line
            if "Your move" in line or "Game over" in line:
                break
        return output
    
    def make_move(self, move: str) -> Tuple[bool, str]:
        """
        Make a chess move.
        
        Args:
            move: Move in UCI format (e.g., "e2e4")
            
        Returns:
            (success, output): Whether move was successful and the output
        """
        if self.game_over:
            return False, "Game is already over"
        
        # Send the move to the chess process
        self._send_command(move)
        
        # Read output until we get a new prompt or game ends
        output = self._read_until_prompt()
        self._parse_output(output)
        
        # Check if move was successful
        if "Error" in output:
            return False, output
        
        # Read computer's move response if it's in the output
        computer_move = None
        if "Computer's move:" in output:
            computer_move_match = re.search(r"Computer's move: (\w+)", output)
            if computer_move_match:
                computer_move = computer_move_match.group(1)
        
        return True, output
    
    def query_llm(self, prompt: str) -> str:
        """
        Query the LLM for a chess move.
        
        Args:
            prompt: Prompt describing the current board state and requesting a move
            
        Returns:
            String containing the LLM's response
        """
        completion = client.chat.completions.create(
            model="deepseek-ai/DeepSeek-V3-0324",
            messages=[
                {
                    "role": "user",
                    "content": "What is the capital of France?"
                }
            ],
            max_tokens=100,
        )
        return completion.choices[0].message.content
    
    def generate_chess_move(self) -> str:
        """
        Generate a chess move using the LLM based on current board state.
        
        Returns:
            Move in UCI format (e.g., "e2e4")
        """
        # Get valid moves
        valid_moves = self.get_valid_moves()
        
        # Create a prompt for the LLM
        prompt = f"""
You are playing chess as White. Your goal is to choose the best move.

Current board state:
{self.board_state}

Current evaluation: {self.evaluation}
{"You are in CHECK!" if self.in_check else ""}

Valid moves (in UCI format):
{', '.join(valid_moves)}

Analyze the position and recommend a single move in UCI format (e.g., "e2e4").
Think about tactics, piece development, king safety, and current material balance.
First explain your reasoning, then provide ONLY the UCI notation for your chosen move on the final line.
"""
        # Query the LLM
        # TODO: structured output for valid moves with better error handling
        response = self.query_llm(prompt)
        
        # Extract the move from the response (assuming the move is on the last line)
        lines = response.strip().split('\n')
        last_line = lines[-1].strip()
        
        # Look for a valid move format in the last line (a valid UCI move is 4-5 characters)
        move_match = re.search(r'\b([a-h][1-8][a-h][1-8][qrbnQRBN]?)\b', last_line)
        if move_match:
            move = move_match.group(1)
            return move
        
        # If no clear move found, try to find it elsewhere in the response
        for line in reversed(lines):
            move_match = re.search(r'\b([a-h][1-8][a-h][1-8][qrbnQRBN]?)\b', line)
            if move_match:
                return move_match.group(1)
        
        # If still no move found, fall back to a random valid move
        if valid_moves:
            return random.choice(valid_moves)
        
        return ""
    
    def play_game(self, moves_limit: int = 50) -> None:
        """
        Play a chess game with the LLM making moves as White.
        
        Args:
            moves_limit: Maximum number of moves to make
        """
        move_count = 0
        
        while not self.game_over and move_count < moves_limit:
            # Generate and make a move
            move = self.generate_chess_move()
            print(f"LLM's move: {move}")
            success, output = self.make_move(move)
            
            if not success:
                print(f"Failed to make move: {output}")
                # Ask for valid moves and try again
                self.get_valid_moves()
                continue
            
            move_count += 1
            print(f"Move {move_count} completed")
            
            # Brief pause to make it easier to follow
            time.sleep(1)
        
        print("Game finished!")
        if self.game_over:
            print("Game ended naturally")
        else:
            print(f"Game ended after {moves_limit} moves")
    
    def close(self) -> None:
        """Close the chess process."""
        if self.process and self.process.poll() is None:
            self._send_command("quit")
            self.process.wait(timeout=5)

# Example usage
if __name__ == "__main__":
    # Path to your chess script
    CHESS_SCRIPT = "./chess_game.py"
    
    # Create the agent
    agent = ChessLLMAgent(CHESS_SCRIPT)
    
    # Start a new game
    print("Starting a new chess game...")
    agent.start_new_game()
    
    # Play the game
    try:
        agent.play_game(moves_limit=3)
    finally:
        # Make sure to close the process
        agent.close()
