import chess
import json
import time
import os
import random
import glob
from datetime import datetime

def make_random_move(board):
    """Make a random legal move on the board."""
    legal_moves = list(board.legal_moves)
    if not legal_moves:
        return False  # No legal moves available (checkmate or stalemate)
    
    move = random.choice(legal_moves)
    board.push(move)
    return True

def update_configs(config_pattern="chess_config*.json", num_moves=10, delay=2.0):
    """
    Update multiple chess configuration files with random moves.
    
    Args:
        config_pattern (str): Pattern to match configuration files (supports wildcards)
        num_moves (int): Number of moves to make
        delay (float): Delay between moves in seconds
    """
    # Find all matching configuration files
    config_files = glob.glob(config_pattern)
    
    # If no files found, create a default one
    if not config_files:
        default_files = ["chess_config_1.json", "chess_config_2.json"]
        for i, filename in enumerate(default_files):
            default_config = {
                "games": {
                    f"Game {i*2+1}": {"fen": chess.STARTING_FEN, "white": f"Player {i*2+1}", "black": f"Player {i*2+2}"},
                    f"Game {i*2+2}": {"fen": chess.STARTING_FEN, "white": f"Player {i*2+3}", "black": f"Player {i*2+4}"}
                }
            }
            with open(filename, 'w') as f:
                json.dump(default_config, f, indent=4)
            config_files.append(filename)
        print(f"Created default configuration files: {', '.join(default_files)}")
    
    # Create board objects for each game in each file
    all_boards = {}
    all_configs = {}
    
    for config_file in config_files:
        # Load the configuration
        if not os.path.exists(config_file):
            # Create default config if this specific file doesn't exist
            default_config = {
                "games": {
                    "Game 1": {"fen": chess.STARTING_FEN, "white": "Player 1", "black": "Player 2"}
                }
            }
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created default configuration in {config_file}")
            all_configs[config_file] = default_config
        else:
            with open(config_file, 'r') as f:
                all_configs[config_file] = json.load(f)
        
        # Initialize boards for each game
        all_boards[config_file] = {}
        for game_id, game_data in all_configs[config_file].get("games", {}).items():
            all_boards[config_file][game_id] = chess.Board(game_data.get("fen", chess.STARTING_FEN))
    
    # Make moves and update the configurations
    for move_num in range(1, num_moves + 1):
        print(f"\n--- Making move {move_num} of {num_moves} ---")
        
        # Update each configuration file
        for config_file in config_files:
            print(f"\nUpdating file: {config_file}")
            config = all_configs[config_file]
            boards = all_boards[config_file]
            
            # Update each game in this config
            for game_id, board in boards.items():
                if make_random_move(board):
                    # Update the FEN in the configuration
                    config["games"][game_id]["fen"] = board.fen()
                    
                    # Print the updated state
                    print(f"  {game_id}: {board.fen()}")
                    print(f"  Last move: {board.peek()}")
                    if board.is_check():
                        print("  CHECK!")
                    if board.is_checkmate():
                        print("  CHECKMATE!")
                else:
                    print(f"  {game_id}: Game over (checkmate or stalemate)")
            
            # Save the updated configuration
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=4)
        
        # Add a timestamp to show when the update occurred
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\nUpdated all configurations at {timestamp}")
        
        # Wait before the next move
        if move_num < num_moves:
            print(f"Waiting {delay} seconds before next move...")
            time.sleep(delay)
    
    print("\nCompleted all moves across all configuration files!")

