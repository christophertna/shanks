import io
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
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

    def test_mode_reports_dry_run_preview(self) -> None:
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"SHANKS_MODE": "dry-run"}),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["--mode"]), 0)

        self.assertIn("dry-run", output.getvalue())
        self.assertIn("previewed and skipped", output.getvalue())

    def test_mode_subcommand_is_supported(self) -> None:
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"SHANKS_MODE": "runtime"}),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["mode"]), 0)

        self.assertIn("safe/normal (runtime)", output.getvalue())

    def test_doctor_reports_a_healthy_environment(self) -> None:
        output = io.StringIO()
        versions = {
            "langgraph": "1.2.10",
            "langgraph-checkpoint-sqlite": "3.1.1",
            "black": "26.5.1",
            "mypy": "1.20.2",
            "pip-audit": "2.10.1",
            "ruff": "0.16.1",
        }

        def installed_version(name: str) -> str:
            return versions[name]

        with tempfile.TemporaryDirectory() as directory:
            with (
                patch.dict(
                    "os.environ",
                    {
                        "SHANKS_MODE": "development",
                        "SHANKS_CHECKPOINT_DB": str(
                            Path(directory) / "checkpoints.sqlite"
                        ),
                        "SHANKS_RUN_LEASE_SECONDS": "3600",
                        "SHANKS_CHECKPOINT_RETENTION": "100",
                        "HOME": "/tmp",
                        "PATH": "/usr/bin",
                    },
                    clear=True,
                ),
                patch("workflow.cli.shutil.which", return_value="/usr/bin/tool"),
                patch(
                    "workflow.cli.importlib_metadata.version",
                    side_effect=installed_version,
                ),
                patch(
                    "workflow.cli.subprocess.run",
                    return_value=subprocess.CompletedProcess(
                        args=("gh", "auth", "status"),
                        returncode=0,
                        stdout="authenticated",
                        stderr="",
                    ),
                ),
                redirect_stdout(output),
            ):
                self.assertEqual(main(["doctor"]), 0)

        self.assertIn("[OK] mode", output.getvalue())
        self.assertIn("[OK] dependencies", output.getvalue())
        self.assertIn("[OK] authentication", output.getvalue())
        self.assertIn("Doctor: PASS", output.getvalue())

    def test_doctor_fails_invalid_environment(self) -> None:
        output = io.StringIO()
        with (
            patch.dict(
                "os.environ",
                {
                    "SHANKS_MODE": "unknown",
                    "SHANKS_RUN_LEASE_SECONDS": "0",
                    "SHANKS_CHECKPOINT_RETENTION": "nope",
                    "SHANKS_CHECKPOINT_DB": "",
                },
                clear=True,
            ),
            patch("workflow.cli.shutil.which", return_value="/usr/bin/tool"),
            patch(
                "workflow.cli.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    args=("gh", "auth", "status"),
                    returncode=1,
                    stdout="",
                    stderr="not authenticated",
                ),
            ),
            redirect_stdout(output),
        ):
            self.assertEqual(main(["doctor"]), 1)

        self.assertIn("[FAIL] mode", output.getvalue())
        self.assertIn("[FAIL] environment", output.getvalue())
        self.assertIn("[FAIL] checkpoint", output.getvalue())
        self.assertIn("Doctor: FAIL", output.getvalue())


if __name__ == "__main__":
    unittest.main()
