import unittest

from team_coordinator_mcp.server_sdk import create_mcp


class ServerSdkTest(unittest.IsolatedAsyncioTestCase):
    async def test_fastmcp_lists_registered_tools(self):
        mcp = create_mcp()
        tools = await mcp.list_tools()
        names = {tool.name for tool in tools}

        self.assertIn("init_workspace", names)
        self.assertIn("get_context_bundle", names)
        self.assertIn("register_agent", names)
        self.assertIn("claim_task", names)
        self.assertIn("render_markdown", names)


if __name__ == "__main__":
    unittest.main()
