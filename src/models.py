"""Core game models and resource rules for Prancing Pony Manager."""

from __future__ import annotations

from dataclasses import dataclass, field


def _clamp(value: int, minimum: int, maximum: int) -> int:
    """Return ``value`` constrained to the inclusive ``[minimum, maximum]`` range."""
    return max(minimum, min(value, maximum))


@dataclass(slots=True)
class Tavern:
    """Mutable state for the tavern; resource changes stay within valid bounds."""

    name: str = "The Prancing Pony"
    gold: int = 24
    provisions: int = 12
    reputation: int = 5
    satisfaction: int = 65
    day: int = 1
    max_reputation: int = 100
    max_satisfaction: int = 100
    max_provisions: int = 30
    max_history: int = 500
    history: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("The tavern must have a name.")
        self.name = self.name.strip()
        if min(self.max_reputation, self.max_satisfaction, self.max_provisions) < 1:
            raise ValueError("Maximum resource limits must be greater than zero.")
        if self.max_history < 1:
            raise ValueError("The history limit must be greater than zero.")
        if self.day < 1:
            raise ValueError("The day must be greater than zero.")
        if min(self.gold, self.provisions, self.reputation, self.satisfaction) < 0:
            raise ValueError("Starting resources cannot be negative.")
        self.provisions = min(self.provisions, self.max_provisions)
        self.reputation = min(self.reputation, self.max_reputation)
        self.satisfaction = min(self.satisfaction, self.max_satisfaction)
        if len(self.history) > self.max_history:
            del self.history[: -self.max_history]

    def change_gold(self, amount: int) -> bool:
        """Apply a gold change, rejecting costs the tavern cannot afford."""
        if self.gold + amount < 0:
            return False
        self.gold += amount
        return True

    def change_provisions(self, amount: int) -> int:
        """Apply a provision change and return the amount actually applied."""
        before = self.provisions
        self.provisions = _clamp(self.provisions + amount, 0, self.max_provisions)
        return self.provisions - before

    def change_reputation(self, amount: int) -> int:
        """Apply a reputation change and return the amount actually applied."""
        before = self.reputation
        self.reputation = _clamp(self.reputation + amount, 0, self.max_reputation)
        return self.reputation - before

    def change_satisfaction(self, amount: int) -> int:
        """Apply a satisfaction change and return the amount actually applied."""
        before = self.satisfaction
        self.satisfaction = _clamp(self.satisfaction + amount, 0, self.max_satisfaction)
        return self.satisfaction - before

    def record(self, message: str) -> None:
        """Append a message to the ledger, keeping memory use bounded."""
        self.history.append(message)
        if len(self.history) > self.max_history:
            del self.history[: -self.max_history]
