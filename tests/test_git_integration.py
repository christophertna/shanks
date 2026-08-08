import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from workflow.adapters import GitHubAdapter
from workflow.workspaces import RunWorkspaceManager, workspace_scope


class GitHubIntegrationTests(unittest.TestCase):
    def test_real_worktree_commit_push_and_pr_reuse(self) -> None:
        with TemporaryDirectory() as directory:
            root, remote = self._repository(Path(directory))
            manager = RunWorkspaceManager(root)
            workspace = manager.ensure("integration run")
            self.assertEqual(manager.ensure("integration run"), workspace)
            (workspace.directory / "feature.txt").write_text(
                "integration coverage\n",
                encoding="utf-8",
            )
            fake_gh = self._fake_gh(Path(directory))
            adapter = GitHubAdapter(
                root,
                initial_dirty_files=(),
                stale_after_days=None,
            )

            with patch.dict(
                os.environ,
                {"PATH": f"{fake_gh.parent}{os.pathsep}{os.environ['PATH']}"},
            ):
                with workspace_scope(workspace.directory):
                    committed = adapter.commit_item(
                        "item-1",
                        "Real integration coverage",
                        ["feature.txt"],
                    )
                    pushed = adapter.push_branch()
                    first_pr = adapter.open_pull_request(
                        "Integration delivery",
                        branch=workspace.branch,
                    )
                    reused_pr = adapter.publish_pr("Integration delivery")

            self.assertEqual(committed.status, "committed")
            self.assertEqual(committed.files_touched, ["feature.txt"])
            self.assertEqual(
                self._git(workspace.directory, "rev-parse", "HEAD"),
                committed.commit_sha,
            )
            self.assertEqual(pushed.status, "branch_pushed")
            self.assertEqual(first_pr.status, "pr_created")
            self.assertEqual(reused_pr.status, "pr_created")
            self.assertEqual(reused_pr.pr_url, first_pr.pr_url)
            self.assertIn(
                workspace.branch,
                self._git(
                    root,
                    "--git-dir",
                    str(remote),
                    "branch",
                    "--list",
                    workspace.branch,
                ),
            )
            self.assertEqual(
                self._git(
                    workspace.directory,
                    "status",
                    "--short",
                    "--untracked-files=all",
                ),
                "",
            )
            calls = self._fake_gh_state(fake_gh)["calls"]
            self.assertEqual(
                [call[:2] for call in calls],
                [["pr", "list"], ["pr", "create"], ["pr", "list"]],
            )

    def test_pr_creation_failure_recovers_on_retry(self) -> None:
        with TemporaryDirectory() as directory:
            root, remote = self._repository(Path(directory))
            manager = RunWorkspaceManager(root)
            workspace = manager.ensure("failure recovery")
            (workspace.directory / "recovery.txt").write_text(
                "retry the handoff\n",
                encoding="utf-8",
            )
            fake_gh = self._fake_gh(Path(directory), fail_create_once=True)
            adapter = GitHubAdapter(
                root,
                initial_dirty_files=(),
                stale_after_days=None,
            )

            with patch.dict(
                os.environ,
                {"PATH": f"{fake_gh.parent}{os.pathsep}{os.environ['PATH']}"},
            ):
                with workspace_scope(workspace.directory):
                    committed = adapter.commit_item(
                        "item-1",
                        "Recover the handoff",
                        ["recovery.txt"],
                    )
                    failed = adapter.publish_pr("Recover the integration delivery")
                    recovered = adapter.publish_pr("Recover the integration delivery")

            self.assertEqual(committed.status, "committed")
            self.assertEqual(failed.status, "failed")
            self.assertEqual(failed.pr_url, "")
            self.assertIn("simulated PR creation failure", failed.error)
            self.assertEqual(recovered.status, "pr_created")
            self.assertEqual(recovered.pr_url, "https://github.test/pull/1")
            self.assertIn(
                workspace.branch,
                self._git(
                    root,
                    "--git-dir",
                    str(remote),
                    "branch",
                    "--list",
                    workspace.branch,
                ),
            )
            calls = self._fake_gh_state(fake_gh)["calls"]
            self.assertEqual(
                [call[:2] for call in calls],
                [["pr", "list"], ["pr", "create"]] * 2,
            )

    @classmethod
    def _repository(cls, directory: Path) -> tuple[Path, Path]:
        root = directory / "project"
        remote = directory / "origin.git"
        root.mkdir()
        cls._run(("git", "init", "-b", "main"), root)
        cls._run(("git", "config", "user.email", "tests@example.com"), root)
        cls._run(("git", "config", "user.name", "Integration Tests"), root)
        (root / "scripts").mkdir()
        (root / ".gitignore").write_text(".shanks/\n", encoding="utf-8")
        (root / "README.md").write_text("initial\n", encoding="utf-8")
        (root / "scripts" / "quality_gates.py").write_text(
            "raise SystemExit(0)\n",
            encoding="utf-8",
        )
        cls._git(root, "add", ".")
        cls._git(root, "commit", "-m", "initial")
        cls._run(("git", "init", "--bare", str(remote)), directory)
        cls._git(root, "remote", "add", "origin", str(remote))
        cls._git(root, "push", "-u", "origin", "main")
        return root, remote

    @staticmethod
    def _fake_gh(directory: Path, *, fail_create_once: bool = False) -> Path:
        fake_bin = directory / "fake-bin"
        fake_bin.mkdir()
        state = {
            "calls": [],
            "fail_create_once": fail_create_once,
            "next_number": 1,
            "prs": [],
        }
        (fake_bin / "state.json").write_text(
            json.dumps(state),
            encoding="utf-8",
        )
        script = fake_bin / "gh"
        script.write_text(
            "#!" + sys.executable + "\n" + r"""import json
import sys
from pathlib import Path

state_path = Path(__file__).with_name("state.json")
state = json.loads(state_path.read_text(encoding="utf-8"))
args = sys.argv[1:]
state["calls"].append(args)


def save():
    state_path.write_text(json.dumps(state), encoding="utf-8")


def option(name):
    index = args.index(name)
    return args[index + 1]


if args[:2] == ["auth", "status"]:
    save()
    print("Logged in")
    raise SystemExit(0)

if args[:2] == ["pr", "list"]:
    save()
    print(json.dumps(state["prs"]))
    raise SystemExit(0)

if args[:2] == ["pr", "create"]:
    if state["fail_create_once"]:
        state["fail_create_once"] = False
        save()
        print("simulated PR creation failure", file=sys.stderr)
        raise SystemExit(1)
    number = state["next_number"]
    state["next_number"] += 1
    head = option("--head")
    title = option("--title")
    body = option("--body")
    labels = [
        args[index + 1]
        for index, value in enumerate(args)
        if value == "--label"
    ]
    reviewers = [
        args[index + 1]
        for index, value in enumerate(args)
        if value == "--reviewer"
    ]
    url = f"https://github.test/pull/{number}"
    state["prs"].append(
        {
            "number": number,
            "url": url,
            "state": "OPEN",
            "mergedAt": None,
            "title": title,
            "body": body,
            "updatedAt": "2026-08-08T00:00:00Z",
            "mergeStateStatus": "CLEAN",
            "labels": [{"name": label} for label in labels],
            "reviewRequests": [{"login": reviewer} for reviewer in reviewers],
            "latestReviews": [],
            "headRefName": head,
        }
    )
    save()
    print(url)
    raise SystemExit(0)

if args[:2] == ["pr", "edit"]:
    target = args[2]
    for pr in state["prs"]:
        if str(pr["number"]) == target:
            if "--title" in args:
                pr["title"] = option("--title")
            if "--body" in args:
                pr["body"] = option("--body")
    save()
    print("edited")
    raise SystemExit(0)

if args[:2] == ["pr", "reopen"]:
    target = args[2]
    for pr in state["prs"]:
        if str(pr["number"]) == target:
            pr["state"] = "OPEN"
    save()
    print("reopened")
    raise SystemExit(0)

save()
print(f"unsupported fake gh command: {args}", file=sys.stderr)
raise SystemExit(2)
""",
            encoding="utf-8",
        )
        script.chmod(0o755)
        return script

    @staticmethod
    def _fake_gh_state(executable: Path) -> dict[str, object]:
        return json.loads(
            executable.with_name("state.json").read_text(encoding="utf-8")
        )

    @staticmethod
    def _git(directory: Path, *args: str) -> str:
        return GitHubIntegrationTests._run(("git", *args), directory)

    @staticmethod
    def _run(command: tuple[str, ...], directory: Path) -> str:
        result = subprocess.run(
            command,
            cwd=directory,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()


if __name__ == "__main__":
    unittest.main()
