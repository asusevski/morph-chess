import chess
import uuid
import json
import os
import sys
import random
import argparse
from datetime import datetime

def initialize_board():
    """
    Initialize a new chess board in the starting position.
    Generates a unique UUID for the game.
    
    Returns:
        tuple: (chess.Board, str) - A new chess board in the starting position and a game ID
    """
    board = chess.Board()
    game_id = str(uuid.uuid4())
    return board, game_id

def make_move(board, move_uci):
    """
    Make a move on the chess board using Universal Chess Interface (UCI) notation.
    Raises an exception if the move is illegal.
    
    Args:
        board (chess.Board): The current chess board
        move_uci (str): The move in UCI notation (e.g., "e2e4", "g1f3")
        
    Returns:
        chess.Board: The updated chess board after the move
        
    Raises:
        ValueError: If the move is not valid UCI notation
        IllegalMoveError: If the move is illegal on the current board
    """
    try:
        move = chess.Move.from_uci(move_uci)
    except ValueError:
        raise ValueError(f"Invalid UCI notation: {move_uci}")
        
    if move not in board.legal_moves:
        raise IllegalMoveError(f"Illegal move: {move_uci}")
        
    board.push(move)
    return board

def is_game_over(board):
    """
    Check if the game is over and return the result.
    
    Args:
        board (chess.Board): The current chess board
        
    Returns:
        dict: A dictionary containing game status information:
            - 'is_over': Boolean indicating if the game is over
            - 'result': The result of the game as a string ("1-0", "0-1", "1/2-1/2", or None)
            - 'reason': The reason why the game is over (checkmate, stalemate, etc.)
    """
    result = {
        'is_over': board.is_game_over(),
        'result': None,
        'reason': None
    }
    
    if result['is_over']:
        if board.is_checkmate():
            result['reason'] = 'checkmate'
            result['result'] = "0-1" if board.turn == chess.WHITE else "1-0"
        elif board.is_stalemate():
            result['reason'] = 'stalemate'
            result['result'] = "1/2-1/2"
        elif board.is_insufficient_material():
            result['reason'] = 'insufficient material'
            result['result'] = "1/2-1/2"
        elif board.is_fifty_moves():
            result['reason'] = 'fifty-move rule'
            result['result'] = "1/2-1/2"
        elif board.is_repetition():
            result['reason'] = 'threefold repetition'
            result['result'] = "1/2-1/2"
            
    return result

# Custom exception for illegal moves
class IllegalMoveError(Exception):
    """Exception raised when an illegal chess move is attempted."""
    pass

# Functions to save and load game state
def save_game(board, game_id, filepath=None):
    """
    Save the current game state to a text file.
    
    Args:
        board (chess.Board): The current chess board
        game_id (str): The UUID of the game
        filepath (str, optional): Custom filepath. If None, uses game_id as filename.
    
    Returns:
        str: Path to the saved game file
    """
    if filepath is None:
        filepath = f"chess_game_{game_id}.json"
    
    game_data = {
        "game_id": game_id,
        "fen": board.fen(),
        "move_history": [move.uci() for move in board.move_stack],
        "saved_at": datetime.now().isoformat()
    }
    
    with open(filepath, 'w') as f:
        json.dump(game_data, f, indent=2)
    
    return filepath

def load_game(filepath):
    """
    Load a saved game from a file.
    
    Args:
        filepath (str): Path to the saved game file
    
    Returns:
        tuple: (chess.Board, str) - Loaded chess board and game ID
    
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
        board = chess.Board(game_data["fen"])
    except ValueError as e:
        raise ValueError(f"Invalid FEN in game file: {str(e)}")
    
    # Optionally replay moves
    if "move_history" in game_data:
        # Clear the move stack first (since we loaded from FEN)
        board.clear_stack()
        # Replay each move
        for move_uci in game_data["move_history"]:
            try:
                move = chess.Move.from_uci(move_uci)
                if move in board.legal_moves:
                    board.push(move)
                else:
                    # If we encounter an illegal move in history, stop replaying
                    # but keep the board state from the valid moves
                    break
            except ValueError:
                # Skip invalid UCI strings
                continue
    
    return board, game_data["game_id"]

def make_random_move(board):
    """
    Make a random legal move on the board.
    
    Args:
        board (chess.Board): The current chess board
        
    Returns:
        chess.Move: The randomly selected move that was made
    
    Raises:
        ValueError: If there are no legal moves available
    """
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        raise ValueError("No legal moves available")
    
    random_move = random.choice(legal_moves)
    board.push(random_move)
    return random_move

def display_board(board):
    """
    Display the chess board with coordinates and current turn.
    
    Args:
        board (chess.Board): The chess board to display
    """
    # Get the evaluation
    eval_score = evaluate_board(board)
    
    # Convert the standard board string to a list of lines
    board_str = str(board).split('\n')
    
    # Add file coordinates at the bottom
    files = '    a b c d e f g h'
    
    # Print rank numbers alongside the board
    print('')
    for i, line in enumerate(board_str):
        print(f' {8-i} {line} {8-i}')
    print(files)
    
    # Display whose turn it is
    turn = "White" if board.turn == chess.WHITE else "Black"
    print(f"\nCurrent turn: {turn}")
    
    # Show evaluation
    if eval_score > 0:
        eval_display = f"+{eval_score}" if eval_score < 100 else "+∞"
        print(f"Evaluation: {eval_display} (White advantage)")
    elif eval_score < 0:
        eval_display = f"{eval_score}" if eval_score > -100 else "-∞"
        print(f"Evaluation: {eval_display} (Black advantage)")
    else:
        print("Evaluation: 0.00 (Equal position)")
    
    # Show check status
    if board.is_check():
        print(f"{turn} is in CHECK!")

def display_valid_moves(board):
    """
    Display all valid moves for the current player in a readable format.
    
    Args:
        board (chess.Board): The current chess board
    """
    legal_moves = list(board.legal_moves)
    
    if not legal_moves:
        print("No legal moves available!")
        return
    
    # Group moves by starting square
    moves_by_square = {}
    for move in legal_moves:
        from_square = chess.square_name(move.from_square)
        if from_square not in moves_by_square:
            moves_by_square[from_square] = []
        moves_by_square[from_square].append(chess.square_name(move.to_square))
    
    # Display moves in organized format
    print("\nValid moves:")
    for from_square, to_squares in sorted(moves_by_square.items()):
        # Get the piece at this square
        piece = board.piece_at(chess.parse_square(from_square))
        piece_symbol = piece.symbol()
        
        # Format the destinations
        destinations = ", ".join(sorted(to_squares))
        
        print(f"  {piece_symbol} at {from_square} → {destinations}")
    
    print(f"Total legal moves: {len(legal_moves)}")

def evaluate_board(board):
    """
    Calculate a simple evaluation of the current board position.
    Positive values favor white, negative values favor black.
    
    Args:
        board (chess.Board): The chess board to evaluate
        
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
        piece = board.piece_at(square)
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
    if board.is_checkmate():
        # Big score for checkmate
        evaluation = float('-inf') if board.turn == chess.WHITE else float('inf')
    elif board.is_check():
        # Small bonus for giving check
        evaluation += 0.5 if board.turn == chess.BLACK else -0.5
    
    # Mobility (number of legal moves)
    mobility = len(list(board.legal_moves))
    # Save current turn
    current_turn = board.turn
    
    # Temporarily switch sides to count opponent's moves
    board.turn = not board.turn
    opponent_mobility = len(list(board.legal_moves))
    # Restore original turn
    board.turn = current_turn
    
    # Add small advantage for mobility difference
    mobility_score = (mobility - opponent_mobility) * 0.05
    evaluation += mobility_score if current_turn == chess.WHITE else -mobility_score
    
    return round(evaluation, 2)

