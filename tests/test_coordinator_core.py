import json
import os
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from team_coordinator_mcp.core import (
    ConflictError,
    CoordinatorStore,
    InvalidOperationError,
    RevisionConflictError,
)


class CoordinatorCoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ack-test-"))
        (self.tmp / "src" / "components").mkdir(parents=True)
        (self.tmp / "src" / "components" / "Button.tsx").write_text("export const Button = 1\n", encoding="utf-8")
        (self.tmp / "src" / "main.ts").write_text("console.log('x')\n", encoding="utf-8")
        self.store = CoordinatorStore(self.tmp, docs_dir=self.tmp / "plan")
        self.store.init_workspace(goal="Test coordination")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_append_event_increments_revision_and_replays_state(self):
        agent = self.store.register_agent("frontend", "Frontend Agent", ["src/**"])
        task = self.store.create_task("Wire iframe", ["src/**"], ["renders iframe"], created_by=agent["id"])

        state_path = self.tmp / ".agent-coordinator" / "state.json"
        state_path.unlink()

        rebuilt = CoordinatorStore(self.tmp, docs_dir=self.tmp / "plan")
        state = rebuilt.load_state()

        self.assertEqual(state["revision"], 3)
        self.assertEqual(state["last_event_id"], task["_event_id"])
        self.assertEqual(state["agents"][0]["id"], agent["id"])
        self.assertEqual(state["tasks"][0]["title"], "Wire iframe")

    def test_expected_revision_conflict_rejects_write(self):
        agent = self.store.register_agent("frontend", "Frontend Agent", ["src/**"])

        with self.assertRaises(RevisionConflictError) as ctx:
            self.store.create_task(
                "Old client write",
                ["src/**"],
                ["accepted"],
                created_by=agent["id"],
                expected_revision=0,
            )

        self.assertEqual(ctx.exception.latest_revision, 2)

    def test_claim_detects_path_and_directory_conflicts(self):
        a1 = self.store.register_agent("frontend", "A1", ["src/**"])
        a2 = self.store.register_agent("backend", "A2", ["src/**"])
        task1 = self.store.create_task("Task 1", ["src/**"], ["done"], created_by=a1["id"])
        task2 = self.store.create_task("Task 2", ["src/**"], ["done"], created_by=a2["id"])

        self.store.claim_task(task1["id"], a1["id"], ["src/components/**"], lease_minutes=10)

        with self.assertRaises(ConflictError) as ctx:
            self.store.claim_task(task2["id"], a2["id"], ["src/components/Button.tsx"], lease_minutes=10)

        self.assertIn("src/components", json.dumps(ctx.exception.conflicts))

    def test_expired_claim_can_be_taken_over(self):
        a1 = self.store.register_agent("frontend", "A1", ["src/**"])
        a2 = self.store.register_agent("backend", "A2", ["src/**"])
        task1 = self.store.create_task("Task 1", ["src/**"], ["done"], created_by=a1["id"])
        task2 = self.store.create_task("Task 2", ["src/**"], ["done"], created_by=a2["id"])

        self.store.claim_task(task1["id"], a1["id"], ["src/main.ts"], lease_minutes=0.001)
        time.sleep(0.08)
        claim = self.store.claim_task(task2["id"], a2["id"], ["src/main.ts"], lease_minutes=10)

        self.assertEqual(claim["status"], "active")
        state = self.store.load_state()
        expired = [c for c in state["claims"] if c["agent_id"] == a1["id"]][0]
        self.assertEqual(expired["status"], "expired")
        self.assertEqual(expired["release_reason"], "expired")

    def test_task_state_machine_rejects_invalid_transitions(self):
        agent = self.store.register_agent("frontend", "Frontend Agent", ["src/**"])
        task = self.store.create_task("Task", ["src/**"], ["done"], created_by=agent["id"])
        self.store.claim_task(task["id"], agent["id"], ["src/main.ts"], lease_minutes=10)

        with self.assertRaises(InvalidOperationError):
            self.store.update_task(task["id"], agent["id"], "review")

        self.store.update_task(task["id"], agent["id"], "in_progress")
        self.store.update_task(task["id"], agent["id"], "blocked", note="API unclear")

        with self.assertRaises(InvalidOperationError):
            self.store.update_task(task["id"], agent["id"], "review")

        self.store.update_task(task["id"], agent["id"], "in_progress")
        self.store.complete_task(task["id"], agent["id"], evidence="unit tests")

        with self.assertRaises(InvalidOperationError):
            self.store.update_task(task["id"], agent["id"], "done")

    def test_update_task_cannot_bypass_review_task_for_done(self):
        owner = self.store.register_agent("frontend", "Owner", ["src/**"])
        other = self.store.register_agent("backend", "Other", ["src/**"])
        task = self.store.create_task("Task", ["src/**"], ["done"], created_by=owner["id"])
        self.store.claim_task(task["id"], owner["id"], ["src/main.ts"], lease_minutes=10)
        self.store.update_task(task["id"], owner["id"], "in_progress")
        self.store.complete_task(task["id"], owner["id"], evidence="tests")

        with self.assertRaises(InvalidOperationError):
            self.store.update_task(task["id"], other["id"], "done")

    def test_dependencies_block_complete_but_not_claim(self):
        agent = self.store.register_agent("frontend", "Frontend Agent", ["src/**"])
        dep = self.store.create_task("Dependency", ["src/**"], ["done"], created_by=agent["id"])
        task = self.store.create_task(
            "Dependent",
            ["src/**"],
            ["done"],
            depends_on=[dep["id"]],
            created_by=agent["id"],
        )

        claim = self.store.claim_task(task["id"], agent["id"], ["src/main.ts"], lease_minutes=10)
        self.assertTrue(claim["warnings"])

        self.store.update_task(task["id"], agent["id"], "in_progress")
        with self.assertRaises(InvalidOperationError):
            self.store.complete_task(task["id"], agent["id"], evidence="not ready")

    def test_root_broad_glob_claim_conflicts_with_concrete_file(self):
        a1 = self.store.register_agent("frontend", "A1", ["**/*"])
        a2 = self.store.register_agent("backend", "A2", ["src/**"])
        task1 = self.store.create_task("Task 1", ["**/*"], ["done"], created_by=a1["id"])
        task2 = self.store.create_task("Task 2", ["src/**"], ["done"], created_by=a2["id"])

        self.store.claim_task(task1["id"], a1["id"], ["*.py"], lease_minutes=10)

        with self.assertRaises(ConflictError):
            self.store.claim_task(task2["id"], a2["id"], ["src/main.ts"], lease_minutes=10)

    def test_review_permissions_and_owner_cannot_self_approve(self):
        owner = self.store.register_agent("frontend", "Owner", ["src/**"])
        tester = self.store.register_agent("tester", "Tester", ["src/**"])
        task = self.store.create_task("Task", ["src/**"], ["done"], created_by=owner["id"], reviewer=tester["id"])
        self.store.claim_task(task["id"], owner["id"], ["src/main.ts"], lease_minutes=10)
        self.store.update_task(task["id"], owner["id"], "in_progress")
        self.store.complete_task(task["id"], owner["id"], evidence="tests")

        with self.assertRaises(InvalidOperationError):
            self.store.review_task(task["id"], owner["id"], "approved")

        reviewed = self.store.review_task(task["id"], tester["id"], "approved", note="ok")
        self.assertEqual(reviewed["status"], "done")

    def test_path_validation_rejects_absolute_and_traversal(self):
        agent = self.store.register_agent("frontend", "Frontend Agent", ["src/**"])
        with self.assertRaises(ValueError):
            self.store.create_task("Bad", ["/tmp/x"], ["done"], created_by=agent["id"])
        with self.assertRaises(ValueError):
            self.store.check_file_claims(["../outside.py"])

    def test_markdown_render_writes_only_generated_files_and_escapes_html(self):
        agent = self.store.register_agent("docs", "Docs Agent", ["plan/**"])
        task = self.store.create_task("Docs", ["plan/**"], ["done"], created_by=agent["id"])
        self.store.record_handoff(
            agent["id"],
            task["id"],
            "summary with <script>alert(1)</script>",
            ["plan/AGENTS.md"],
            "verified",
            "none",
        )

        manual = self.tmp / "plan" / "manual.md"
        manual.parent.mkdir(exist_ok=True)
        manual.write_text("manual", encoding="utf-8")

        rendered = self.store.render_markdown()

        self.assertEqual(manual.read_text(encoding="utf-8"), "manual")
        self.assertTrue((self.tmp / "plan" / "AGENTS.md").read_text(encoding="utf-8").startswith("<!-- generated"))
        handoff = (self.tmp / "plan" / "HANDOFF_LOG.md").read_text(encoding="utf-8")
        self.assertIn("&lt;script&gt;", handoff)
        self.assertNotIn("<script>", handoff)
        self.assertIn("HANDOFF_LOG.md", rendered["written"])

    def test_markdown_render_does_not_overwrite_non_generated_fixed_files(self):
        manual_agents = self.tmp / "plan" / "AGENTS.md"
        manual_agents.parent.mkdir(exist_ok=True)
        manual_agents.write_text("# Human notes\n", encoding="utf-8")

        rendered = self.store.render_markdown()

        self.assertEqual(manual_agents.read_text(encoding="utf-8"), "# Human notes\n")
        self.assertIn("AGENTS.md", rendered["skipped"])
        self.assertTrue((self.tmp / "plan" / "TASK_BOARD.md").read_text(encoding="utf-8").startswith("<!-- generated"))


class LockRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ack-lock-"))
        self.store = CoordinatorStore(self.tmp)
        self.store.init_workspace(goal="Lock test")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_expired_lock_is_cleaned(self):
        lock_path = self.tmp / ".agent-coordinator" / ".lock"
        lock_path.write_text(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "hostname": "unknown-host",
                    "created_at": "2000-01-01T00:00:00Z",
                    "expires_at": "2000-01-01T00:00:01Z",
                    "owner": "stale",
                }
            ),
            encoding="utf-8",
        )

        agent = self.store.register_agent("frontend", "A", ["src/**"])
        self.assertEqual(agent["role"], "frontend")


if __name__ == "__main__":
    unittest.main()
