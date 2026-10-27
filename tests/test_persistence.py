import json
import random
import tempfile
import unittest
from pathlib import Path

from game import Game, GameConfig
from models import Tavern
from persistence import (
    SAVE_VERSION,
    SaveFormatError,
    SaveNotFoundError,
    game_to_dict,
    load_game,
    save_game,
)


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)

    def test_round_trip_preserves_game_state_and_rng(self):
        game = Game(
            tavern=Tavern(name="The Gilded Acorn", gold=41, provisions=9, day=4),
            rng=random.Random(23),
            config=GameConfig(actions_per_day=3, meal_price=6),
        )
        game.tavern.record("A quiet afternoon.")
        game.actions_left = 1
        game.is_over = False
        game.last_event = game.draw_event()
        event_title = game.last_event.title
        path = self.directory / "saves" / "acorn.json"

        saved = save_game(game, path)
        expected_random = [game.rng.random() for _ in range(4)]
        loaded = load_game(saved)

        self.assertEqual(saved, path)
        self.assertEqual(loaded.tavern.name, "The Gilded Acorn")
        self.assertEqual(loaded.tavern.gold, 41)
        self.assertEqual(loaded.tavern.provisions, 9)
        self.assertEqual(loaded.tavern.day, 4)
        self.assertEqual(loaded.tavern.history, ["A quiet afternoon."])
        self.assertEqual(loaded.actions_left, 1)
        self.assertEqual(loaded.config.actions_per_day, 3)
        self.assertEqual(loaded.config.meal_price, 6)
        self.assertEqual(loaded.last_event.title, event_title)
        self.assertEqual([loaded.rng.random() for _ in range(4)], expected_random)

    def test_save_writes_human_readable_json_without_temporary_files(self):
        path = self.directory / "game.json"
        save_game(Game(rng=random.Random(1)), path)

        payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], SAVE_VERSION)
        self.assertIn("tavern", payload)
        self.assertEqual(list(self.directory.glob(".*.tmp")), [])

    def test_save_overwrites_an_existing_file_atomically(self):
        path = self.directory / "game.json"
        save_game(Game(tavern=Tavern(gold=10)), path)
        save_game(Game(tavern=Tavern(gold=99)), path)
        self.assertEqual(load_game(path).tavern.gold, 99)

    def test_missing_file_has_a_clear_error(self):
        with self.assertRaises(SaveNotFoundError):
            load_game(self.directory / "missing.json")

    def test_invalid_json_is_rejected(self):
        path = self.directory / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        with self.assertRaises(SaveFormatError):
            load_game(path)

    def test_unsupported_version_is_rejected(self):
        path = self.directory / "old.json"
        path.write_text(json.dumps({"version": 999, "tavern": {}}), encoding="utf-8")
        with self.assertRaises(SaveFormatError):
            load_game(path)

    def test_boolean_version_is_not_treated_as_one(self):
        path = self.directory / "boolean-version.json"
        path.write_text(json.dumps({"version": True, "tavern": {}}), encoding="utf-8")
        with self.assertRaises(SaveFormatError):
            load_game(path)

    def test_invalid_tavern_state_is_rejected(self):
        path = self.directory / "invalid.json"
        payload = game_to_dict(Game())
        payload["tavern"]["gold"] = -5
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(SaveFormatError):
            load_game(path)

    def test_unknown_pending_event_is_rejected(self):
        path = self.directory / "event.json"
        payload = game_to_dict(Game())
        payload["state"]["last_event"] = "A Dragon Orders Dessert"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(SaveFormatError):
            load_game(path)

    def test_actions_left_outside_the_day_limit_is_rejected(self):
        path = self.directory / "actions.json"
        payload = game_to_dict(Game())
        payload["state"]["actions_left"] = 99
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(SaveFormatError):
            load_game(path)

    def test_boolean_is_not_accepted_as_an_integer(self):
        path = self.directory / "boolean.json"
        payload = game_to_dict(Game())
        payload["tavern"]["gold"] = True
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaises(SaveFormatError):
            load_game(path)


if __name__ == "__main__":
    unittest.main()
