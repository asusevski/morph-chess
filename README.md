# Morph Chess - LLM-Powered Chess Agent

Morph Chess is a project that enables an LLM (Large Language Model) to play chess against a computer opponent. The LLM plays as White, making moves based on the current board state, while the computer plays as Black with random moves.

## Features

- Play chess with an LLM making moves for White
- Configurable with different LLM providers (OpenAI, Hugging Face, etc.)
- Customizable game settings
- Save and load functionality to continue games
- Auto-save capability to prevent losing game progress
- Visual board representation in the console

## Requirements

- Python 3.10 or higher
- Dependencies listed in pyproject.toml

## Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/morph-chess.git
cd morph-chess
```

2. Install dependencies using pip:

```bash
pip install -e .
```

3. Set up API keys as environment variables for your chosen LLM provider:

For OpenAI:
```bash
export OPENAI_API_KEY=your_api_key_here
```

For Hugging Face:
```bash
export HF_API_KEY=your_api_key_here
```

## Configuration

The project is configured via `config.yaml`. You can adjust:

- LLM provider and model settings
- Chess game parameters

Example configuration:

```yaml
llm:
  provider: "openai"
  model_id: "gpt-4o"
  api_key_env: "OPENAI_API_KEY"
  max_tokens: 100

# Alternative configuration using Hugging Face
# llm:
#   provider: "hf-inference"
#   model_id: "meta-llama/Llama-3.3-70B-Instruct"
#   api_key_env: "HF_API_KEY"
#   max_tokens: 100

chess:
  max_moves: 2  # Maximum number of moves to play
  autosave: true  # Automatically save the game after each move
```

## Usage

### Running the Agent

The main script for playing chess is `agent.py`. It can be run with several command-line options:

```bash
python agent.py [options]
```

#### Command-line options:

- `--chess PATH`: Path to the chess game script (default: ./chess_game.py)
- `--load FILE`: Load a saved game from a file
- `--no-autosave`: Disable automatic saving of game state
- `--moves N`: Maximum number of moves to play before stopping
- `--debug`: Enable debug output
- `--config PATH`: Path to configuration file (default: config.yaml)
- `--game-id ID`: Specify a custom game ID for the session

#### Examples:

Start a new game with default settings:
```bash
python agent.py
```

Load a previously saved game:
```bash
python agent.py --load chess_autosaves/game_id_1234.json
```

Play a game with a limit of 10 moves:
```bash
python agent.py --moves 10
```

Use a specific configuration file:
```bash
python agent.py --config my_config.yaml
```

### Using the entrypoint.sh Script

For convenience, you can also use the `entrypoint.sh` script:

```bash
chmod +x entrypoint.sh  # Make the script executable
./entrypoint.sh
```

This script starts a new game with a predefined game ID (1234) and ensures the autosave directory exists.

