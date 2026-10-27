# Prancing Pony Manager

A cozy fantasy tavern-management game for the terminal. Keep the hearth warm, serve adventurers, protect your pantry, and make the choices that turn a modest inn into a legend. Written in Python with **no third-party runtime dependencies**.

## Requirements

- Python 3.10 or later
- No additional packages required

## Quick start

From the project root:

```sh
make run
```

Or run the entry point directly:

```sh
PYTHONPATH=src python3 src/cli_main.py
```

Customise the tavern, use a reproducible event sequence, or clear the terminal before launch:

```sh
PYTHONPATH=src python3 src/cli_main.py --name "The Crooked Moon" --seed 7 --clear
```

Install the command-line entry points if you prefer:

```sh
python3 -m pip install -e .
prancing-pony --seed 7
prancing-pony-manager --seed 7
```

## How to play

You get **two actions per day**:

1. **Serve the house stew** — spend provisions to earn gold and satisfaction.
2. **Restock provisions** — buy supplies for the pantry.
3. **Promote the tavern** — spend gold to gain reputation and satisfaction.
4. **End the day** — trigger the nightly service and the next event.

Every day also brings a random encounter with two or three choices. Choices can cost gold or provisions, but they can also earn reputation, satisfaction, and story. At night, guests arrive based on your reputation; every guest without a meal lowers satisfaction. The run ends if satisfaction reaches zero, or if the tavern is left with neither gold nor provisions.

Enter the number of an option when prompted. Enter `Q` to quit at any prompt.

## Saving and loading

Saves are human-readable JSON files and are written atomically, so an interrupted save cannot leave a half-written file behind.

```sh
# Save when you leave the tavern
PYTHONPATH=src python3 src/cli_main.py --save saves/pony.json

# Continue a previous run
PYTHONPATH=src python3 src/cli_main.py --load saves/pony.json
```

Saved games include the tavern state, economy configuration, the pending event, the bounded ledger of recent results, and the random generator state. Loading validates the file and reports a clear error for missing, corrupt, unsupported, or out-of-range data.

## Command-line options

| Option | Description |
| --- | --- |
| `--name NAME` | Name of the tavern (default: `The Prancing Pony`). |
| `--seed N` | Seed the random event sequence for repeatable runs. |
| `--load FILE` | Load a saved game. |
| `--save FILE` | Save the game when you leave the tavern. |
| `--clear` | Clear the terminal before starting. |
| `--version` | Show the installed version. |

## Tests

The suite uses the standard-library `unittest` framework and covers models, events, game rules, persistence, terminal input handling, and the CLI:

```sh
make test
```

The equivalent command is:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

`make check` compiles every module and runs the suite without verbose output. `make clean` removes caches and temporary files.

## Project structure

The code lives directly in `src/`; there are no nested implementation packages.

```text
src/models.py       Tavern state, resource bounds, and the event ledger
src/events.py       Random encounters, choices, and consequences
src/game.py         Economy rules and the daily game loop
src/persistence.py  Validated, atomic JSON save/load support
src/terminal_ui.py  Testable terminal interface and dashboard
src/cli_main.py     Command-line arguments and entry point
tests/test_models.py
tests/test_events.py
tests/test_game.py
tests/test_persistence.py
tests/test_cli.py
```

## Design notes

- **Deterministic when asked:** `--seed` reproduces the same event sequence and the random state is preserved across saves.
- **Defensive by default:** resource changes are clamped, unaffordable actions leave state untouched, and save files are validated before a game is created.
- **Bounded memory:** the tavern ledger keeps only the most recent entries.
- **Testable UI:** terminal input and output are injected, so the full game loop can be exercised without a real terminal.
- **No external services:** the game runs entirely locally and offline.
