import random
import unittest

from events import EventManager
from game import Game, GameConfig
from models import Tavern


class GameTests(unittest.TestCase):
    def test_config_rejects_non_positive_settings(self):
        for kwargs in (
            {"actions_per_day": 0},
            {"meal_price": 0},
            {"meal_provisions": 0},
            {"meal_satisfaction": 0},
            {"restock_cost": 0},
            {"restock_amount": 0},
            {"reputation_cost": 0},
            {"promotion_reputation": 0},
            {"promotion_satisfaction": 0},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    GameConfig(**kwargs)

    def test_serve_meal_consumes_resources_and_action(self):
        game = Game(tavern=Tavern(gold=0, provisions=2, satisfaction=99))
        result = game.serve_meal()
        self.assertEqual(game.tavern.gold, 5)
        self.assertEqual(game.tavern.provisions, 0)
        self.assertEqual(game.tavern.satisfaction, 100)
        self.assertEqual(game.actions_left, 1)
        self.assertIn("+5 gold", result)

    def test_serve_meal_without_stock_does_not_consume_action(self):
        game = Game(tavern=Tavern(provisions=1))
        self.assertIn("Not enough provisions", game.serve_meal())
        self.assertEqual(game.actions_left, 2)

    def test_restock_exact_cost_and_capacity_limit(self):
        game = Game(tavern=Tavern(gold=8, provisions=29))
        result = game.restock()
        self.assertEqual(game.tavern.gold, 0)
        self.assertEqual(game.tavern.provisions, 30)
        self.assertEqual(game.actions_left, 1)
        self.assertIn("+1 provisions", result)

    def test_restock_rejects_insufficient_gold(self):
        game = Game(tavern=Tavern(gold=7, provisions=10))
        self.assertIn("Not enough gold", game.restock())
        self.assertEqual(game.tavern.gold, 7)
        self.assertEqual(game.actions_left, 2)

    def test_restock_full_pantry_does_not_charge(self):
        game = Game(tavern=Tavern(gold=20, provisions=30))
        self.assertIn("pantry is already full", game.restock())
        self.assertEqual(game.tavern.gold, 20)

    def test_promotion_costs_gold_but_caps_positive_stats(self):
        game = Game(tavern=Tavern(gold=4, reputation=99, satisfaction=99))
        result = game.promote_tavern()
        self.assertEqual(game.tavern.gold, 0)
        self.assertEqual(game.tavern.reputation, 100)
        self.assertEqual(game.tavern.satisfaction, 100)
        self.assertIn("+1 reputation", result)

    def test_no_actions_remain_after_two_valid_actions(self):
        game = Game(tavern=Tavern(provisions=10))
        game.serve_meal()
        game.promote_tavern()
        self.assertEqual(game.actions_left, 0)
        gold = game.tavern.gold
        self.assertEqual(game.serve_meal(), "No actions remain today.")
        self.assertEqual(game.tavern.gold, gold)

    def test_close_day_consumes_stock_resets_actions_and_advances(self):
        game = Game(tavern=Tavern(provisions=30), rng=random.Random(4))
        result = game.close_day()
        self.assertEqual(game.tavern.day, 2)
        self.assertEqual(game.actions_left, 2)
        self.assertLess(game.tavern.provisions, 30)
        self.assertIn("The night ends", result)

    def test_close_day_with_empty_pantry_lowers_satisfaction(self):
        game = Game(tavern=Tavern(gold=0, provisions=0, satisfaction=30), rng=random.Random(1))
        game.close_day()
        self.assertLess(game.tavern.satisfaction, 30)

    def test_close_day_closes_at_zero_satisfaction(self):
        game = Game(tavern=Tavern(gold=0, provisions=0, satisfaction=1), rng=random.Random(1))
        result = game.close_day()
        self.assertTrue(game.is_over)
        self.assertEqual(game.actions_left, 0)
        self.assertIn("closes", result)

    def test_close_day_closes_without_gold_or_provisions(self):
        game = Game(tavern=Tavern(gold=0, provisions=0, satisfaction=50), rng=random.Random(1))
        result = game.close_day()
        self.assertTrue(game.is_over)
        self.assertIn("no gold or provisions", result)

    def test_event_must_be_drawn_before_resolution(self):
        game = Game()
        with self.assertRaises(RuntimeError):
            game.resolve_event(0)

    def test_event_can_only_be_resolved_once(self):
        game = Game(rng=random.Random(2))
        event = game.draw_event()
        game.resolve_event(0)
        self.assertIsNone(game.last_event)
        with self.assertRaises(RuntimeError):
            game.resolve_event(0)
        self.assertIsNotNone(event)

    def test_repeated_event_draw_returns_same_pending_event(self):
        game = Game(rng=random.Random(9))
        self.assertIs(game.draw_event(), game.draw_event())

    def test_seed_reproduces_event_sequence(self):
        first = EventManager(random.Random(18))
        second = EventManager(random.Random(18))
        self.assertEqual(
            [first.next_event().title for _ in range(8)],
            [second.next_event().title for _ in range(8)],
        )

    def test_promotion_is_refused_when_both_stats_are_maxed(self):
        game = Game(tavern=Tavern(gold=20, reputation=100, satisfaction=100))
        result = game.promote_tavern()
        self.assertIn("already legendary", result)
        self.assertEqual(game.tavern.gold, 20)
        self.assertEqual(game.actions_left, 2)

    def test_custom_configuration_controls_rewards(self):
        game = Game(
            tavern=Tavern(provisions=10, satisfaction=50),
            config=GameConfig(meal_price=7, meal_provisions=1, meal_satisfaction=2),
        )
        result = game.serve_meal()
        self.assertEqual(game.tavern.gold, 31)
        self.assertEqual(game.tavern.provisions, 9)
        self.assertEqual(game.tavern.satisfaction, 52)
        self.assertIn("+7 gold", result)

    def test_close_day_after_game_over_does_not_change_state(self):
        game = Game(tavern=Tavern())
        game.is_over = True
        before = (game.tavern.day, game.tavern.gold, game.tavern.provisions)
        self.assertEqual(game.close_day(), "The game is already over.")
        self.assertEqual((game.tavern.day, game.tavern.gold, game.tavern.provisions), before)


if __name__ == "__main__":
    unittest.main()
