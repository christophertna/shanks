import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from workflow.adapters import StubAgentAdapter
from workflow.contracts import AgentRequest, AgentResult
from workflow.nodes import NodeDependencies, create_nodes
from workflow.state import CURRENT_STATE_SCHEMA_VERSION, migrate_state
from workflow.workspaces import (
    RunWorkspace,
    RunWorkspaceManager,
    WorkspaceError,
    current_workspace_directory,
    workspace_scope,
)


class RecordingAdapter:
    def __init__(self, role: str) -> None:
        self.role = role
        self.model_name = role
        self.requests: list[AgentRequest] = []

    def run(self, request: AgentRequest) -> AgentResult:
        self.requests.append(request)
        if self.role == "planner":
            return AgentResult(
                status="planned",
                assigned_model=self.model_name,
                plan=["build"],
                builder_instructions="build it",
            )
        return AgentResult(status="completed", assigned_model=self.model_name)


class FakeWorkspaceManager:
    def __init__(self, directory: Path) -> None:
        self.workspace = RunWorkspace(
            run_id="run-1",
            branch="shanks/run/run-1",
            directory=directory,
            base_branch="main",
        )
        self.run_ids: list[str] = []

    def ensure(self, run_id: str) -> RunWorkspace:
        self.run_ids.append(run_id)
        return self.workspace


class WorkspaceTests(unittest.TestCase):
    def test_manager_creates_and_reuses_a_run_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._git(root, "init", "-b", "main")
            self._git(root, "config", "user.email", "tests@example.com")
            self._git(root, "config", "user.name", "Tests")
            (root / "README.md").write_text("initial\n", encoding="utf-8")
            self._git(root, "add", "README.md")
            self._git(root, "commit", "-m", "initial")

            manager = RunWorkspaceManager(root)
            first = manager.ensure("thread/one")
            second = manager.ensure("thread/one")

            self.assertEqual(first, second)
            self.assertTrue(first.branch.startswith("shanks/run/thread-one-"))
            self.assertTrue((first.directory / ".git").exists())
            self.assertEqual(
                self._git(first.directory, "branch", "--show-current"),
                first.branch,
            )

    def test_development_mode_can_delete_a_run_branch_after_worktree_removal(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._git(root, "init", "-b", "main")
            self._git(root, "config", "user.email", "tests@example.com")
            self._git(root, "config", "user.name", "Tests")
            (root / "README.md").write_text("initial\n", encoding="utf-8")
            self._git(root, "add", "README.md")
            self._git(root, "commit", "-m", "initial")

            manager = RunWorkspaceManager(root)
            workspace = manager.ensure("thread/one")
            manager.remove("thread/one")

            with patch.dict("os.environ", {"SHANKS_MODE": "runtime"}):
                with self.assertRaisesRegex(WorkspaceError, "not in development mode"):
                    manager.delete_branch("thread/one")

            with patch.dict(
                "os.environ",
                {"SHANKS_MODE": "development"},
            ):
                manager.delete_branch("thread/one")

            self.assertEqual(
                self._git(root, "branch", "--list", workspace.branch),
                "",
            )

    def test_development_mode_cannot_delete_a_protected_branch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = RunWorkspaceManager(Path(directory))

            with patch.dict("os.environ", {"SHANKS_MODE": "development"}):
                with self.assertRaisesRegex(WorkspaceError, "protected branch"):
                    manager.delete_branch(
                        "thread/one",
                        branch="main",
                    )

    def test_development_mode_cannot_delete_a_branch_outside_the_run_scope(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager = RunWorkspaceManager(Path(directory))

            with patch.dict("os.environ", {"SHANKS_MODE": "development"}):
                with self.assertRaisesRegex(WorkspaceError, "run scope"):
                    manager.delete_branch(
                        "thread/one",
                        branch="feature/another-run",
                    )

    def test_workspace_context_is_scoped_and_restored(self) -> None:
        self.assertIsNone(current_workspace_directory())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            with workspace_scope(path):
                self.assertEqual(current_workspace_directory(), path.resolve())
            self.assertIsNone(current_workspace_directory())

    def test_graph_nodes_persist_run_identity_and_route_requests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace_directory = Path(directory)
            planner = RecordingAdapter("planner")
            manager = FakeWorkspaceManager(workspace_directory)
            dependencies = NodeDependencies(
                planner=planner,
                builder=RecordingAdapter("builder"),
                critic=StubAgentAdapter("critic", "critic"),
                validator=StubAgentAdapter("validator", "validator"),
                debugger=StubAgentAdapter("debugger", "debugger"),
                workspace_manager=manager,
            )
            planning = create_nodes(dependencies)["planning"]

            update = planning(
                {
                    "task": "isolated run",
                    "workflow_mode": "implement",
                    "prd_items": [{"id": "item-1", "title": "Item"}],
                },
                {"configurable": {"thread_id": "run/1"}},
            )

            self.assertEqual(
                update["state_schema_version"], CURRENT_STATE_SCHEMA_VERSION
            )
            self.assertEqual(update["run_id"], "run/1")
            self.assertEqual(update["run_branch"], "shanks/run/run-1")
            self.assertEqual(
                update["workspace_directory"], workspace_directory.as_posix()
            )
            self.assertEqual(
                planner.requests[0].working_directory,
                workspace_directory,
            )
            self.assertEqual(manager.run_ids, ["run/1"])

    def test_v4_state_migrates_workspace_fields(self) -> None:
        migrated = migrate_state({"state_schema_version": 4})

        self.assertEqual(migrated["state_schema_version"], CURRENT_STATE_SCHEMA_VERSION)
        self.assertEqual(migrated["run_id"], "")
        self.assertEqual(migrated["run_branch"], "")
        self.assertEqual(migrated["workspace_directory"], "")

    @staticmethod
    def _git(directory: Path, *args: str) -> str:
        result = subprocess.run(
            ("git", *args),
            cwd=directory,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()


if __name__ == "__main__":
    unittest.main()
