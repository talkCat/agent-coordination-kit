import shutil
import tempfile
import unittest
from pathlib import Path

from team_coordinator_mcp.tools import TeamCoordinatorTools


class TeamCoordinatorToolsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ack-tools-"))
        (self.tmp / "src").mkdir()
        (self.tmp / "src" / "main.py").write_text("print('x')\n", encoding="utf-8")
        self.tools = TeamCoordinatorTools(default_root=self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_tool_list_contains_expected_contract(self):
        names = {tool["name"] for tool in self.tools.list_tools()}
        self.assertIn("init_workspace", names)
        self.assertIn("claim_task", names)
        self.assertIn("render_markdown", names)

    def test_call_tool_round_trip(self):
        init = self.tools.call_tool("init_workspace", {"root": str(self.tmp), "docs_dir": str(self.tmp / "plan")})
        self.assertEqual(init["revision"], 1)

        agent = self.tools.call_tool(
            "register_agent",
            {"role": "frontend", "display_name": "FE", "scope": ["src/**"]},
        )
        task = self.tools.call_tool(
            "create_task",
            {
                "title": "Implement FE",
                "scope": ["src/**"],
                "acceptance": ["tests pass"],
                "created_by": agent["id"],
            },
        )
        claim = self.tools.call_tool(
            "claim_task",
            {"task_id": task["id"], "agent_id": agent["id"], "file_patterns": ["src/main.py"]},
        )

        self.assertEqual(claim["task_id"], task["id"])
        bundle = self.tools.call_tool("get_context_bundle", {})
        self.assertEqual(bundle["revision"], 4)
        self.assertEqual(bundle["active_claims"][0]["id"], claim["id"])

    def test_tool_errors_are_structured(self):
        self.tools.call_tool("init_workspace", {"root": str(self.tmp)})
        result = self.tools.call_tool("create_task", {"title": "Bad", "scope": ["/x"], "acceptance": []})
        self.assertEqual(result["error"]["type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
