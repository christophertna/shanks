"""Real-CLI smoke tests for the Codex, Claude, and critic adapters.

Opt-in and skipped by default (set SHANKS_RUN_AGENT_SMOKE=1) so CI stays
deterministic; run manually with an authenticated `codex`/`claude` CLI to
catch drift in the subprocess contract (flags, exit codes, output parsing)
before a full workflow run.
"""

import os
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from workflow.adapters import (
    CLAUDE_OPUS_48_MODEL,
    GPT56_LUNA_MODEL,
    ClaudeAdapter,
    ClaudeOpus48CriticAdapter,
    CodexAdapter,
    GPT56LunaCriticAdapter,
)
from workflow.contracts import AgentRequest

RUN_SMOKE = os.environ.get("SHANKS_RUN_AGENT_SMOKE") == "1"
PROMPT = "Reply with the single word OK and take no other action."
CRITIC_PROMPT = "Confirm greeting.py's greet() function returns the string 'hi'."


@unittest.skipUnless(
    RUN_SMOKE, "set SHANKS_RUN_AGENT_SMOKE=1 to run real agent CLI smoke tests"
)
class RealAgentSmokeTests(unittest.TestCase):
    def _project(self, directory: Path) -> Path:
        project = directory / "project"
        project.mkdir()
        (project / "greeting.py").write_text(
            'def greet():\n    return "hi"\n', encoding="utf-8"
        )
        return project

    @unittest.skipUnless(shutil.which("codex"), "codex CLI not installed")
    def test_codex_adapter_runs_against_real_cli(self) -> None:
        with TemporaryDirectory() as directory:
            project = self._project(Path(directory))
            adapter = CodexAdapter(project, read_only=True)
            result = adapter.run(AgentRequest(task=PROMPT, timeout_seconds=120))

        self.assertEqual(result.assigned_model, "codex")
        self.assertEqual(result.status, "completed", result.error or result.feedback)
        self.assertIn("ok", result.feedback.lower())

    @unittest.skipUnless(shutil.which("claude"), "claude CLI not installed")
    def test_claude_adapter_runs_against_real_cli(self) -> None:
        with TemporaryDirectory() as directory:
            project = self._project(Path(directory))
            adapter = ClaudeAdapter(project, read_only=True)
            result = adapter.run(AgentRequest(task=PROMPT, timeout_seconds=120))

        self.assertEqual(result.assigned_model, "claude")
        self.assertEqual(result.status, "completed", result.error or result.feedback)
        self.assertIn("ok", result.feedback.lower())

    @unittest.skipUnless(shutil.which("claude"), "claude CLI not installed")
    def test_claude_adapter_write_path_runs_inside_the_sandbox(self) -> None:
        with TemporaryDirectory() as directory:
            project = self._project(Path(directory))
            adapter = ClaudeAdapter(project, read_only=False)
            result = adapter.run(
                AgentRequest(
                    task=(
                        "Create a file named sandbox_ok.txt containing the "
                        "single word OK, then reply with the single word OK "
                        "and take no other action."
                    ),
                    timeout_seconds=120,
                )
            )

            self.assertEqual(result.assigned_model, "claude")
            self.assertEqual(
                result.status, "completed", result.error or result.feedback
            )
            self.assertTrue((project / "sandbox_ok.txt").exists())

    @unittest.skipUnless(shutil.which("codex"), "codex CLI not installed")
    def test_gpt_5_6_luna_critic_runs_against_real_cli(self) -> None:
        with TemporaryDirectory() as directory:
            project = self._project(Path(directory))
            adapter = GPT56LunaCriticAdapter(project)
            result = adapter.run(AgentRequest(task=CRITIC_PROMPT, timeout_seconds=120))

        self.assertEqual(result.assigned_model, GPT56_LUNA_MODEL)
        self.assertEqual(
            result.status, "critic_audited", result.error or result.feedback
        )
        self.assertIsInstance(result.approved, bool)
        self.assertTrue(result.feedback)

    @unittest.skipUnless(shutil.which("claude"), "claude CLI not installed")
    def test_claude_opus_4_8_critic_runs_against_real_cli(self) -> None:
        with TemporaryDirectory() as directory:
            project = self._project(Path(directory))
            adapter = ClaudeOpus48CriticAdapter(project)
            result = adapter.run(AgentRequest(task=CRITIC_PROMPT, timeout_seconds=120))

        self.assertEqual(result.assigned_model, CLAUDE_OPUS_48_MODEL)
        self.assertEqual(
            result.status, "critic_audited", result.error or result.feedback
        )
        self.assertIsInstance(result.approved, bool)
        self.assertTrue(result.feedback)


if __name__ == "__main__":
    unittest.main()
