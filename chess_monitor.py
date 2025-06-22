import chess
import chess.svg
import time
import os
import io
import tkinter as tk
from PIL import Image, ImageTk
import threading
import json
from datetime import datetime
from cairosvg import svg2png
import glob

class ChessBoardMonitor:
    def __init__(self, config_pattern="chess_config*.json", refresh_rate=1.0):
        """
        Initialize the chess board monitor application.
        
        Args:
            config_pattern (str): Pattern to match config files (supports wildcards)
            refresh_rate (float): How often to check for updates (in seconds)
        """
        self.config_pattern = config_pattern
        self.refresh_rate = refresh_rate
        self.boards = {}
        self.board_widgets = {}
        self.last_modified = {}
        self.config_files = []
        
        # Create the main window
        self.root = tk.Tk()
        self.root.title("Multi-Game Chess Board Monitor")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Create a frame for the boards
        self.frame = tk.Frame(self.root)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Initializing...")
        self.status_bar = tk.Label(self.root, textvariable=self.status_var, 
                                   bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Find all config files
        self.find_config_files()
        
        # Start the monitoring thread
        self.running = True
        self.thread = threading.Thread(target=self.monitor_files)
        self.thread.daemon = True
        self.thread.start()
    
    def find_config_files(self):
        """Find all configuration files matching the pattern."""
        self.config_files = glob.glob(self.config_pattern)
        if not self.config_files:
            # Create default config files if none exist
            default_file = "chess_config.json"
            self.create_default_config(default_file)
            self.config_files = [default_file]
        
        # Initialize last_modified tracker for each file
        for file in self.config_files:
            self.last_modified[file] = None
    
    def create_default_config(self, filename):
        """Create a default configuration file."""
        default_config = {
            "games": {
                "Game 1": {"fen": chess.STARTING_FEN, "white": "Player 1", "black": "Player 2"}
            }
        }
        with open(filename, 'w') as f:
            json.dump(default_config, f, indent=4)
        print(f"Created default configuration file: {filename}")
    
    def load_boards(self):
        """Load chess boards from all configuration files."""
        try:
            # Clear existing boards
            for widget in self.frame.winfo_children():
                widget.destroy()
            
            self.boards = {}
            self.board_widgets = {}
            
            all_games = {}
            
            # Collect games from all config files
            for config_file in self.config_files:
                try:
                    if os.path.exists(config_file):
                        with open(config_file, 'r') as f:
                            config = json.load(f)
                        
                        # Add file identifier to game IDs to avoid conflicts
                        file_id = os.path.basename(config_file).replace('.json', '')
                        for game_id, game_data in config.get("games", {}).items():
                            unique_id = f"{game_id} [{file_id}]"
                            all_games[unique_id] = game_data
                except Exception as e:
                    print(f"Error loading {config_file}: {str(e)}")
            
            # Determine grid layout
            num_games = len(all_games)
            cols = min(3, num_games)  # Max 3 columns
            rows = (num_games + cols - 1) // cols  # Ceiling division
            
            # Create boards
            i = 0
            for game_id, game_data in all_games.items():
                # Create frame for each game
                game_frame = tk.Frame(self.frame)
                row, col = i // cols, i % cols
                game_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                
                # Create board object
                board = chess.Board(game_data.get("fen", chess.STARTING_FEN))
                self.boards[game_id] = board
                
                # Create header with game info
                header_frame = tk.Frame(game_frame)
                header_frame.pack(fill=tk.X)
                
                game_title = tk.Label(header_frame, text=game_id, font=("Arial", 12, "bold"))
                game_title.pack(side=tk.TOP)
                
                players_text = f"{game_data.get('white', 'White')} vs {game_data.get('black', 'Black')}"
                players_label = tk.Label(header_frame, text=players_text)
                players_label.pack(side=tk.TOP)
                
                # Label for chess board image
                board_label = tk.Label(game_frame)
                board_label.pack(padx=5, pady=5)
                self.board_widgets[game_id] = board_label
                
                # Update display
                self.update_board_display(game_id)
                
                i += 1
            
            # Configure grid weights
            for i in range(rows):
                self.frame.grid_rowconfigure(i, weight=1)
            for i in range(cols):
                self.frame.grid_columnconfigure(i, weight=1)
                
            self.status_var.set(f"Loaded {num_games} chess boards at {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.status_var.set(f"Error loading boards: {str(e)}")
            print(f"Error: {str(e)}")
    
    def update_board_display(self, game_id):
        """Update the display for a specific board."""
        if game_id not in self.boards or game_id not in self.board_widgets:
            return
            
        board = self.boards[game_id]
        board_widget = self.board_widgets[game_id]
        
        # Convert board to SVG
        svg_data = chess.svg.board(board, size=350)
        
        # Convert SVG to PNG
        png_data = svg2png(bytestring=svg_data)
        
        # Convert PNG to PhotoImage
        image = Image.open(io.BytesIO(png_data))
        photo = ImageTk.PhotoImage(image)
        
        # Update label
        board_widget.configure(image=photo)
        board_widget.image = photo  # Prevent garbage collection
    
    def monitor_files(self):
        """Monitor all configuration files for changes."""
        while self.running:
            try:
                updated = False
                
                # Check for new config files
                current_files = glob.glob(self.config_pattern)
                if set(current_files) != set(self.config_files):
                    self.config_files = current_files
                    for file in self.config_files:
                        if file not in self.last_modified:
                            self.last_modified[file] = None
                    updated = True
                
                # Check each file for modifications
                for config_file in self.config_files:
                    if os.path.exists(config_file):
                        modified_time = os.path.getmtime(config_file)
                        
                        if self.last_modified[config_file] is None or modified_time > self.last_modified[config_file]:
                            self.last_modified[config_file] = modified_time
                            updated = True
                
                # Reload boards if any files were updated
                if updated:
                    self.root.after(0, self.load_boards)
                
                time.sleep(self.refresh_rate)
                
            except Exception as e:
                print(f"Error monitoring files: {str(e)}")
                self.status_var.set(f"Error monitoring files: {str(e)}")
                time.sleep(self.refresh_rate)
    
    def on_close(self):
        """Handle window close event."""
        self.running = False
        self.root.destroy()
    
    def run(self):
        """Run the application."""
        # Load boards initially
        self.load_boards()
        
        # Start main loop
        self.root.mainloop()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Multi-Game Chess Board Monitor')
    parser.add_argument('--config', type=str, default='chess_config*.json',
                        help='Pattern to match configuration files (supports wildcards)')
    parser.add_argument('--refresh', type=float, default=1.0,
                        help='Refresh rate in seconds')
    args = parser.parse_args()
    
    # Start the monitor
    monitor = ChessBoardMonitor(config_pattern=args.config, refresh_rate=args.refresh)
    monitor.run()


if __name__ == "__main__":
    main()
