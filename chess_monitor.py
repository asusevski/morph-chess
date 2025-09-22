import argparse
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
import hashlib
import logging


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='chess_monitor.log'
)
logger = logging.getLogger('ChessMonitor')


class ChessBoardMonitor:
    def __init__(self, games_pattern="chess_autosaves/game_id_*.json", refresh_rate=1.0, game_timeout=20.0):
        """
        Initialize the chess board monitor application.
        
        Args:
            games_pattern (str): Pattern to match game files (supports wildcards)
            refresh_rate (float): How often to check for updates (in seconds)
            game_timeout (float): How long to wait before removing a missing game (in seconds)
        """
        self.games_pattern = games_pattern
        self.refresh_rate = refresh_rate
        self.game_timeout = game_timeout
        self.boards = {}
        self.board_widgets = {}
        self.game_info = {}  # Store additional game information
        self.game_frames = {}  # Store frames for each game
        self.last_modified = {}
        self.game_files = []
        self.displayed_games = set()  # Track which games are currently displayed
        self.game_state_hashes = {}  # Track game state hash to avoid redundant updates
        self.game_last_seen = {}  # Track when each game was last seen
        
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
    
    def compute_game_state_hash(self, file_path):
        """Calculate MD5 hash of file contents"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating hash: {e}")
            return None
    
    def find_game_files(self):
        """Find all game files matching the pattern."""
        try:
            previous_files = set(self.game_files)
            self.game_files = glob.glob(self.games_pattern)
            current_files = set(self.game_files)
            
            # Log new files
            new_files = current_files - previous_files
            if new_files:
                logger.info(f"Found {len(new_files)} new game files: {new_files}")
            
            # Initialize last_modified tracker for each file
            for file in self.game_files:
                if file not in self.last_modified:
                    self.last_modified[file] = None
                    game_id = os.path.basename(file).replace('.json', '')
                    # Initialize last seen time
                    self.game_last_seen[game_id] = time.time()
        except Exception as e:
            logger.error(f"Error finding game files: {str(e)}")
    
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
            error_msg = f"Error loading boards: {str(e)}"
            self.status_var.set(error_msg)
            logger.error(error_msg)
    
    def create_or_update_game_display(self, game_file, index, cols):
        """Create or update a single game display."""
        try:
            # Get game ID from filename
            game_id = os.path.basename(game_file).replace('.json', '').replace('game_id_', '')
            
            # Update last seen time
            self.game_last_seen[game_id] = time.time()
            
            # Calculate current hash
            current_hash = self.compute_game_state_hash(game_file)
            if current_hash is None:
                return
            
            # Skip update if the state hasn't changed
            if game_id in self.game_state_hashes and self.game_state_hashes[game_id] == current_hash:
                logger.debug(f"No state change for {game_id}, skipping update")
                return
            
            # Update the state hash
            self.game_state_hashes[game_id] = current_hash
            
            # Try to read the game file
            try:
                with open(game_file, 'r') as f:
                    file_content = f.read()
                    if not file_content.strip():
                        logger.warning(f"Empty file: {game_file}")
                        return
                    game_data = json.loads(file_content)
            except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
                logger.warning(f"Error reading {game_file}: {str(e)}")
                return
            
            # Extract game info
            fen = game_data.get("fen", chess.STARTING_FEN)
            strategy = game_data.get("strategy_name", "Unknown")
            last_updated = game_data.get("last_updated", datetime.now().isoformat())
            move_history = game_data.get("move_history", [])

            # Read instance_id from metadata file
            metadata_file = f"chess_autosaves/metadata_game_id_{game_id}.json"
            instance_id = "Unknown"
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    instance_id = metadata.get("instance_id", "Unknown")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                instance_id = "Unknown"
            
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
                    "move_history": move_history,
                    "instance_id": instance_id
                }
                
                # Update labels with new info
                game_frame = self.game_frames[game_id]
                
                # Update move count and last move time
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
                logger.info(f"Updated existing game {game_id}")
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
                    "move_history": move_history,
                    "instance_id": instance_id
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

                # Instance ID
                instance_label = tk.Label(header_frame, text=f"Instance: {instance_id}")
                instance_label.pack(side=tk.TOP)

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
                logger.info(f"Created new game display for {game_id}")
                
        except Exception as e:
            error_msg = f"Error creating/updating display for {game_file}: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
    
    def update_board_display(self, game_id):
        """Update the display for a specific board."""
        if game_id not in self.boards or game_id not in self.board_widgets:
            return
            
        board = self.boards[game_id]
        board_widget = self.board_widgets[game_id]
        
        try:
            # Set the lastmove argument to highlight the last move
            last_move = None
            move_history = self.game_info[game_id].get("move_history", [])
            if move_history:
                try:
                    last_move_str = move_history[-1]
                    from_square = chess.parse_square(last_move_str[:2])
                    to_square = chess.parse_square(last_move_str[2:4])
                    last_move = chess.Move(from_square, to_square)
                except (ValueError, IndexError) as e:
                    logger.warning(f"Could not parse last move for {game_id}: {str(e)}")
            
            # Convert board to SVG - highlight the last move
            svg_data = chess.svg.board(board, size=350, lastmove=last_move)
            
            # Convert SVG to PNG
            png_data = svg2png(bytestring=svg_data)
            
            # Convert PNG to PhotoImage
            image = Image.open(io.BytesIO(png_data))
            photo = ImageTk.PhotoImage(image)
            
            # Update label
            board_widget.configure(image=photo)
            board_widget.image = photo  # Prevent garbage collection
        except Exception as e:
            error_msg = f"Error updating board display for {game_id}: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
    
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
        
        logger.info(f"Rearranged {num_games} boards")
    
    def check_for_missing_games(self):
        """Check for game files that were previously displayed but are now missing."""
        current_time = time.time()
        games_to_remove = []
        
        # Find games that haven't been seen for a while
        for game_id in list(self.displayed_games):
            last_seen = self.game_last_seen.get(game_id, 0)
            time_since_last_seen = current_time - last_seen
            
            if time_since_last_seen > self.game_timeout:
                # Game has been missing for too long, mark for removal
                games_to_remove.append(game_id)
                logger.info(f"Game {game_id} hasn't been seen for {time_since_last_seen:.1f} seconds, removing")
        
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
                
            if game_id in self.game_state_hashes:
                del self.game_state_hashes[game_id]
                
            self.displayed_games.remove(game_id)
            
        if games_to_remove:
            self.rearrange_boards()
    
    def monitor_files(self):
        """Monitor all game files for changes and look for new files."""
        while self.running:
            try:
                # Check for new game files
                self.find_game_files()
                
                # Check each file for content changes (not just modification time)
                game_files_sorted = sorted(self.game_files)
                for i, game_file in enumerate(game_files_sorted):
                    if os.path.exists(game_file):
                        try:
                            # Get current hash
                            current_hash = self.compute_game_state_hash(game_file)
                            if current_hash is None:
                                continue
                                
                            # Get game ID
                            game_id = os.path.basename(game_file).replace('.json', '')
                            
                            # Check if content has changed
                            if game_id not in self.game_state_hashes or self.game_state_hashes[game_id] != current_hash:
                                # Content has changed, update display
                                cols = min(3, len(game_files_sorted))
                                
                                # Schedule update on main thread
                                def update_game(gf=game_file, idx=i, c=cols):
                                    self.create_or_update_game_display(gf, idx, c)
                                    
                                self.root.after(0, update_game)
                        except Exception as e:
                            logger.error(f"Error processing file {game_file}: {str(e)}")
                
                # Check for missing games every cycle
                self.root.after(0, self.check_for_missing_games)
                
                # Sleep between checks
                time.sleep(self.refresh_rate)
                
            except Exception as e:
                error_msg = f"Error monitoring files: {str(e)}"
                logger.error(error_msg)
                self.status_var.set(error_msg)
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
    
    parser = argparse.ArgumentParser(description='Chess Games Monitor')
    parser.add_argument('--games', type=str, default='chess_autosaves/game_id_*.json',
                        help='Pattern to match game files (supports wildcards)')
    parser.add_argument('--refresh', type=float, default=1.0,
                        help='Refresh rate in seconds')
    parser.add_argument('--timeout', type=float, default=20.0,
                        help='How long to wait before removing a missing game (in seconds)')
    args = parser.parse_args()
    
    # Start the monitor
    monitor = ChessBoardMonitor(
        games_pattern=args.games, 
        refresh_rate=args.refresh,
        game_timeout=args.timeout
    )
    monitor.run()


if __name__ == "__main__":
    main()
