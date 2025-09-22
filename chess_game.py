import argparse
import os
from chess_engine import ChessEngine, IllegalMoveError

def display_help():
    """Display help information for the chess game."""
    print("\nCommands:")
    print("  - Enter moves in UCI format (e.g., 'e2e4')")
    print("  - Type 'moves' to show all valid moves")
    print("  - Type 'save' to save the current game")
    print("  - Type 'quit' to exit")
    print("  - Type 'help' for this message")

def display_valid_moves(engine):
    """
    Display all valid moves for the current player in a readable format.
    
    Args:
        engine: ChessEngine instance
    """
    legal_moves = engine.get_valid_moves()
    
    if not legal_moves:
        print("No legal moves available!")
        return
    
    # Group moves by starting square
    moves_by_square = {}
    for move in legal_moves:
        from_square = move[:2]
        to_square = move[2:4]
        if from_square not in moves_by_square:
            moves_by_square[from_square] = []
        moves_by_square[from_square].append(to_square)
    
    # Display moves in organized format
    print("\nValid moves:")
    for from_square, to_squares in sorted(moves_by_square.items()):
        # Get the piece at this square
        piece = engine.board.piece_at(chess.parse_square(from_square))
        piece_symbol = piece.symbol()
        
        # Format the destinations
        destinations = ", ".join(sorted(to_squares))
        
        print(f"  {piece_symbol} at {from_square} → {destinations}")
    
    print(f"Total legal moves: {len(legal_moves)}")

def game_loop():
    """
    Main game loop for playing chess against a computer making random moves.
    Allows loading from a saved game or starting a new one.
    """
    parser = argparse.ArgumentParser(description="Chess game with save/load functionality")
    parser.add_argument("--load", help="Load a saved game file")
    parser.add_argument("--autosave", action="store_true", help="Automatically save the game after every move")
    parser.add_argument("--game-id", help="Specify a custom game ID")
    parser.add_argument("--strategy", help="Name of the agent's strategy")
    args = parser.parse_args()
    
    # Create save directory
    autosave_dir = "chess_autosaves"
    
    # Initialize the chess engine
    if args.load:
        try:
            engine = ChessEngine(load_path=args.load, autosave=args.autosave, autosave_dir=autosave_dir, strategy_name=args.strategy)
            print(f"Loaded game with ID: {engine.game_id}")
        except (FileNotFoundError, ValueError) as e:
            print(f"Error loading game: {e}")
            return
    else:
        engine = ChessEngine(autosave=args.autosave, autosave_dir=autosave_dir, game_id=args.game_id, strategy_name=args.strategy)
        print(f"New game started with ID: {engine.game_id}")
    
    # Define the autosave file path
    autosave_path = os.path.join(autosave_dir, f"game_id_{engine.game_id}.json")
        
    print("\nWelcome to Chess!")
    print("You play as White, computer plays as Black")
    
    # Display strategy if specified
    if engine.strategy_name:
        print(f"Agent is using the '{engine.strategy_name}' strategy")
        
    display_help()
    
    if args.autosave:
        print("\nAuto-save is enabled. Game will be saved after every move.")
        print(f"Auto-save file: {autosave_path}")
    
    # Main game loop
    while True:
        # Display the current board
        print("\n" + engine.get_board_state_text())
        print(f"\nCurrent turn: {engine.get_current_turn()}")
        
        # Show evaluation
        eval_score = engine.evaluate_position()
        if eval_score > 0:
            eval_display = f"+{eval_score}" if eval_score < 100 else "+∞"
            print(f"Evaluation: {eval_display} (White advantage)")
        elif eval_score < 0:
            eval_display = f"{eval_score}" if eval_score > -100 else "-∞"
            print(f"Evaluation: {eval_display} (Black advantage)")
        else:
            print("Evaluation: 0.00 (Equal position)")
        
        # Show check status
        if engine.is_in_check():
            print(f"{engine.get_current_turn()} is in CHECK!")
        
        # Check if game is over
        status = engine.is_game_over()
        if status['is_over']:
            print(f"\nGame over! Result: {status['result']}")
            print(f"Reason: {status['reason']}")
            
            # Save the final state if autosave is enabled
            if args.autosave:
                engine.save_game()
                print(f"Final game state saved to: {autosave_path}")
            break
        
        # Human's turn (White)
        if engine.get_current_turn() == "White":
            user_input = input("\nYour move (or 'save'/'quit'/'help'): ").strip().lower()
            
            if user_input == 'quit':
                print("Thanks for playing!")
                break
            elif user_input == 'save':
                # Save to a custom file in the main directory
                custom_filepath = f"chess_game_{engine.game_id}.json"
                engine.save_game(custom_filepath)
                print(f"Game saved to: {custom_filepath}")
                print(f"Game ID: {engine.game_id}")
                continue
            elif user_input == 'help':
                display_help()
                continue
            elif user_input == 'moves':
                display_valid_moves(engine)
                continue
            
            # Try to make the user's move
            try:
                engine.make_move(user_input)
                print(f"Move made: {user_input}")
            except (ValueError, IllegalMoveError) as e:
                print(f"Error: {e}")
                print("Please try again.")
                continue
        
        # Computer's turn (Black)
        else:
            print("\nComputer is thinking...")
            try:
                computer_move = engine.make_computer_move()
                print(f"Computer's move: {computer_move}")
            except ValueError as e:
                print(f"Error: {e}")
                break

# Required import for chess square parsing in display_valid_moves
import chess

# Run the game if script is executed
if __name__ == "__main__":
    game_loop()
