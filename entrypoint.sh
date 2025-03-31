#!/bin/bash

# Set the game ID (you can change this to any value)
GAME_ID=1234

# Create the autosave directory if it doesn't exist
mkdir -p chess_autosaves

# Run the agent script with autosave enabled and specific game ID
# The game ID will be passed to chess_game.py via --game-id parameter
# This allows for consistent game IDs across runs
python agent.py --chess ./chess_game.py --game-id $GAME_ID
