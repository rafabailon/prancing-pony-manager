import unittest

from models import Tavern


class TavernTests(unittest.TestCase):
    def test_initial_resources_are_capped(self):
        tavern = Tavern(provisions=100, reputation=150, satisfaction=120)
        self.assertEqual(tavern.provisions, tavern.max_provisions)
        self.assertEqual(tavern.reputation, tavern.max_reputation)
        self.assertEqual(tavern.satisfaction, tavern.max_satisfaction)

    def test_invalid_initial_state_is_rejected(self):
        for kwargs in (
            {"name": "   "},
            {"day": 0},
            {"gold": -1},
            {"provisions": -1},
            {"reputation": -1},
            {"satisfaction": -1},
            {"max_provisions": 0},
            {"max_history": 0},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    Tavern(**kwargs)

    def test_gold_rejects_unaffordable_cost_without_mutating(self):
        tavern = Tavern(gold=3)
        self.assertFalse(tavern.change_gold(-4))
        self.assertEqual(tavern.gold, 3)

    def test_gold_allows_exact_balance_and_zero(self):
        tavern = Tavern(gold=3)
        self.assertTrue(tavern.change_gold(-3))
        self.assertEqual(tavern.gold, 0)
        self.assertTrue(tavern.change_gold(0))

    def test_bounded_resources_clamp_at_both_edges(self):
        tavern = Tavern(provisions=1, reputation=0, satisfaction=99)
        self.assertEqual(tavern.change_provisions(-9), -1)
        self.assertEqual(tavern.change_provisions(100), tavern.max_provisions)
        self.assertEqual(tavern.change_reputation(-20), 0)
        self.assertEqual(tavern.change_reputation(200), tavern.max_reputation)
        self.assertEqual(tavern.change_satisfaction(20), 1)
        self.assertEqual(tavern.change_satisfaction(-200), -100)

    def test_name_is_trimmed_for_display(self):
        self.assertEqual(Tavern(name="  The Green Dragon  ").name, "The Green Dragon")

    def test_history_is_bounded(self):
        tavern = Tavern(max_history=3)
        for index in range(5):
            tavern.record(f"entry {index}")
        self.assertEqual(tavern.history, ["entry 2", "entry 3", "entry 4"])

    def test_oversized_history_is_trimmed_on_construction(self):
        tavern = Tavern(max_history=2, history=["old", "middle", "new"])
        self.assertEqual(tavern.history, ["middle", "new"])


if __name__ == "__main__":
    unittest.main()