def game_loop():
    """
    Main game loop for playing chess against a computer making random moves.
    Allows loading from a saved game or starting a new one.
    """
    parser = argparse.ArgumentParser(description="Chess game with save/load functionality")
    parser.add_argument("--load", help="Load a saved game file")
    parser.add_argument("--autosave", action="store_true", help="Automatically save the game after every move")
    args = parser.parse_args()
    
    # Either load a game or start a new one
    if args.load:
        try:
            board, game_id = load_game(args.load)
            print(f"Loaded game with ID: {game_id}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error loading game: {e}")
            return
    else:
        board, game_id = initialize_board()
        print(f"New game started with ID: {game_id}")
    
    # Create save directory if using autosave
    autosave_dir = "chess_autosaves"
    if args.autosave and not os.path.exists(autosave_dir):
        os.makedirs(autosave_dir)
        
    print("\nWelcome to Chess!")
    print("You play as White, computer plays as Black")
    print("Commands:")
    print("  - Enter moves in UCI format (e.g., 'e2e4')")
    print("  - Type 'moves' to show all valid moves")
    print("  - Type 'save' to save the current game")
    print("  - Type 'quit' to exit")
    print("  - Type 'help' for this message")
    
    if args.autosave:
        print("\nAuto-save is enabled. Game will be saved after every move.")
        print(f"Auto-save files will be stored in the '{autosave_dir}' directory.")
    
    # Main game loop
    while True:
        display_board(board)
        
        # Check if game is over
        status = is_game_over(board)
        if status['is_over']:
            print(f"\nGame over! Result: {status['result']}")
            print(f"Reason: {status['reason']}")
            break
        
        # Human's turn (White)
        if board.turn == chess.WHITE:
            user_input = input("\nYour move (or 'save'/'quit'/'help'): ").strip().lower()
            
            if user_input == 'quit':
                print("Thanks for playing!")
                break
            elif user_input == 'save':
                filepath = save_game(board, game_id)
                print(f"Game saved to: {filepath}")
                print(f"Game ID: {game_id}")
                continue
            elif user_input == 'help':
                print("\nCommands:")
                print("  - Enter moves in UCI format (e.g., 'e2e4')")
                print("  - Type 'moves' to show all valid moves")
                print("  - Type 'save' to save the current game")
                print("  - Type 'quit' to exit")
                print("  - Type 'help' for this message")
                continue
            elif user_input == 'moves':
                display_valid_moves(board)
                continue
            
            # Try to make the user's move
            try:
                board = make_move(board, user_input)
                
                # Auto-save after player's move if enabled
                if args.autosave:
                    autosave_path = os.path.join(autosave_dir, f"chess_game_{game_id}_move_{len(board.move_stack)}.json")
                    save_game(board, game_id, autosave_path)
                    print(f"Game auto-saved to: {autosave_path}")
            except (ValueError, IllegalMoveError) as e:
                print(f"Error: {e}")
                print("Please try again.")
                continue
        
        # Computer's turn (Black)
        else:
            print("\nComputer is thinking...")
            try:
                # Make a random move for the computer
                random_move = make_random_move(board)
                print(f"Computer's move: {random_move.uci()}")
                
                # Auto-save after computer's move if enabled
                if args.autosave:
                    autosave_path = os.path.join(autosave_dir, f"chess_game_{game_id}_move_{len(board.move_stack)}.json")
                    save_game(board, game_id, autosave_path)
                    print(f"Game auto-saved to: {autosave_path}")
            except ValueError as e:
                print(f"Error: {e}")
                break

# Run the game if script is executed
if __name__ == "__main__":
    game_loop()
