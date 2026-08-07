import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from workflow.cli import main


class ShanksCliTests(unittest.TestCase):
    def test_mode_reports_safe_runtime(self) -> None:
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"SHANKS_MODE": "runtime"}),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["--mode"]), 0)

        self.assertIn("safe/normal (runtime)", output.getvalue())
        self.assertIn("human approval required", output.getvalue())

    def test_mode_reports_development_capability_without_consent(self) -> None:
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"SHANKS_MODE": "development"}),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["-mode"]), 0)

        self.assertIn("development", output.getvalue())
        self.assertIn("human approval still required", output.getvalue())

    def test_mode_subcommand_is_supported(self) -> None:
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"SHANKS_MODE": "runtime"}),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["mode"]), 0)

        self.assertIn("safe/normal (runtime)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
