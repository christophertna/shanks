"""Behavioral tests for scripts/sandbox_claude.sh's write containment.

These exercise the actual sandbox mechanism (not just command construction)
since the whole point of the script is a runtime guarantee: a real attempt
to write outside the target directory must fail.
"""

import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "sandbox_claude.sh"
HAS_SANDBOX_EXEC = sys.platform == "darwin" and shutil.which("sandbox-exec") is not None


def _run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


@unittest.skipUnless(
    HAS_SANDBOX_EXEC, "sandbox_claude.sh only sandboxes on macOS with sandbox-exec"
)
class SandboxClaudeContainmentTests(unittest.TestCase):
    def test_allows_writes_inside_the_target_directory(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "inside"
            target.mkdir()
            result = _run(str(target), "bash", "-c", f"echo hi > '{target / 'ok.txt'}'")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((target / "ok.txt").exists())

    def test_denies_writes_outside_the_target_directory(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "inside"
            target.mkdir()
            outside = Path(directory) / "outside"
            outside.mkdir()
            result = _run(
                str(target), "bash", "-c", f"echo hi > '{outside / 'bad.txt'}'"
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((outside / "bad.txt").exists())

    def test_denies_a_parent_directory_escape(self) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "inside"
            target.mkdir()
            result = _run(
                str(target), "bash", "-c", f"echo hi > '{target}/../escaped.txt'"
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(directory) / "escaped.txt").exists())


class SandboxClaudeFallbackTests(unittest.TestCase):
    def test_runs_the_command_unsandboxed_when_sandbox_exec_is_unavailable(
        self,
    ) -> None:
        with TemporaryDirectory() as directory:
            target = Path(directory) / "inside"
            target.mkdir()
            result = _run(
                str(target),
                "bash",
                "-c",
                "echo fallback-ran",
                env={"PATH": "/bin"},
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("fallback-ran", result.stdout)
            self.assertIn("running", result.stderr)


if __name__ == "__main__":
    unittest.main()
