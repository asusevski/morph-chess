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
    def __init__(self, games_pattern="*.json", refresh_rate=1.0):
        """
        Initialize the chess board monitor application.
        
        Args:
            games_pattern (str): Pattern to match game files (supports wildcards)
            refresh_rate (float): How often to check for updates (in seconds)
        """
        self.games_pattern = games_pattern
        self.refresh_rate = refresh_rate
        self.boards = {}
        self.board_widgets = {}
        self.game_info = {}  # Store additional game information
        self.game_frames = {}  # Store frames for each game
        self.last_modified = {}
        self.game_files = []
        self.displayed_games = set()  # Track which games are currently displayed
        
        # Create the main window
        self.root = tk.Tk()
        self.root.title("Chess Games Monitor")
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
        
        # Find all game files
        self.find_game_files()
        
        # Setup the grid layout
        self.setup_grid_layout()
        
        # Load initial boards
        self.load_initial_boards()
        
        # Start the monitoring thread
        self.running = True
        self.thread = threading.Thread(target=self.monitor_files)
        self.thread.daemon = True
        self.thread.start()
    
    def find_game_files(self):
        """Find all game files matching the pattern."""
        self.game_files = glob.glob(self.games_pattern)
        
        # Initialize last_modified tracker for each file
        for file in self.game_files:
            if file not in self.last_modified:
                self.last_modified[file] = None
    
    def setup_grid_layout(self):
        """Setup the grid layout for the boards."""
        # Configure grid weights for responsive layout
        for i in range(3):  # Assuming max 3 columns
            self.frame.grid_columnconfigure(i, weight=1)
        for i in range(10):  # Assuming reasonable max number of rows
            self.frame.grid_rowconfigure(i, weight=1)
    
    def load_initial_boards(self):
        """Load chess boards from all game files initially."""
        try:
            # Determine grid layout
            num_games = len(self.game_files)
            if num_games == 0:
                self.status_var.set("No game files found. Waiting for files...")
                return
                
            cols = min(3, num_games)  # Max 3 columns
            
            # Create boards
            for i, game_file in enumerate(sorted(self.game_files)):
                self.create_or_update_game_display(game_file, i, cols)
                
            self.status_var.set(f"Loaded {num_games} chess games at {datetime.now().strftime('%H:%M:%S')}")
            
        except Exception as e:
            self.status_var.set(f"Error loading boards: {str(e)}")
            print(f"Error loading boards: {str(e)}")
    
    def create_or_update_game_display(self, game_file, index, cols):
        """Create or update a single game display."""
        try:
            # Try to read the game file
            try:
                with open(game_file, 'r') as f:
                    game_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"Error reading {game_file}: {str(e)}")
                # If we can't read the file, but it's already displayed, keep it
                game_id = os.path.basename(game_file)
                if game_id in self.displayed_games:
                    return
                else:
                    # Don't try to display this file
                    return
            
            # Extract game ID and other info
            game_id = game_data.get("game_id", os.path.basename(game_file))
            fen = game_data.get("fen", chess.STARTING_FEN)
            strategy = game_data.get("strategy_name", "Unknown")
            last_updated = game_data.get("last_updated", "Unknown")
            move_history = game_data.get("move_history", [])
            
            # Calculate grid position
            row, col = index // cols, index % cols
            
            # Check if this game is already displayed
            if game_id in self.displayed_games:
                # Update existing board
                self.boards[game_id] = chess.Board(fen)
                self.game_info[game_id] = {
                    "file": game_file,
                    "strategy": strategy,
                    "last_updated": last_updated,
                    "move_history": move_history
                }
                
                # Update labels with new info
                game_frame = self.game_frames[game_id]
                
                # Update move count
                for widget in game_frame.winfo_children():
                    if isinstance(widget, tk.Frame):  # This is the header frame
                        for label in widget.winfo_children():
                            if isinstance(label, tk.Label) and "Moves:" in label.cget("text"):
                                label.config(text=f"Moves: {len(move_history)}")
                            elif isinstance(label, tk.Label) and "Last move:" in label.cget("text"):
                                last_time = last_updated.split('T')[1].split('.')[0] if 'T' in last_updated else last_updated
                                label.config(text=f"Last move: {last_time}")
                
                # Update the board display
                self.update_board_display(game_id)
            else:
                # Create a new frame for the game
                game_frame = tk.Frame(self.frame)
                game_frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
                self.game_frames[game_id] = game_frame
                
                # Create board object
                board = chess.Board(fen)
                self.boards[game_id] = board
                self.game_info[game_id] = {
                    "file": game_file,
                    "strategy": strategy,
                    "last_updated": last_updated,
                    "move_history": move_history
                }
                
                # Create header with game info
                header_frame = tk.Frame(game_frame)
                header_frame.pack(fill=tk.X)
                
                # Game ID as title
                title = os.path.basename(game_file).replace('.json', '')
                game_title = tk.Label(header_frame, text=f"Game: {title}", font=("Arial", 12, "bold"))
                game_title.pack(side=tk.TOP)
                
                # Strategy info
                strategy_label = tk.Label(header_frame, text=f"Strategy: {strategy}")
                strategy_label.pack(side=tk.TOP)
                
                # Move count
                moves_label = tk.Label(header_frame, text=f"Moves: {len(move_history)}")
                moves_label.pack(side=tk.TOP)
                
                # Last updated time
                last_time = last_updated.split('T')[1].split('.')[0] if 'T' in last_updated else last_updated
                updated_label = tk.Label(header_frame, text=f"Last move: {last_time}")
                updated_label.pack(side=tk.TOP)
                
                # Label for chess board image
                board_label = tk.Label(game_frame)
                board_label.pack(padx=5, pady=5)
                self.board_widgets[game_id] = board_label
                
                # Update display
                self.update_board_display(game_id)
                
                # Mark as displayed
                self.displayed_games.add(game_id)
                
        except Exception as e:
            print(f"Error creating/updating display for {game_file}: {str(e)}")
    
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
    
    def rearrange_boards(self):
        """Rearrange boards in the grid if needed."""
        # Get currently displayed games
        active_games = sorted(list(self.displayed_games))
        num_games = len(active_games)
        
        if num_games == 0:
            return
            
        cols = min(3, num_games)  # Max 3 columns
        
        # Rearrange all games
        for i, game_id in enumerate(active_games):
            if game_id in self.game_frames:
                row, col = i // cols, i % cols
                self.game_frames[game_id].grid(row=row, column=col)
    
    def check_for_missing_games(self):
        """Check for game files that were previously displayed but are now missing."""
        current_files = set(self.game_files)
        games_to_remove = []
        
        # Find games that are displayed but no longer have files
        for game_id in self.displayed_games:
            file_found = False
            for game_file in current_files:
                if os.path.basename(game_file) == game_id or os.path.basename(game_file).startswith(game_id):
                    file_found = True
                    break
                    
            if not file_found:
                # Game has been missing for too long, remove it
                games_to_remove.append(game_id)
        
        # Remove games that are no longer present
        for game_id in games_to_remove:
            if game_id in self.game_frames:
                self.game_frames[game_id].destroy()
                del self.game_frames[game_id]
            
            if game_id in self.board_widgets:
                del self.board_widgets[game_id]
                
            if game_id in self.boards:
                del self.boards[game_id]
                
            if game_id in self.game_info:
                del self.game_info[game_id]
                
            self.displayed_games.remove(game_id)
    
    def monitor_files(self):
        """Monitor all game files for changes and look for new files."""
        while self.running:
            try:
                updated = False
                
                # Check for new game files
                current_files = glob.glob(self.games_pattern)
                if set(current_files) != set(self.game_files):
                    # Update the file list
                    self.game_files = current_files
                    for file in self.game_files:
                        if file not in self.last_modified:
                            self.last_modified[file] = None
                    updated = True
                
                # Check each file for modifications
                for game_file in self.game_files:
                    if os.path.exists(game_file):
                        try:
                            modified_time = os.path.getmtime(game_file)
                            
                            if self.last_modified[game_file] is None or modified_time > self.last_modified[game_file]:
                                self.last_modified[game_file] = modified_time
                                
                                # Update just this game
                                def update_specific_game():
                                    try:
                                        # Find index for this game
                                        game_files_sorted = sorted(self.game_files)
                                        if game_file in game_files_sorted:
                                            index = game_files_sorted.index(game_file)
                                            cols = min(3, len(game_files_sorted))
                                            self.create_or_update_game_display(game_file, index, cols)
                                    except Exception as e:
                                        print(f"Error updating specific game {game_file}: {str(e)}")
                                
                                # Schedule the update on the main thread
                                self.root.after(0, update_specific_game)
                                updated = True
                        except (FileNotFoundError, PermissionError) as e:
                            # File might be in the middle of being uploaded
                            print(f"Couldn't access {game_file}: {str(e)}")
                
                # Check for missing games less frequently to prevent flickering
                if updated:
                    # Schedule a check for missing games
                    self.root.after(5000, self.check_for_missing_games)  # Check after 5 seconds of stability
                    
                    # Rearrange boards if needed
                    self.root.after(0, self.rearrange_boards)
                    
                    # Update status
                    self.status_var.set(f"Updated games at {datetime.now().strftime('%H:%M:%S')}")
                
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
        # Start main loop
        self.root.mainloop()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Chess Games Monitor')
    parser.add_argument('--games', type=str, default='game_*.json',
                        help='Pattern to match game files (supports wildcards)')
    parser.add_argument('--refresh', type=float, default=1.0,
                        help='Refresh rate in seconds')
    args = parser.parse_args()
    
    # Start the monitor
    monitor = ChessBoardMonitor(games_pattern=args.games, refresh_rate=args.refresh)
    monitor.run()


if __name__ == "__main__":
    main()