def modify_chess_monitor(original_file="chess_monitor.py", output_file="chess_monitor_multi.py"):
    """
    Modify the chess_monitor.py script to handle multiple configuration files.
    This creates a new file with the modified code.
    """
    try:
        with open(original_file, 'r') as f:
            code = f.read()
        
        # Replace the ChessBoardMonitor class to support multiple config files
        modified_code = code.replace(
            "class ChessBoardMonitor:",
            """class ChessBoardMonitor:
    def __init__(self, config_files=None, refresh_rate=1.0):
        \"\"\"
        Initialize the chess board monitor application.
        
        Args:
            config_files (list): List of paths to configuration files with game data
            refresh_rate (float): How often to check for updates (in seconds)
        \"\"\"
        self.config_files = config_files or ["chess_config.json"]
        if isinstance(self.config_files, str):
            self.config_files = [self.config_files]
        self.refresh_rate = refresh_rate
        self.boards = {}
        self.board_widgets = {}
        self.last_modified = {file: None for file in self.config_files}"""
        )
        
        # Replace the load_boards method
        modified_code = modified_code.replace(
            "def load_boards(self):",
            """def load_boards(self):
        \"\"\"Load the chess boards from all configuration files.\"\"\"
        try:
            # Clear existing boards if there are any
            for widget in self.frame.winfo_children():
                widget.destroy()
            
            self.boards = {}
            self.board_widgets = {}
            
            all_games = {}
            
            # Load games from all configuration files
            for config_file in self.config_files:
                try:
                    if not os.path.exists(config_file):
                        # Create a default configuration with one empty board
                        default_config = {
                            "games": {
                                f"Game ({config_file})": {"fen": chess.STARTING_FEN, "white": "Player 1", "black": "Player 2"}
                            }
                        }
                        with open(config_file, 'w') as f:
                            json.dump(default_config, f, indent=4)
                        
                        self.status_var.set(f"Created default configuration in {config_file}")
                    
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    # Add prefix to game IDs to avoid conflicts between files
                    for game_id, game_data in config.get("games", {}).items():
                        full_id = f"{game_id} ({os.path.basename(config_file)})"
                        all_games[full_id] = game_data
                        
                except Exception as e:
                    print(f"Error loading {config_file}: {str(e)}")
                    self.status_var.set(f"Error loading {config_file}: {str(e)}")"""
        )
        
        # Replace the monitor_file method
        modified_code = modified_code.replace(
            "def monitor_file(self):",
            """def monitor_file(self):
        \"\"\"Monitor all configuration files for changes and update as needed.\"\"\"
        while self.running:
            try:
                updated = False
                
                # Check each configuration file
                for config_file in self.config_files:
                    # Check if the file exists and if it's been modified
                    if os.path.exists(config_file):
                        modified_time = os.path.getmtime(config_file)
                        
                        # If this is the first check or the file has been modified
                        if self.last_modified[config_file] is None or modified_time > self.last_modified[config_file]:
                            self.last_modified[config_file] = modified_time
                            updated = True
                
                # If any file was updated, reload all boards
                if updated:
                    # Load the boards on the main thread
                    self.root.after(0, self.load_boards)
                
                time.sleep(self.refresh_rate)
                
            except Exception as e:
                print(f"Error monitoring files: {str(e)}")
                self.status_var.set(f"Error monitoring files: {str(e)}")
                time.sleep(self.refresh_rate)"""
        )
        
        # Update the main function to accept multiple config files
        modified_code = modified_code.replace(
            "def main():",
            """def main():
    # Add import for io module that was missing above
    import io
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Chess Board Monitor')
    parser.add_argument('--config', type=str, nargs='+', default=['chess_config.json'],
                        help='Path(s) to configuration file(s)')
    parser.add_argument('--refresh', type=float, default=1.0,
                        help='Refresh rate in seconds')
    args = parser.parse_args()
    
    # Start the monitor
    monitor = ChessBoardMonitor(config_files=args.config, refresh_rate=args.refresh)
    monitor.run()"""
        )
        
        # Write the modified code to a new file
        with open(output_file, 'w') as f:
            f.write(modified_code)
        
        print(f"Created modified chess monitor script: {output_file}")
        print(f"You can run it with: python {output_file} --config chess_config_1.json chess_config_2.json")
        
    except Exception as e:
        print(f"Error modifying chess monitor: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Update multiple chess configurations with random moves')
    parser.add_argument('--config', type=str, default='chess_config*.json',
                        help='Pattern to match configuration files (supports wildcards)')
    parser.add_argument('--moves', type=int, default=10,
                        help='Number of moves to make')
    parser.add_argument('--delay', type=float, default=2.0,
                        help='Delay between moves in seconds')
    parser.add_argument('--modify-monitor', action='store_true',
                        help='Create a modified version of chess_monitor.py to handle multiple files')
    args = parser.parse_args()
    
    # Create modified monitor script if requested
    if args.modify_monitor:
        modify_chess_monitor()
    
    # Update the configurations
    update_configs(config_pattern=args.config, num_moves=args.moves, delay=args.delay)
