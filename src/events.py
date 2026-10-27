"""Random tavern events and their player choices."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

from models import Tavern


@dataclass(frozen=True, slots=True)
class Choice:
    label: str
    consequence: str
    apply: Callable[[Tavern], str]


@dataclass(frozen=True, slots=True)
class TavernEvent:
    title: str
    description: str
    choices: tuple[Choice, ...]


def _bard_coin(tavern: Tavern) -> str:
    if not tavern.change_gold(-3):
        tavern.change_satisfaction(-4)
        return "You cannot afford the bard. He leaves, singing about your stinginess. (-4 satisfaction)"
    tavern.change_satisfaction(8)
    tavern.change_reputation(2)
    return "The bard takes 3 gold; the crowd demands an encore. (+8 satisfaction, +2 reputation)"


def _bard_out(tavern: Tavern) -> str:
    tavern.change_satisfaction(-6)
    return "You politely escort him to the door. (-6 satisfaction)"


def _bard_song(tavern: Tavern) -> str:
    if not tavern.change_provisions(-1):
        tavern.change_satisfaction(-3)
        return "There is no dinner left for the bard. The song becomes a mournful ballad. (-3 satisfaction)"
    tavern.change_reputation(4)
    return "You pay him with a meal and a story. (-1 provision, +4 reputation)"


def _brawl_peace(tavern: Tavern) -> str:
    if not tavern.change_gold(-4):
        tavern.change_satisfaction(-6)
        return "You cannot afford a round. The brawl continues and satisfaction falls. (-6 satisfaction)"
    tavern.change_satisfaction(5)
    tavern.change_reputation(2)
    return "You buy a round for both sides. (-4 gold, +5 satisfaction, +2 reputation)"


def _brawl_bouncer(tavern: Tavern) -> str:
    tavern.change_satisfaction(-3)
    tavern.change_reputation(1)
    return "Your stern look is enough to separate them. (-3 satisfaction, +1 reputation)"


def _brawl_watch(tavern: Tavern) -> str:
    tavern.change_provisions(-2)
    tavern.change_satisfaction(-10)
    return "A table ends up in splinters. (-2 provisions, -10 satisfaction)"


def _wizard_stew(tavern: Tavern) -> str:
    tavern.change_gold(5)
    tavern.change_provisions(5)
    tavern.change_reputation(2)
    return "The wizard pays 5 gold for rare ingredients. (+5 gold, +5 provisions, +2 reputation)"


def _wizard_room(tavern: Tavern) -> str:
    if not tavern.change_gold(-4):
        tavern.change_satisfaction(-5)
        return "You cannot offer a room. (-5 satisfaction)"
    tavern.change_reputation(4)
    tavern.change_satisfaction(3)
    return "You rent him the quietest room. (-4 gold, +4 reputation, +3 satisfaction)"


def _wizard_refuse(tavern: Tavern) -> str:
    tavern.change_satisfaction(-2)
    return "You politely decline the request. (-2 satisfaction)"


def _lost_traveller(tavern: Tavern) -> str:
    if not tavern.change_provisions(-2):
        tavern.change_reputation(-1)
        tavern.change_satisfaction(-4)
        return "The pantry is empty. The traveller leaves cold and hungry. (-1 reputation, -4 satisfaction)"
    tavern.change_reputation(3)
    tavern.change_satisfaction(5)
    return "You serve a hot meal at cost. (-2 provisions, +3 reputation, +5 satisfaction)"


def _lost_coin(tavern: Tavern) -> str:
    tavern.change_gold(5)
    tavern.change_satisfaction(2)
    return "A grateful traveller leaves an unexpected tip. (+5 gold, +2 satisfaction)"


class EventManager:
    """Select one event per day from an injectable random generator."""

    def __init__(self, rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._events = self._build_events()

    @staticmethod
    def _build_events() -> tuple[TavernEvent, ...]:
        return (
            TavernEvent(
                "The Bard of Seven Verses",
                "A minstrel strides in, climbs onto a table, and starts rhyming the names of every guest.",
                (
                    Choice("Pay him to continue", "Costs 3 gold.", _bard_coin),
                    Choice("Ask him to leave", "The crowd may miss the entertainment.", _bard_out),
                    Choice("Trade dinner for a song", "Spend one provision to gain renown.", _bard_song),
                ),
            ),
            TavernEvent(
                "The Twin Axes Argument",
                "Two adventurers argue over whether a dragon should pay extra for a room.",
                (
                    Choice("Buy a round", "An expensive, but legendary, mediation.", _brawl_peace),
                    Choice("Lay down the law", "The room settles, though not everyone applauds.", _brawl_bouncer),
                    Choice("Let them work it out", "The furniture does not approve.", _brawl_watch),
                ),
            ),
            TavernEvent(
                "The Wizard in the Damp Cloak",
                "A mage asks for ingredients for a soup that, she claims, remembers the future.",
                (
                    Choice("Sell her provisions", "A profitable and slightly mysterious deal.", _wizard_stew),
                    Choice("Rent her a room", "She pays to sleep away from the fireplace.", _wizard_room),
                    Choice("Decline the offer", "Best not to ask what is in the soup.", _wizard_refuse),
                ),
            ),
            TavernEvent(
                "A Traveller in the Rain",
                "A drenched explorer asks for shelter and insists her map has just changed.",
                (
                    Choice("Serve a hot dinner", "A small cost for a grand tale.", _lost_traveller),
                    Choice("Listen to her story", "Sometimes the best stories come with a tip.", _lost_coin),
                ),
            ),
        )

    @property
    def events(self) -> tuple[TavernEvent, ...]:
        """Return the immutable event catalogue."""
        return self._events

    def get_event(self, title: str) -> TavernEvent | None:
        """Look up an event by title, or return ``None`` when it is unknown."""
        return next((event for event in self._events if event.title == title), None)

    def next_event(self) -> TavernEvent:
        return self._rng.choice(self._events)

    def resolve(self, event: TavernEvent, choice_index: int, tavern: Tavern) -> str:
        if not 0 <= choice_index < len(event.choices):
            raise ValueError("That event choice does not exist.")
        outcome = event.choices[choice_index].apply(tavern)
        tavern.record(f"{event.title}: {outcome}")
        return outcome
