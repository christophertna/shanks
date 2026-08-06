import subprocess
import unittest
from pathlib import Path

from scripts.quality_gates import (
    DiffStats,
    diff_command,
    diff_size_errors,
    parse_numstat,
    quality_commands,
    run_quality_gates,
    validate_diff_base,
)


class QualityGateTests(unittest.TestCase):
    def test_quality_commands_cover_all_requested_gate_types(self) -> None:
        commands = dict(quality_commands("python"))

        self.assertEqual(commands["formatting"][:3], ("python", "-m", "black"))
        self.assertEqual(commands["linting"][:3], ("python", "-m", "ruff"))
        self.assertEqual(commands["typing"][:3], ("python", "-m", "mypy"))
        self.assertEqual(
            commands["dependency/security audit"][:3],
            ("python", "-m", "pip_audit"),
        )

    def test_numstat_parser_counts_text_and_binary_files(self) -> None:
        stats = parse_numstat("4\t2\tworkflow/a.py\n-\t-\tassets/logo.bin\n")

        self.assertEqual(stats, DiffStats(files=2, lines=6, binary_files=1))

    def test_numstat_parser_ignores_generated_graphify_output(self) -> None:
        stats = parse_numstat(
            "4\t2\tworkflow/a.py\n100\t200\tgraphify-out/graph.json\n"
        )

        self.assertEqual(stats, DiffStats(files=1, lines=6))

    def test_numstat_parser_rejects_malformed_output(self) -> None:
        with self.assertRaises(ValueError):
            parse_numstat("not git numstat")

    def test_diff_commands_use_the_requested_base_and_mode(self) -> None:
        self.assertEqual(
            diff_command("origin/main"),
            ("git", "diff", "--numstat", "origin/main...HEAD"),
        )
        self.assertEqual(
            diff_command("origin/main", staged=True),
            ("git", "diff", "--cached", "--numstat", "origin/main"),
        )

    def test_diff_base_rejects_option_injection(self) -> None:
        with self.assertRaises(ValueError):
            validate_diff_base("--output=/tmp/unsafe")

    def test_diff_size_gate_reports_file_and_line_limits(self) -> None:
        errors = diff_size_errors(
            DiffStats(files=3, lines=12),
            max_files=2,
            max_lines=10,
        )

        self.assertEqual(len(errors), 2)
        self.assertIn("3 files", errors[0])
        self.assertIn("12 lines", errors[1])

    def test_quality_runner_reports_failed_external_gates(self) -> None:
        def failing_runner(*args, **kwargs):
            return subprocess.CompletedProcess(
                args=args[0], returncode=1, stdout="lint output", stderr=""
            )

        failures = run_quality_gates(Path("/tmp/project"), runner=failing_runner)

        self.assertEqual(len(failures), 4)
        self.assertIn("formatting gate failed", failures[0])
        self.assertIn("lint output", failures[-1])

    def test_quality_runner_applies_diff_size_gate(self) -> None:
        def passing_runner(command, **kwargs):
            if command[0] == "git":
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="2\t3\tworkflow/new.py\n",
                    stderr="",
                )
            return subprocess.CompletedProcess(
                args=command, returncode=0, stdout="ok", stderr=""
            )

        failures = run_quality_gates(
            Path("/tmp/project"),
            diff_base="origin/main",
            max_lines=4,
            runner=passing_runner,
        )

        self.assertEqual(failures, ["diff changes 5 lines; limit is 4 lines"])


if __name__ == "__main__":
    unittest.main()
