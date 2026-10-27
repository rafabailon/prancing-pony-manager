import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from game import Game
from models import Tavern
from terminal_ui import TerminalApp, _display_width


class TerminalAppTests(unittest.TestCase):
    def make_app(self, answers, **kwargs):
        output = []

        def read_input(_prompt):
            if not answers:
                raise EOFError
            return answers.pop(0)

        app = TerminalApp(
            game=Game(tavern=Tavern()),
            input_fn=read_input,
            output_fn=output.append,
            **kwargs,
        )
        return app, output

    def test_invalid_input_then_quit_does_not_crash(self):
        app, output = self.make_app(["abc", "Q"])
        app.run()
        self.assertTrue(any("valid option" in line for line in output))
        self.assertTrue(any("Thanks for looking after" in line for line in output))

    def test_out_of_range_input_is_reprompted(self):
        app, output = self.make_app(["99", "Q"])
        app.run()
        self.assertTrue(any("between 1 and 4" in line for line in output))

    def test_valid_action_event_and_day_complete(self):
        # Serve one meal, end management early, choose the first random event.
        app, output = self.make_app(["1", "4", "1", "Q"])
        app.run()
        self.assertTrue(any("serve the house stew" in line for line in output))
        self.assertTrue(any("The night ends" in line for line in output))
        self.assertEqual(app.game.tavern.day, 2)

    def test_eof_exits_cleanly_from_action_prompt(self):
        app, output = self.make_app([])
        app.run()
        self.assertTrue(any("Thanks for looking after" in line for line in output))

    def test_quit_during_event_does_not_advance_day(self):
        app, output = self.make_app(["4", "Q"])
        app.run()
        self.assertEqual(app.game.tavern.day, 1)
        self.assertFalse(any("The night ends" in line for line in output))

    def test_direct_script_entry_point_starts_game(self):
        project_root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(project_root / "src")
        result = subprocess.run(
            [sys.executable, "src/cli_main.py", "--seed", "7"],
            cwd=project_root,
            env=environment,
            input="Q\n",
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FANTASY TAVERN MANAGEMENT", result.stdout)
        self.assertIn("Thanks for looking after the tavern", result.stdout)

    def test_dashboard_lines_are_aligned_even_with_long_names(self):
        app, output = self.make_app([])
        app.game.tavern.name = "A Very Long Tavern Name That Should Still Fit " * 2
        app.show_dashboard()
        lines = output[0].strip("\n").splitlines()
        widths = {_display_width(line) for line in lines}
        self.assertEqual(len(widths), 1, lines)

    def test_version_flag_reports_the_project_name(self):
        project_root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(project_root / "src")
        result = subprocess.run(
            [sys.executable, "src/cli_main.py", "--version"],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("prancing-pony 1.1.0", result.stdout)

    def test_blank_name_is_rejected_with_a_usage_error(self):
        project_root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(project_root / "src")
        result = subprocess.run(
            [sys.executable, "src/cli_main.py", "--name", "   "],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot be empty", result.stderr)

    def test_missing_save_file_fails_cleanly(self):
        project_root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(project_root / "src")
        result = subprocess.run(
            [sys.executable, "src/cli_main.py", "--load", "does-not-exist.json"],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Save file not found", result.stderr)

    def test_save_flag_writes_a_valid_save_on_exit(self):
        project_root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(project_root / "src")
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "nested" / "game.json"
            result = subprocess.run(
                [
                    sys.executable,
                    "src/cli_main.py",
                    "--seed",
                    "7",
                    "--name",
                    "The Copper Kettle",
                    "--save",
                    str(save_path),
                ],
                cwd=project_root,
                env=environment,
                input="Q\n",
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(save_path.is_file())
            payload = json.loads(save_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["tavern"]["name"], "The Copper Kettle")
            self.assertEqual(payload["tavern"]["day"], 1)


if __name__ == "__main__":
    unittest.main()
