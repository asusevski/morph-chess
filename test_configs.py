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

def create_config_files(num_files=3, games_per_file=2):
    """Create chess configuration files with initial states."""
    config_files = []
    
    for i in range(1, num_files + 1):
        filename = f"chess_config_{i}.json"
        config = {"games": {}}
        
        # Create games for this file
        for j in range(1, games_per_file + 1):
            game_id = f"Game {j}"
            # Some files start with default position, some with a few moves already made
            if random.random() > 0.5:
                board = chess.Board()
                # Make 0-3 random initial moves
                for _ in range(random.randint(0, 3)):
                    make_random_move(board)
                fen = board.fen()
            else:
                fen = chess.STARTING_FEN
                
            config["games"][game_id] = {
                "fen": fen,
                "white": f"Player {(i-1)*games_per_file*2 + j*2 - 1}",
                "black": f"Player {(i-1)*games_per_file*2 + j*2}"
            }
        
        # Write the config file
        with open(filename, 'w') as f:
            json.dump(config, f, indent=4)
            
        config_files.append(filename)
        print(f"Created {filename} with {games_per_file} games")
    
    return config_files

def update_configs(config_files, num_moves=10, delay=2.0):
    """Make random moves and update the configuration files."""
    # Load boards from config files
    all_boards = {}
    
    for config_file in config_files:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        all_boards[config_file] = {}
        for game_id, game_data in config["games"].items():
            all_boards[config_file][game_id] = chess.Board(game_data["fen"])
    
    # Make moves
    for move_num in range(1, num_moves + 1):
        print(f"\n=== MOVE {move_num} of {num_moves} ===")
        
        # Update each file
        for config_file in config_files:
            print(f"\nUpdating {config_file}:")
            
            # Load current config
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Update each game
            boards = all_boards[config_file]
            for game_id, board in boards.items():
                if make_random_move(board):
                    # Update FEN in config
                    config["games"][game_id]["fen"] = board.fen()
                    
                    # Show move info
                    last_move = board.peek() if len(board.move_stack) > 0 else None
                    print(f"  {game_id}: Made move {last_move}")
                    
                    if board.is_check():
                        print(f"  {game_id}: CHECK!")
                    if board.is_checkmate():
                        print(f"  {game_id}: CHECKMATE!")
                else:
                    print(f"  {game_id}: Game over (checkmate or stalemate)")
            
            # Save updated config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
        
        # Show timestamp for this update
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\nUpdated all files at {timestamp}")
        
        # Wait before next move
        if move_num < num_moves:
            print(f"Waiting {delay} seconds...")
            time.sleep(delay)
    
    print("\nCompleted all moves!")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate and update chess configuration files')
    parser.add_argument('--files', type=int, default=3,
                        help='Number of configuration files to create')
    parser.add_argument('--games', type=int, default=1,
                        help='Number of games per file')
    parser.add_argument('--moves', type=int, default=10,
                        help='Number of moves to make')
    parser.add_argument('--delay', type=float, default=2.0,
                        help='Delay between moves in seconds')
    parser.add_argument('--no-create', action='store_true',
                        help='Skip creating new files, just update existing ones')
    args = parser.parse_args()
    
    # Create or identify config files
    if args.no_create:
        import glob
        config_files = glob.glob("chess_config_*.json")
        if not config_files:
            print("No existing config files found. Creating new ones...")
            config_files = create_config_files(args.files, args.games)
    else:
        config_files = create_config_files(args.files, args.games)
    
    # Update the configuration files
    update_configs(config_files, args.moves, args.delay)

if __name__ == "__main__":
    main()
