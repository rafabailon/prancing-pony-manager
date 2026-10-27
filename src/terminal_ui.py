"""Terminal interface for Prancing Pony Manager."""

from __future__ import annotations

import os
import time
import unicodedata
from collections.abc import Callable

from game import Game

Input = Callable[[str], str]
Output = Callable[[str], None]

_BOX_INNER_WIDTH = 60


def _character_width(character: str) -> int:
    if unicodedata.combining(character):
        return 0
    return 2 if unicodedata.east_asian_width(character) in {"F", "W"} else 1


def _display_width(text: str) -> int:
    return sum(_character_width(character) for character in text)


def _fit(text: str, width: int) -> str:
    """Pad or truncate ``text`` so its terminal width is exactly ``width``."""
    if _display_width(text) > width:
        kept: list[str] = []
        used = 0
        for character in text:
            character_width = _character_width(character)
            if used + character_width > width - 1:
                break
            kept.append(character)
            used += character_width
        text = "".join(kept).rstrip() + "…"
    return text + " " * (width - _display_width(text))


def _pair(left: str, right: str, width: int) -> str:
    gap = max(1, width - _display_width(left) - _display_width(right))
    return left + " " * gap + right


class TerminalApp:
    """Small, testable console UI with injectable input/output functions."""

    def __init__(
        self,
        game: Game | None = None,
        input_fn: Input = input,
        output_fn: Output = print,
        clear_screen: bool = False,
        pause: float = 0.0,
    ) -> None:
        self.game = game or Game()
        self.input = input_fn
        self.output = output_fn
        self.clear_screen = clear_screen
        self.pause = max(0.0, pause)

    def _clear(self) -> None:
        if self.clear_screen:
            os.system("cls" if os.name == "nt" else "clear")

    def show_dashboard(self) -> None:
        tavern = self.game.tavern
        width = _BOX_INNER_WIDTH
        border = "═" * width
        day_label = f"DAY {tavern.day}  "
        name_label = _fit(f"  🐴  {tavern.name}", width - _display_width(day_label) - 1)
        title = _pair(name_label, day_label, width)
        resources = (
            f"  Gold: {tavern.gold:>4}   Provisions: {tavern.provisions:>3}   "
            f"Reputation: {tavern.reputation:>3}/{tavern.max_reputation:<3}"
        )
        status = (
            f"  Satisfaction: {tavern.satisfaction:>3}/{tavern.max_satisfaction:<3}   "
            f"Actions left: {self.game.actions_left:<2}"
        )
        self.output(
            "\n"
            f"╔{border}╗\n"
            f"║{_fit(title, width)}║\n"
            f"╠{border}╣\n"
            f"║{_fit(resources, width)}║\n"
            f"║{_fit(status, width)}║\n"
            f"╚{border}╝"
        )

    def _read_choice(self, prompt: str, minimum: int, maximum: int) -> int | None:
        try:
            raw = self.input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if raw.lower() in {"q", "quit", "exit"}:
            return None
        try:
            choice = int(raw)
        except ValueError:
            self.output("Enter a valid option number (or Q to quit).")
            return -1
        if not minimum <= choice <= maximum:
            self.output(f"Choose a number between {minimum} and {maximum}.")
            return -1
        return choice

    def _manage_day(self) -> bool:
        actions = (
            ("Serve the house stew", self.game.serve_meal),
            ("Restock provisions", self.game.restock),
            ("Promote the tavern", self.game.promote_tavern),
        )
        while self.game.actions_left > 0 and not self.game.is_over:
            self.show_dashboard()
            self.output("What will you do before nightfall?")
            for index, (label, _) in enumerate(actions, start=1):
                self.output(f"  {index}. {label}")
            self.output("  4. End the day")
            choice = self._read_choice("> ", 1, 4)
            if choice is None:
                return False
            if choice == -1:
                continue
            if choice == 4:
                break
            self.output(actions[choice - 1][1]())
        return True

    def _run_event(self) -> bool:
        event = self.game.draw_event()
        self.output(f"\n⚡ EVENT: {event.title}\n{event.description}")
        for index, choice in enumerate(event.choices, start=1):
            self.output(f"  {index}. {choice.label} — {choice.consequence}")
        selected = self._read_choice("> ", 1, len(event.choices))
        while selected == -1:
            selected = self._read_choice("> ", 1, len(event.choices))
        if selected is None:
            return False
        self.output(self.game.resolve_event(selected - 1))
        return True

    def run(self) -> None:
        self._clear()
        title = "PRANCING PONY MANAGER · FANTASY TAVERN MANAGEMENT"
        self.output(f"╭{'─' * 58}╮")
        self.output(f"│{_fit(title.center(58), 58)}│")
        self.output(f"╰{'─' * 58}╯")
        self.output("Serve meals, earn renown, and keep adventurers from burning the place down.")
        self.output("Enter Q at any time to close the ledger.\n")

        while not self.game.is_over:
            if not self._manage_day() or not self._run_event():
                break
            self.output(self.game.close_day())
            if self.pause:
                time.sleep(self.pause)
        self.show_dashboard()
        self.output("Thanks for looking after the tavern. May the roads rise to meet you!")
