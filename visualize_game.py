import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageFont
import os
import sys
from pathlib import Path

class ChessBoardDisplay:
    """A class to display chess positions from FEN strings in a Tkinter window."""
    
    def __init__(self, root=None):
        """
        Initialize the chess board display.
        
        Args:
            root: Optional Tkinter root window. If None, a new one will be created.
        """
        # Create the main window if not provided
        self.root_provided = root is not None
        self.root = root or tk.Tk()
        self.root.title("Chess Board - FEN Viewer")
        
        # Create main frame for the board
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(padx=10, pady=10)
        
        # Create the board frame (will be recreated for each new position)
        self.board_frame = None
        
        # Dictionary for piece to filename mapping
        self.piece_files = {
            'p': 'bp.png', 'n': 'bn.png', 'b': 'bb.png', 'r': 'br.png', 'q': 'bq.png', 'k': 'bk.png',
            'P': 'wp.png', 'N': 'wn.png', 'B': 'wb.png', 'R': 'wr.png', 'Q': 'wq.png', 'K': 'wk.png'
        }
        
        # Colors for the board squares
        self.light_color = "#EBECD0"  # Light square
        self.dark_color = "#779556"   # Dark square
        
        # Create reference for the FEN label
        self.fen_label = tk.Label(self.root, text="", font=('Arial', 10))
        self.fen_label.pack(pady=5)
        
        # Add a button to close the window if we created the root
        if not self.root_provided:
            close_button = tk.Button(self.root, text="Close", command=self.root.destroy)
            close_button.pack(pady=5)
    
    def ensure_piece_image(self, piece_char):
        """Make sure the piece image exists, creating a placeholder if needed."""
        pieces_dir = Path("pieces")
        pieces_dir.mkdir(exist_ok=True)
        
        filename = self.piece_files[piece_char]
        filepath = pieces_dir / filename
        
        if not filepath.exists():
            print(f"Creating placeholder for {piece_char} ({filename})")
            self.create_placeholder_piece(piece_char, filepath)
        
        return filepath
    
    def create_placeholder_piece(self, piece_char, filepath):
        """Create a simple colored rectangle with a letter as a placeholder for a chess piece."""
        color = "black" if piece_char.islower() else "white"
        text_color = "white" if piece_char.islower() else "black"
        
        img = Image.new('RGB', (60, 60), color=color)
        draw = ImageDraw.Draw(img)
        
        # Try to use a system font, default to a simple solution if not available
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except IOError:
            font = ImageFont.load_default()
        
        # Draw the piece letter in the center
        letter = piece_char.upper()
        
        # Handle text sizing with different Pillow versions
        # Method 1: For Pillow >= 9.2.0
        if hasattr(draw, 'textbbox'):
            bbox = draw.textbbox((0, 0), letter, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        # Method 2: For Pillow < 9.2.0 but >= 8.0.0
        elif hasattr(font, 'getbbox'):
            bbox = font.getbbox(letter)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        # Method 3: Fallback for older Pillow versions
        else:
            # Approximate the size based on the font size
            text_width, text_height = 20, 30  # Reasonable defaults
            
        position = ((60 - text_width) // 2, (60 - text_height) // 2)
        draw.text(position, letter, fill=text_color, font=font)
        
        img.save(filepath)
    
    def display_position(self, fen_string):
        """
        Display a chess position from a FEN string.
        
        Args:
            fen_string (str): A valid FEN string representing a chess position
        """
        # Extract the board part of the FEN (first part before any spaces)
        board_part = fen_string.split()[0]
        
        # Clear the previous board if it exists
        if self.board_frame:
            self.board_frame.destroy()
        
        # Create a new board frame
        self.board_frame = tk.Frame(self.main_frame)
        self.board_frame.pack()
        
        # Update the FEN label
        self.fen_label.config(text=f"FEN: {fen_string}")
        
        # Variables to store references to the images to prevent garbage collection
        self.piece_images = {}
        
        # Parse the FEN
        rows = board_part.split('/')
        
        # Add column labels (a-h)
        for col in range(8):
            label = tk.Label(self.board_frame, text=chr(97 + col), font=('Arial', 12))
            label.grid(row=8, column=col)
        
        # Create the board squares and place pieces
        for i, row in enumerate(rows):
            # Add row labels (8-1)
            rank = 8 - i
            label = tk.Label(self.board_frame, text=str(rank), font=('Arial', 12))
            label.grid(row=i, column=8)
            
            col = 0
            for char in row:
                if char.isdigit():
                    # Add the specified number of empty squares
                    empty_count = int(char)
                    for j in range(empty_count):
                        color = self.dark_color if (i + col) % 2 == 1 else self.light_color
                        square = tk.Label(self.board_frame, width=8, height=4, bg=color)
                        square.grid(row=i, column=col)
                        col += 1
                else:
                    # Add a square with a piece
                    color = self.dark_color if (i + col) % 2 == 1 else self.light_color
                    square = tk.Label(self.board_frame, width=8, height=4, bg=color)
                    
                    # Get or create the appropriate piece image
                    piece_path = self.ensure_piece_image(char)
                    img = Image.open(piece_path)
                    resize_method = Image.ANTIALIAS if hasattr(Image, 'ANTIALIAS') else Image.LANCZOS
                    img = img.resize((50, 50), resize_method)
                    piece_img = ImageTk.PhotoImage(img)
                    
                    # Store the image reference to prevent garbage collection
                    self.piece_images[(i, col)] = piece_img
                    
                    # Configure the square to display the piece
                    square.configure(image=piece_img)
                    square.grid(row=i, column=col)
                    col += 1
        
        # Update the window
        self.root.update()
    
    def start_mainloop(self):
        """Start the Tkinter main loop if we created the root."""
        if not self.root_provided:
            self.root.mainloop()
    
    def close(self):
        """Close the window if we created the root."""
        if not self.root_provided:
            self.root.destroy()


def display_chess_board(fen_string):
    """
    Display a chess board in a graphical window based on a FEN string.
    This function creates a new window for each call.
    
    Args:
        fen_string (str): A valid FEN string representing a chess position
    """
    root = tk.Tk()
    board = ChessBoardDisplay(root)
    board.display_position(fen_string)
    root.mainloop()


def display_multiple_positions(fen_strings, delay_ms=2000):
    """
    Display multiple chess positions in sequence in the same window.
    
    Args:
        fen_strings (list): List of FEN strings to display
        delay_ms (int): Delay between positions in milliseconds
    """
    root = tk.Tk()
    board = ChessBoardDisplay(root)
    
    def show_next_position(positions, index=0):
        if index < len(positions):
            board.display_position(positions[index])
            root.after(delay_ms, show_next_position, positions, index + 1)
    
    # Start showing positions
    show_next_position(fen_strings)
    
    # Start the main loop
    root.mainloop()


# Example usage
if __name__ == "__main__":
    # If arguments are provided, display each one as a separate board
    if len(sys.argv) > 1:
        for fen in sys.argv[1:]:
            display_chess_board(fen)
    else:
        # Example: Show a sequence of moves in the same window
        sample_positions = [
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # Starting position
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",  # After 1. e4
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",  # After 1... e5
            "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2",  # After 2. Nf3
        ]
        
        print("Displaying a sequence of moves. Window will close automatically after showing all positions.")
        display_multiple_positions(sample_positions)
