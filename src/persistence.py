"""Safe JSON persistence for Prancing Pony Manager.

The format is intentionally small and human readable. Loading is defensive:
unknown or malformed data raises :class:`SaveFormatError` instead of leaving a
half-broken game in memory.
"""

from __future__ import annotations

import json
import os
import random
import tempfile
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any

from game import Game, GameConfig
from models import Tavern

SAVE_VERSION = 1

_TAVERN_FIELDS = {item.name for item in fields(Tavern)}
_CONFIG_FIELDS = {item.name for item in fields(GameConfig)}


class SaveError(Exception):
    """Base class for persistence failures that are safe to show to players."""


class SaveNotFoundError(SaveError):
    """Raised when the requested save file does not exist."""


class SaveFormatError(SaveError):
    """Raised when a save file is unreadable or contains invalid data."""


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SaveFormatError(f"{label} must be a JSON object.")
    return value


def _integer(
    data: dict[str, Any],
    key: str,
    label: str,
    *,
    minimum: int | None = None,
) -> int:
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise SaveFormatError(f"{label}.{key} must be an integer.")
    if minimum is not None and value < minimum:
        raise SaveFormatError(f"{label}.{key} must be at least {minimum}.")
    return value


def _encode_rng_state(value: Any) -> Any:
    """Convert the nested tuples returned by ``Random.getstate`` to JSON lists."""
    if isinstance(value, tuple):
        return [_encode_rng_state(item) for item in value]
    return value


def _decode_rng_state(value: Any) -> Any:
    """Convert JSON lists back into the tuples expected by ``Random.setstate``."""
    if isinstance(value, list):
        return tuple(_decode_rng_state(item) for item in value)
    return value


def _tavern_from_dict(data: Any) -> Tavern:
    values = _mapping(data, "tavern")
    unknown = set(values) - _TAVERN_FIELDS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise SaveFormatError(f"Unknown tavern field(s): {names}.")

    name = values.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SaveFormatError("tavern.name must be a non-empty string.")

    for key in _TAVERN_FIELDS - {"name", "history"}:
        if key not in values:
            raise SaveFormatError(f"tavern.{key} is missing.")
        _integer(values, key, "tavern", minimum=0 if key not in {
            "day", "max_reputation", "max_satisfaction", "max_provisions", "max_history"
        } else 1)

    history = values.get("history", [])
    if not isinstance(history, list) or not all(isinstance(item, str) for item in history):
        raise SaveFormatError("tavern.history must be a list of strings.")
    values = {**values, "history": list(history)}

    try:
        return Tavern(**values)
    except (TypeError, ValueError) as exc:
        raise SaveFormatError(f"Invalid tavern state: {exc}") from exc


def _config_from_dict(data: Any) -> GameConfig:
    if data is None:
        return GameConfig()
    values = _mapping(data, "config")
    unknown = set(values) - _CONFIG_FIELDS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise SaveFormatError(f"Unknown config field(s): {names}.")

    for key in values:
        _integer(values, key, "config", minimum=1)
    try:
        return GameConfig(**values)
    except (TypeError, ValueError) as exc:
        raise SaveFormatError(f"Invalid game configuration: {exc}") from exc


def game_to_dict(game: Game) -> dict[str, Any]:
    """Build a JSON-serialisable snapshot of ``game``."""
    return {
        "version": SAVE_VERSION,
        "tavern": asdict(game.tavern),
        "config": asdict(game.config),
        "state": {
            "actions_left": game.actions_left,
            "is_over": game.is_over,
            "last_event": game.last_event.title if game.last_event else None,
        },
        "rng_state": _encode_rng_state(game.rng.getstate()),
    }


def save_game(game: Game, path: str | os.PathLike[str]) -> Path:
    """Atomically write ``game`` to ``path`` and return the resolved path."""
    destination = Path(path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = game_to_dict(game)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.",
        suffix=".tmp",
        dir=destination.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, destination)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise
    return destination


def load_game(path: str | os.PathLike[str], rng: random.Random | None = None) -> Game:
    """Load a game from ``path``, raising :class:`SaveError` on bad input."""
    source = Path(path).expanduser()
    try:
        raw = source.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SaveNotFoundError(f"Save file not found: {source}") from exc
    except OSError as exc:
        raise SaveError(f"Could not read save file: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SaveFormatError(f"Save file is not valid JSON: {exc}") from exc

    payload = _mapping(payload, "save")
    version = payload.get("version")
    if isinstance(version, bool) or version != SAVE_VERSION:
        raise SaveFormatError(
            f"Unsupported save version {version!r}; expected {SAVE_VERSION}."
        )
    if "tavern" not in payload:
        raise SaveFormatError("save.tavern is missing.")

    tavern = _tavern_from_dict(payload["tavern"])
    config = _config_from_dict(payload.get("config"))
    state = _mapping(payload.get("state", {}), "state")

    actions_left = state.get("actions_left", config.actions_per_day)
    if isinstance(actions_left, bool) or not isinstance(actions_left, int):
        raise SaveFormatError("state.actions_left must be an integer.")
    if not 0 <= actions_left <= config.actions_per_day:
        raise SaveFormatError(
            f"state.actions_left must be between 0 and {config.actions_per_day}."
        )

    is_over = state.get("is_over", False)
    if not isinstance(is_over, bool):
        raise SaveFormatError("state.is_over must be a boolean.")

    game_rng = rng or random.Random()
    rng_state = payload.get("rng_state")
    if rng_state is not None:
        try:
            game_rng.setstate(_decode_rng_state(rng_state))
        except (TypeError, ValueError) as exc:
            raise SaveFormatError("save.rng_state is invalid.") from exc

    game = Game(tavern=tavern, rng=game_rng, config=config)
    game.actions_left = actions_left
    game.is_over = is_over

    last_event_title = state.get("last_event")
    if last_event_title is not None:
        if not isinstance(last_event_title, str):
            raise SaveFormatError("state.last_event must be a string or null.")
        event = game.events.get_event(last_event_title)
        if event is None:
            raise SaveFormatError(f"Unknown pending event: {last_event_title}.")
        game.last_event = event
    return game
