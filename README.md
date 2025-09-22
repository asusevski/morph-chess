# Chess Cloud Orchestrator

A distributed chess system that runs multiple chess agents on cloud instances with real-time visualization.

## Components

- **`orchestrator.py`** - Main orchestrator that manages cloud instances, deploys chess agents, and synchronizes game states
- **`chess_engine.py`** - Core chess engine with move validation, position evaluation, and save/load functionality
- **`chess_game.py`** - Interactive chess game for playing against computer opponents locally
- **`chess_monitor.py`** - Real-time GUI that visualizes multiple chess games simultaneously
- **`config.yaml`** - Configuration for agents, chess settings, and LLM parameters

## Usage

### Run distributed chess games:
```bash
uv run orchestrator.py
```

### Monitor games locally (run separately):
```bash
uv run chess_monitor.py
```

### Play interactively:
```bash
python chess_game.py --autosave --strategy aggressive
```

## Features

- **Cloud deployment**: Automatically provisions instances and deploys agents
- **Game synchronization**: Real-time sync of game states from cloud to local storage
- **Live visualization**: GUI showing multiple chess boards with move highlighting
- **Configurable strategies**: Support for aggressive, defensive, and balanced play styles
- **Auto-save**: Persistent game state storage with JSON format
