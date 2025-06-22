import chess
import json
import time
import os
import random
from datetime import datetime

def make_random_move(board):
    """Make a random legal move on the board."""
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return False  # No legal moves available (checkmate or stalemate)
    
    move = random.choice(legal_moves)
    board.push(move)
    return True

def update_config(config_file="chess_config.json", num_moves=10, delay=2.0):
    """
    Update the chess configuration file with random moves.
    
    Args:
        config_file (str): Path to the configuration file
        num_moves (int): Number of moves to make
        delay (float): Delay between moves in seconds
    """
    # Create default config if it doesn't exist
    if not os.path.exists(config_file):
        default_config = {
            "games": {
                "Game 1": {"fen": chess.STARTING_FEN, "white": "Player 1", "black": "Player 2"},
                "Game 2": {"fen": chess.STARTING_FEN, "white": "Player 3", "black": "Player 4"}
            }
        }
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=4)
        print(f"Created default configuration in {config_file}")
    
    # Load the configuration
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    # Create board objects for each game
    boards = {}
    for game_id, game_data in config.get("games", {}).items():
        boards[game_id] = chess.Board(game_data.get("fen", chess.STARTING_FEN))
    
    # Make moves and update the configuration
    for move_num in range(1, num_moves + 1):
        print(f"\nMaking move {move_num} of {num_moves}")
        
        # Update each game
        for game_id, board in boards.items():
            if make_random_move(board):
                # Update the FEN in the configuration
                config["games"][game_id]["fen"] = board.fen()
                
                # Print the updated state
                print(f"{game_id}: {board.fen()}")
                print(f"Last move: {board.peek()}")
                if board.is_check():
                    print("CHECK!")
                if board.is_checkmate():
                    print("CHECKMATE!")
            else:
                print(f"{game_id}: Game over (checkmate or stalemate)")
        
        # Save the updated configuration
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
        
        # Add a timestamp to show when the update occurred
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"Updated configuration at {timestamp}")
        
        # Wait before the next move
        if move_num < num_moves:
            print(f"Waiting {delay} seconds before next move...")
            time.sleep(delay)
    
    print("\nCompleted all moves!")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Update chess configuration with random moves')
    parser.add_argument('--config', type=str, default='chess_config.json',
                        help='Path to the configuration file')
    parser.add_argument('--moves', type=int, default=10,
                        help='Number of moves to make')
    parser.add_argument('--delay', type=float, default=2.0,
                        help='Delay between moves in seconds')
    args = parser.parse_args()
    
    update_config(config_file=args.config, num_moves=args.moves, delay=args.delay)
