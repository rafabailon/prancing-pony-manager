import unittest

from events import EventManager
from models import Tavern


class EventManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = EventManager()
        self.tavern = Tavern()

    def test_event_pool_contains_distinct_scenarios_and_choices(self):
        events = self.manager.events
        self.assertEqual(len(events), 4)
        self.assertEqual(len({event.title for event in events}), 4)
        self.assertTrue(all(len(event.choices) >= 2 for event in events))

    def test_events_can_be_looked_up_by_title(self):
        event = self.manager.events[0]
        self.assertIs(self.manager.get_event(event.title), event)
        self.assertIsNone(self.manager.get_event("The Nonexistent Party"))

    def test_invalid_choice_does_not_change_state(self):
        event = self.manager._events[0]
        initial = (self.tavern.gold, self.tavern.provisions, self.tavern.satisfaction)
        with self.assertRaises(ValueError):
            self.manager.resolve(event, len(event.choices), self.tavern)
        self.assertEqual(
            (self.tavern.gold, self.tavern.provisions, self.tavern.satisfaction),
            initial,
        )

    def test_bard_choice_applies_exact_effects(self):
        event = next(e for e in self.manager._events if e.title.startswith("The Bard"))
        result = self.manager.resolve(event, 0, self.tavern)
        self.assertEqual(self.tavern.gold, 21)
        self.assertEqual(self.tavern.satisfaction, 73)
        self.assertEqual(self.tavern.reputation, 7)
        self.assertIn(event.title, self.tavern.history[-1])
        self.assertIn("3 gold", result)

    def test_bard_cannot_be_paid_when_tavern_is_broke(self):
        event = next(e for e in self.manager._events if e.title.startswith("The Bard"))
        tavern = Tavern(gold=0)
        result = self.manager.resolve(event, 0, tavern)
        self.assertEqual(tavern.gold, 0)
        self.assertEqual(tavern.satisfaction, 61)
        self.assertIn("cannot afford", result)

    def test_bard_dinner_choice_fails_gracefully_without_provisions(self):
        event = next(e for e in self.manager._events if e.title.startswith("The Bard"))
        tavern = Tavern(provisions=0)
        result = self.manager.resolve(event, 2, tavern)
        self.assertEqual(tavern.provisions, 0)
        self.assertEqual(tavern.reputation, 5)
        self.assertEqual(tavern.satisfaction, 62)
        self.assertIn("no dinner left", result)

    def test_broke_tavern_cannot_pay_brawl_round(self):
        event = next(e for e in self.manager._events if e.title.startswith("The Twin Axes"))
        tavern = Tavern(gold=0)
        result = self.manager.resolve(event, 0, tavern)
        self.assertEqual(tavern.gold, 0)
        self.assertEqual(tavern.satisfaction, 59)
        self.assertIn("cannot afford", result.lower())

    def test_wizard_trade_increases_gold_and_caps_provisions(self):
        event = next(e for e in self.manager._events if e.title.startswith("The Wizard"))
        tavern = Tavern(gold=0, provisions=29)
        result = self.manager.resolve(event, 0, tavern)
        self.assertEqual(tavern.gold, 5)
        self.assertEqual(tavern.provisions, 30)
        self.assertEqual(tavern.reputation, 7)
        self.assertIn("+5 gold", result)


if __name__ == "__main__":
    unittest.main()
