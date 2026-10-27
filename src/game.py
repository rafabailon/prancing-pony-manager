"""Game rules, daily actions, and tavern end-of-day simulation."""

from __future__ import annotations

import random
from dataclasses import dataclass

from events import EventManager, TavernEvent
from models import Tavern


@dataclass(frozen=True, slots=True)
class GameConfig:
    """Tunable economy rules; defaults are balanced for a short, cozy run."""

    actions_per_day: int = 2
    meal_price: int = 5
    meal_provisions: int = 2
    meal_satisfaction: int = 4
    restock_cost: int = 8
    restock_amount: int = 6
    reputation_cost: int = 4
    promotion_reputation: int = 3
    promotion_satisfaction: int = 2

    def __post_init__(self) -> None:
        if self.actions_per_day < 1:
            raise ValueError("There must be at least one action per day.")
        positive = (
            self.meal_price,
            self.meal_provisions,
            self.meal_satisfaction,
            self.restock_cost,
            self.restock_amount,
            self.reputation_cost,
            self.promotion_reputation,
            self.promotion_satisfaction,
        )
        if min(positive) < 1:
            raise ValueError("Costs, rewards, and quantities must be positive.")


class Game:
    """Coordinates the rules while leaving input/output to the command-line layer."""

    def __init__(
        self,
        tavern: Tavern | None = None,
        rng: random.Random | None = None,
        config: GameConfig | None = None,
    ) -> None:
        self.tavern = tavern or Tavern()
        self.rng = rng or random.Random()
        self.config = config or GameConfig()
        self.events = EventManager(self.rng)
        self.actions_left = self.config.actions_per_day
        self.is_over = False
        self.last_event: TavernEvent | None = None

    def serve_meal(self) -> str:
        if self.actions_left < 1:
            return "No actions remain today."
        if self.tavern.provisions < self.config.meal_provisions:
            return f"Not enough provisions; you need {self.config.meal_provisions}."
        self.tavern.change_provisions(-self.config.meal_provisions)
        self.tavern.change_gold(self.config.meal_price)
        satisfaction = self.tavern.change_satisfaction(self.config.meal_satisfaction)
        self.actions_left -= 1
        message = (
            f"You serve the house stew: +{self.config.meal_price} gold, "
            f"-{self.config.meal_provisions} provisions, +{satisfaction} satisfaction."
        )
        self.tavern.record(message)
        return message

    def restock(self) -> str:
        if self.actions_left < 1:
            return "No actions remain today."
        if self.tavern.provisions >= self.tavern.max_provisions:
            return "The pantry is already full."
        if not self.tavern.change_gold(-self.config.restock_cost):
            return f"Not enough gold; restocking costs {self.config.restock_cost}."
        amount = self.tavern.change_provisions(self.config.restock_amount)
        self.actions_left -= 1
        message = f"You buy provisions: -{self.config.restock_cost} gold, +{amount} provisions."
        self.tavern.record(message)
        return message

    def promote_tavern(self) -> str:
        if self.actions_left < 1:
            return "No actions remain today."
        if (
            self.tavern.reputation >= self.tavern.max_reputation
            and self.tavern.satisfaction >= self.tavern.max_satisfaction
        ):
            return "Word of the tavern is already legendary; promotion would be wasted."
        if not self.tavern.change_gold(-self.config.reputation_cost):
            return f"Not enough gold; promotion costs {self.config.reputation_cost}."
        reputation = self.tavern.change_reputation(self.config.promotion_reputation)
        satisfaction = self.tavern.change_satisfaction(self.config.promotion_satisfaction)
        self.actions_left -= 1
        message = (
            f"A town crier promotes the tavern: -{self.config.reputation_cost} gold, "
            f"+{reputation} reputation, +{satisfaction} satisfaction."
        )
        self.tavern.record(message)
        return message

    def resolve_event(self, choice_index: int) -> str:
        if self.last_event is None:
            raise RuntimeError("There is no event to resolve.")
        event = self.last_event
        result = self.events.resolve(event, choice_index, self.tavern)
        self.last_event = None
        return result

    def close_day(self) -> str:
        """Run nightly customer flow, trigger the next day and check defeat conditions."""
        if self.is_over:
            return "The game is already over."

        guests = max(1, 2 + self.tavern.reputation // 12 + self.rng.randint(-1, 1))
        meals = min(guests, self.tavern.provisions // self.config.meal_provisions)
        missed = guests - meals
        self.tavern.change_provisions(-meals * self.config.meal_provisions)
        earned = meals * self.config.meal_price
        self.tavern.change_gold(earned)
        satisfaction_change = min(5, meals) - missed * 5
        self.tavern.change_satisfaction(satisfaction_change)
        if meals:
            self.tavern.change_reputation(1 if missed == 0 else 0)

        result = f"The night ends: {guests} guests, {meals} meals served, +{earned} gold."
        if missed:
            result += f" {missed} guests go without dinner."
        self.tavern.record(result)
        self.actions_left = self.config.actions_per_day
        self.tavern.day += 1

        if self.tavern.satisfaction <= 0:
            self.is_over = True
            result += " The guests have lost patience: the tavern closes."
        elif self.tavern.gold <= 0 and self.tavern.provisions <= 0:
            self.is_over = True
            result += " With no gold or provisions left, the tavern must close."
        if self.is_over:
            self.actions_left = 0
        return result

    def draw_event(self) -> TavernEvent:
        if self.last_event is None:
            self.last_event = self.events.next_event()
        return self.last_event
