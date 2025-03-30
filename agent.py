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
    provider="novita",
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
        
        print(f"Starting chess process with command: {' '.join(cmd)}")
        
        # Start the chess process
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Get initial output including game ID with timeout protection
        output = ""
        start_time = time.time()
        timeout = 20  # 20 seconds timeout
        
        # First check if the process started correctly
        if self.process.poll() is not None:
            error = self.process.stderr.read()
            raise RuntimeError(f"Chess process failed to start: Exit code {self.process.returncode}, Error: {error}")
        
        print("Chess process started, waiting for initial output...")
        
        # Variables to track readiness indicators
        game_id_found = False
        
        # Read output with timeout
        while time.time() - start_time < timeout:
            # Check if there's data available to read (non-blocking)
            import select
            readable, _, _ = select.select([self.process.stdout], [], [], 0.5)
            
            if readable:
                line = self.process.stdout.readline()
                if not line:  # EOF
                    break
                    
                print(f"Read line: {line.strip()}")
                output += line
                
                # Extract game ID
                if "New game started with ID:" in line:
                    self.game_id = line.split("ID:")[1].strip()
                    game_id_found = True
                    # After finding the game ID, wait a bit and then send a newline to get the board
                    time.sleep(1)
                    self._send_command("")
                
                # Check for board output (looking for chess board pattern)
                if any(rank_indicator in line for rank_indicator in [' 8 ', ' 7 ', ' 6 ', ' 5 ', ' 4 ', ' 3 ', ' 2 ', ' 1 ']):
                    print("Found board pattern!")
                
                # If we've reached the prompt, we can stop reading
                if "Your move" in line or "Enter moves in UCI format" in line:
                    print("Found prompt for move input!")
                    break
            
            # If we've found the game ID and waited enough time, force continuing
            if game_id_found and time.time() - start_time > 5:  # Wait at least 5 seconds to collect output
                print("Found game ID - assuming game is ready for initial output.")
                break
            
            # Check if process is still running
            if self.process.poll() is not None:
                error = self.process.stderr.read()
                raise RuntimeError(f"Chess process exited unexpectedly: Exit code {self.process.returncode}, Error: {error}")
        
        # Check if we timed out
        if not game_id_found and time.time() - start_time >= timeout:
            self.process.terminate()
            raise TimeoutError(f"Timed out waiting for chess process initial output. Last output: {output}")
        
        print("Initial chess output received, parsing board state...")
        # Parse the initial board state
        self._parse_output(output)
    
    def load_game(self, save_file: str, autosave: bool = True) -> None:
        """Load a saved chess game."""
        cmd = [sys.executable, self.chess_script_path, "--load", save_file]
        if autosave:
            cmd.append("--autosave")
        
        print(f"Loading chess game with command: {' '.join(cmd)}")
            
        # Start the chess process
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Get initial output with timeout protection
        output = ""
        start_time = time.time()
        timeout = 20  # 20 seconds timeout
        
        # First check if the process started correctly
        if self.process.poll() is not None:
            error = self.process.stderr.read()
            raise RuntimeError(f"Chess process failed to start: Exit code {self.process.returncode}, Error: {error}")
        
        print("Chess process started, waiting for initial output...")
        
        # Variables to track readiness indicators
        game_id_found = False
        
        # Read output with timeout
        while time.time() - start_time < timeout:
            # Check if there's data available to read (non-blocking)
            import select
            readable, _, _ = select.select([self.process.stdout], [], [], 0.5)
            
            if readable:
                line = self.process.stdout.readline()
                if not line:  # EOF
                    break
                    
                print(f"Read line: {line.strip()}")
                output += line
                
                # Extract game ID
                if "Loaded game with ID:" in line:
                    self.game_id = line.split("ID:")[1].strip()
                    game_id_found = True
                    # After finding the game ID, wait a bit and then send a newline to get the board
                    time.sleep(1)
                    self._send_command("")
                
                # Check for board output (looking for chess board pattern)
                if any(rank_indicator in line for rank_indicator in [' 8 ', ' 7 ', ' 6 ', ' 5 ', ' 4 ', ' 3 ', ' 2 ', ' 1 ']):
                    print("Found board pattern!")
                
                # If we've reached the prompt, we can stop reading
                if "Your move" in line or "Enter moves in UCI format" in line:
                    print("Found prompt for move input!")
                    break
            
            # If we've found the game ID and waited enough time, force continuing
            if game_id_found and time.time() - start_time > 5:  # Wait at least 5 seconds to collect output
                print("Found game ID - assuming game is ready for initial output.")
                break
            
            # Check if process is still running
            if self.process.poll() is not None:
                error = self.process.stderr.read()
                raise RuntimeError(f"Chess process exited unexpectedly: Exit code {self.process.returncode}, Error: {error}")
        
        # Check if we timed out
        if not game_id_found and time.time() - start_time >= timeout:
            self.process.terminate()
            raise TimeoutError(f"Timed out waiting for chess process initial output. Last output: {output}")
        
        print("Initial chess output received, parsing board state...")
        # Parse the initial board state
        self._parse_output(output)
    
    def _parse_output(self, output: str) -> None:
        """Parse the chess game output to extract board state and other information."""
        # Extract the board representation (8x8 grid with pieces)
        # More flexible pattern that can capture board states with variations in formatting
        board_lines = []
        lines = output.split('\n')
        rank_indicators = [' 8 ', ' 7 ', ' 6 ', ' 5 ', ' 4 ', ' 3 ', ' 2 ', ' 1 ']
        
        # First try to find consecutive board lines
        for i in range(len(lines)):
            if any(rank_indicator in lines[i] for rank_indicator in rank_indicators):
                # Found a potential board line, check if we have 8 consecutive board lines
                if i + 7 < len(lines):
                    potential_board = lines[i:i+8]
                    if all(any(rank in line for rank in rank_indicators) for line in potential_board):
                        board_lines = potential_board
                        # Add the file coordinates line if it exists
                        if i + 8 < len(lines) and 'a b c d e f g h' in lines[i+8]:
                            board_lines.append(lines[i+8])
                        break
        
        # If we found the board, join it back together
        if board_lines:
            self.board_state = '\n'.join(board_lines)
        else:
            # Fallback to older regex pattern if we couldn't find consecutive board lines
            board_pattern = r' 8 .*\n 7 .*\n 6 .*\n 5 .*\n 4 .*\n 3 .*\n 2 .*\n 1 .*\n.*a b c d e f g h'
            board_match = re.search(board_pattern, output, re.DOTALL)
            if board_match:
                self.board_state = board_match.group(0)
        
        # Extract turn information - more flexible pattern
        turn_match = re.search(r'(Current turn|Turn)[:\s]*(White|Black)', output, re.IGNORECASE)
        if turn_match:
            self.turn = turn_match.group(2)
        
        # Extract evaluation - more flexible pattern
        eval_match = re.search(r'Evaluation:?\s*([+-]?[\d.]+|\+∞|-∞)', output)
        if eval_match:
            eval_str = eval_match.group(1)
            if eval_str == "+∞":
                self.evaluation = float('inf')
            elif eval_str == "-∞":
                self.evaluation = float('-inf')
            else:
                try:
                    self.evaluation = float(eval_str)
                except ValueError:
                    print(f"Warning: Could not convert evaluation value '{eval_str}' to float")
        
        # Check if in check - more flexible pattern
        self.in_check = "CHECK" in output.upper()
        
        # Check if game is over - more flexible pattern
        self.game_over = "Game over" in output or "checkmate" in output.lower()
        
        # Extract valid moves if they're in the output
        # First try the expected format
        if "Valid moves:" in output:
            moves_section = output.split("Valid moves:")[1]
            if "Total legal moves:" in moves_section:
                moves_section = moves_section.split("Total legal moves:")[0]
            
            self.valid_moves = []
            for line in moves_section.strip().split('\n'):
                if "→" in line:
                    try:
                        piece_info, destinations = line.split("→")
                        # Extract the from square by finding "at X" in the piece info
                        from_match = re.search(r'at\s+([a-h][1-8])', piece_info)
                        if from_match:
                            from_square = from_match.group(1)
                            # Extract all destination squares
                            to_squares = re.findall(r'([a-h][1-8])', destinations)
                            for to_square in to_squares:
                                self.valid_moves.append(f"{from_square}{to_square}")
                    except Exception as e:
                        print(f"Error parsing move line '{line}': {str(e)}")
        
        # If we couldn't find moves in the expected format, try a more general approach
        if not self.valid_moves:
            # Look for patterns that look like UCI moves (e.g., e2e4)
            uci_moves = re.findall(r'\b([a-h][1-8][a-h][1-8][qrbnQRBN]?)\b', output)
            if uci_moves:
                self.valid_moves = uci_moves
    
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
        """Read output from the chess process until a new prompt appears, with timeout."""
        output = ""
        start_time = time.time()
        timeout = 15  # 15 seconds timeout
        
        board_pattern_found = False
        
        while time.time() - start_time < timeout:
            # Check if there's data available to read (non-blocking)
            import select
            readable, _, _ = select.select([self.process.stdout], [], [], 0.5)
            
            if readable:
                line = self.process.stdout.readline()
                if not line:  # EOF
                    break
                
                output += line
                
                # Check for board output (looking for chess board pattern)
                if any(rank_indicator in line for rank_indicator in [' 8 ', ' 7 ', ' 6 ', ' 5 ', ' 4 ', ' 3 ', ' 2 ', ' 1 ']):
                    board_pattern_found = True
                
                # If we've reached a prompt, we can stop reading
                if "Your move" in line or "Enter moves in UCI format" in line or "Game over" in line:
                    return output
            
            # If we've found a board representation and collected a reasonable amount of output,
            # we can consider the response complete after a certain amount of time with no output
            if board_pattern_found and len(output) > 100 and time.time() - start_time > 5:
                return output
            
            # Check if process is still running
            if self.process.poll() is not None:
                error = self.process.stderr.read() if self.process.stderr else "No error output available"
                print(f"Chess process exited unexpectedly: {error}")
                return output
        
        # If we get here, we timed out
        print(f"Warning: Timed out waiting for prompt after {timeout} seconds")
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
        #TODO: update model to new deepseek v3
        completion = client.chat.completions.create(
            model = "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=100,
        )
        return completion.choices[0].message.content

    def _parse_llm_chess_move(self, llm_output: str) -> str:
        valid_moves = self.get_valid_moves()
        lines = llm_output.strip().split('\n')
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
        return self._parse_llm_chess_move(response)
    
    def play_game(self, moves_limit: int = 50) -> None:
        """
        Play a chess game with the LLM making moves as White.
        
        Args:
            moves_limit: Maximum number of moves to make
        """
        move_count = 0
        
        # First parse the output to get the current state
        # Important: We need to know whose turn it is (White or Black)
        if not self.turn:
            # Ensure we've parsed the state at least once
            output = self._read_until_prompt()
            self._parse_output(output)
        
        while not self.game_over and move_count < moves_limit:
            # Check whose turn it is
            if self.turn.lower() == "black":
                # Wait for computer's move to complete
                print("Waiting for computer (Black) to move...")
                output = self._read_until_prompt()
                self._parse_output(output)
                continue
                
            # Generate and make a move as White
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
    import argparse
    
    # Set up command line arguments
    arg_parser = argparse.ArgumentParser(description="LLM Chess Agent")
    arg_parser.add_argument("--chess", default="./chess_game.py", help="Path to chess game script")
    arg_parser.add_argument("--load", help="Load a saved game file")
    arg_parser.add_argument("--no-autosave", action="store_true", help="Disable auto-saving")
    arg_parser.add_argument("--moves", type=int, default=3, help="Maximum number of moves to play")
    arg_parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = arg_parser.parse_args()
    
    # Create the agent
    agent = ChessLLMAgent(args.chess)
    
    try:
        if args.load:
            print(f"Loading chess game from: {args.load}")
            agent.load_game(args.load, autosave=not args.no_autosave)
        else:
            print("Starting a new chess game...")
            agent.start_new_game(autosave=not args.no_autosave)
        
        # Play the game
        agent.play_game(moves_limit=args.moves)
        
    except Exception as e:
        import traceback
        print(f"Error: {str(e)}")
        if args.debug:
            traceback.print_exc()
    finally:
        # Make sure to close the process
        try:
            agent.close()
        except Exception as close_error:
            print(f"Error during cleanup: {str(close_error)}")
