import chess
import uuid
import json
import os
from datetime import datetime

class ChessEngine:
    """
    A chess engine that maintains game state and provides methods for gameplay.
    """
    def __init__(self, load_path=None, autosave=True, autosave_dir="chess_autosaves"):
        """
        Initialize a new chess engine.
        
        Args:
            load_path (str): Path to a saved game to load
            autosave (bool): Whether to automatically save the game after moves
            autosave_dir (str): Directory for autosave files
        """
        # Create save directory if it doesn't exist
        self.autosave_dir = autosave_dir
        if not os.path.exists(self.autosave_dir):
            os.makedirs(self.autosave_dir)
            
        self.autosave = autosave
        self.move_timestamps = {}
        
        # Either load a game or start a new one
        if load_path:
            self._load_game(load_path)
        else:
            self.board = chess.Board()
            self.game_id = str(uuid.uuid4())
        
        # Set up autosave path
        self.autosave_path = os.path.join(self.autosave_dir, f"game_id_{self.game_id}.json")
    
    def make_move(self, move_uci):
        """
        Make a move on the chess board using UCI notation.
        
        Args:
            move_uci (str): The move in UCI notation (e.g., "e2e4", "g1f3")
            
        Returns:
            bool: Whether the move was successful
            
        Raises:
            ValueError: If the move is not valid UCI notation
            IllegalMoveError: If the move is illegal on the current board
        """
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            raise ValueError(f"Invalid UCI notation: {move_uci}")
            
        if move not in self.board.legal_moves:
            raise IllegalMoveError(f"Illegal move: {move_uci}")
        
        # Make the move
        self.board.push(move)
        
        # Record timestamp for this move
        self.move_timestamps[len(self.board.move_stack)] = datetime.now().isoformat()
        
        # Auto-save if enabled
        if self.autosave:
            self.save_game()
        
        return True
    
    def make_computer_move(self):
        """
        Make a random move for the computer (Black).
        
        Returns:
            str: The move made, in UCI format
            
        Raises:
            ValueError: If there are no legal moves available
        """
        if not self.is_computer_turn():
            return None
            
        legal_moves = list(self.board.legal_moves)
        if not legal_moves:
            raise ValueError("No legal moves available")
        
        import random
        random_move = random.choice(legal_moves)
        self.board.push(random_move)
        
        # Record timestamp for this move
        self.move_timestamps[len(self.board.move_stack)] = datetime.now().isoformat()
        
        # Auto-save if enabled
        if self.autosave:
            self.save_game()
        
        return random_move.uci()
    
    def is_computer_turn(self):
        """
        Check if it's the computer's turn (Black).
        
        Returns:
            bool: True if it's the computer's turn, False otherwise
        """
        return self.board.turn == chess.BLACK
    
    def get_valid_moves(self):
        """
        Get a list of valid moves in UCI format.
        
        Returns:
            list: List of valid moves in UCI format
        """
        return [move.uci() for move in self.board.legal_moves]
    
    def save_game(self, filepath=None):
        """
        Save the current game state to a file.
        
        Args:
            filepath (str, optional): Custom filepath. If None, uses autosave path.
        
        Returns:
            str: Path to the saved game file
        """
        if filepath is None:
            filepath = self.autosave_path
        
        # Convert move timestamps keys to strings for JSON serialization
        string_move_timestamps = {str(k): v for k, v in self.move_timestamps.items()}
        
        game_data = {
            "game_id": self.game_id,
            "fen": self.board.fen(),
            "move_history": [move.uci() for move in self.board.move_stack],
            "move_timestamps": string_move_timestamps,
            "last_updated": datetime.now().isoformat()
        }
        
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(game_data, f, indent=2)
        
        return filepath
    
    def _load_game(self, filepath):
        """
        Load a saved game from a file.
        
        Args:
            filepath (str): Path to the saved game file
        
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file contains invalid game data
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Game file not found: {filepath}")
        
        with open(filepath, 'r') as f:
            try:
                game_data = json.load(f)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid game file format: {filepath}")
        
        # Validate required fields
        required_fields = ["game_id", "fen"]
        for field in required_fields:
            if field not in game_data:
                raise ValueError(f"Missing required field in game file: {field}")
        
        # Create board from FEN
        try:
            self.board = chess.Board(game_data["fen"])
        except ValueError as e:
            raise ValueError(f"Invalid FEN in game file: {str(e)}")
        
        # Set game ID
        self.game_id = game_data["game_id"]
        
        # Extract move timestamps (convert keys back to integers)
        self.move_timestamps = {}
        if "move_timestamps" in game_data:
            self.move_timestamps = {int(k): v for k, v in game_data["move_timestamps"].items()}
        
        # Optionally replay moves
        if "move_history" in game_data:
            # Clear the move stack first (since we loaded from FEN)
            self.board.clear_stack()
            # Replay each move
            for move_uci in game_data["move_history"]:
                try:
                    move = chess.Move.from_uci(move_uci)
                    if move in self.board.legal_moves:
                        self.board.push(move)
                    else:
                        # If we encounter an illegal move in history, stop replaying
                        # but keep the board state from the valid moves
                        break
                except ValueError:
                    # Skip invalid UCI strings
                    continue
    
    def is_game_over(self):
        """
        Check if the game is over and return the result.
        
        Returns:
            dict: A dictionary containing game status information:
                - 'is_over': Boolean indicating if the game is over
                - 'result': The result of the game as a string ("1-0", "0-1", "1/2-1/2", or None)
                - 'reason': The reason why the game is over (checkmate, stalemate, etc.)
        """
        result = {
            'is_over': self.board.is_game_over(),
            'result': None,
            'reason': None
        }
        
        if result['is_over']:
            if self.board.is_checkmate():
                result['reason'] = 'checkmate'
                result['result'] = "0-1" if self.board.turn == chess.WHITE else "1-0"
            elif self.board.is_stalemate():
                result['reason'] = 'stalemate'
                result['result'] = "1/2-1/2"
            elif self.board.is_insufficient_material():
                result['reason'] = 'insufficient material'
                result['result'] = "1/2-1/2"
            elif self.board.is_fifty_moves():
                result['reason'] = 'fifty-move rule'
                result['result'] = "1/2-1/2"
            elif self.board.is_repetition():
                result['reason'] = 'threefold repetition'
                result['result'] = "1/2-1/2"
                
        return result
    
    def get_current_turn(self):
        """
        Get the current turn.
        
        Returns:
            str: "White" or "Black"
        """
        return "White" if self.board.turn == chess.WHITE else "Black"
    
    def is_in_check(self):
        """
        Check if the current player is in check.
        
        Returns:
            bool: True if in check, False otherwise
        """
        return self.board.is_check()
    
    def evaluate_position(self):
        """
        Calculate a simple evaluation of the current board position.
        Positive values favor white, negative values favor black.
        
        Returns:
            float: Evaluation score (positive favors white, negative favors black)
        """
        # Piece values (standard chess values)
        piece_values = {
            chess.PAWN: 1.0,
            chess.KNIGHT: 3.0,
            chess.BISHOP: 3.0,
            chess.ROOK: 5.0,
            chess.QUEEN: 9.0,
            chess.KING: 0.0  # King's value isn't counted in material
        }
        
        # Position evaluation weights
        position_weights = {
            # Center control
            chess.E4: 0.3, chess.D4: 0.3, chess.E5: 0.3, chess.D5: 0.3,
            # Extended center
            chess.C3: 0.1, chess.D3: 0.1, chess.E3: 0.1, chess.F3: 0.1,
            chess.C6: 0.1, chess.D6: 0.1, chess.E6: 0.1, chess.F6: 0.1,
            chess.C4: 0.1, chess.C5: 0.1, chess.F4: 0.1, chess.F5: 0.1
        }
        
        evaluation = 0.0
        
        # Count material
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                # Get material value
                value = piece_values[piece.piece_type]
                
                # Add square-specific position value if applicable
                if square in position_weights:
                    value += position_weights[square]
                    
                # Apply sign based on color
                value = value if piece.color == chess.WHITE else -value
                evaluation += value
        
        # Check status advantages
        if self.board.is_checkmate():
            # Big score for checkmate
            evaluation = float('-inf') if self.board.turn == chess.WHITE else float('inf')
        elif self.board.is_check():
            # Small bonus for giving check
            evaluation += 0.5 if self.board.turn == chess.BLACK else -0.5
        
        # Mobility (number of legal moves)
        mobility = len(list(self.board.legal_moves))
        # Save current turn
        current_turn = self.board.turn
        
        # Temporarily switch sides to count opponent's moves
        self.board.turn = not self.board.turn
        opponent_mobility = len(list(self.board.legal_moves))
        # Restore original turn
        self.board.turn = current_turn
        
        # Add small advantage for mobility difference
        mobility_score = (mobility - opponent_mobility) * 0.05
        evaluation += mobility_score if current_turn == chess.WHITE else -mobility_score
        
        return round(evaluation, 2)
    
    def get_board_state_text(self):
        """
        Get a text representation of the board.
        
        Returns:
            str: Text representation of the board with coordinates
        """
        # Convert the standard board string to a list of lines
        board_str = str(self.board).split('\n')
        
        # Add file coordinates at the bottom
        files = '    a b c d e f g h'
        
        # Construct board representation with rank numbers
        output = []
        for i, line in enumerate(board_str):
            output.append(f' {8-i} {line} {8-i}')
        output.append(files)
        
        return '\n'.join(output)

# Custom exception for illegal moves
class IllegalMoveError(Exception):
    """Exception raised when an illegal chess move is attempted."""
    pass
