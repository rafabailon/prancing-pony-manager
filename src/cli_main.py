"""Command-line entry point for Prancing Pony Manager."""

from __future__ import annotations

import argparse
import random
import sys

from game import Game
from models import Tavern
from persistence import SaveError, load_game, save_game
from terminal_ui import TerminalApp

__version__ = "1.1.0"


def _tavern_name(value: str) -> str:
    name = value.strip()
    if not name:
        raise argparse.ArgumentTypeError("The tavern name cannot be empty.")
    return name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prancing-pony",
        description="Manage a fantasy tavern in Prancing Pony Manager.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Seed the random event sequence for repeatable runs.",
    )
    parser.add_argument(
        "--name",
        type=_tavern_name,
        default="The Prancing Pony",
        help="Name of your tavern.",
    )
    parser.add_argument(
        "--load",
        metavar="FILE",
        help="Load a previously saved game from FILE.",
    )
    parser.add_argument(
        "--save",
        metavar="FILE",
        help="Write the game state to FILE when you leave the tavern.",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear the terminal before starting.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.load:
            game = load_game(args.load, rng=random.Random(args.seed))
        else:
            game = Game(tavern=Tavern(name=args.name), rng=random.Random(args.seed))
    except SaveError as exc:
        parser.error(str(exc))

    status = 0
    try:
        TerminalApp(game=game, clear_screen=args.clear).run()
    finally:
        if args.save:
            try:
                save_game(game, args.save)
            except OSError as exc:
                print(f"Could not save game: {exc}", file=sys.stderr)
                status = 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
