"""MCP server implemented with the official Python MCP SDK."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import os

from mcp.server.fastmcp import FastMCP

from .tools import TeamCoordinatorTools


def create_tools() -> TeamCoordinatorTools:
    root = Path(os.environ.get("ACK_WORKSPACE_ROOT", ".")).resolve()
    docs = os.environ.get("ACK_DOCS_DIR")
    return TeamCoordinatorTools(default_root=root, default_docs_dir=Path(docs).resolve() if docs else None)


def create_mcp() -> FastMCP:
    mcp = FastMCP(
        "team-coordinator-mcp",
        instructions=(
            "Coordinate multiple AI agents working in one repo. "
            "events.jsonl is the fact source, state.json is a projection, "
            "and Markdown is a generated human-readable view."
        ),
        log_level=os.environ.get("ACK_MCP_LOG_LEVEL", "ERROR"),
    )
    tools = create_tools()

    @mcp.tool()
    def init_workspace(root: str, docs_dir: Optional[str] = None, goal: str = "", expected_revision: Optional[int] = None) -> Dict[str, Any]:
        """Initialize the repo-local coordination workspace."""
        return tools.call_tool(
            "init_workspace",
            {"root": root, "docs_dir": docs_dir, "goal": goal, "expected_revision": expected_revision},
        )

    @mcp.tool()
    def get_context_bundle(role: Optional[str] = None, scope: Optional[List[str]] = None) -> Dict[str, Any]:
        """Return goal, tasks, decisions, handoffs, active claims, and revision."""
        return tools.call_tool("get_context_bundle", {"role": role, "scope": scope})

    @mcp.tool()
    def register_agent(role: str, display_name: str, scope: List[str], expected_revision: Optional[int] = None) -> Dict[str, Any]:
        """Register an agent session with role and repo-root relative scope."""
        return tools.call_tool(
            "register_agent",
            {"role": role, "display_name": display_name, "scope": scope, "expected_revision": expected_revision},
        )

    @mcp.tool()
    def heartbeat_agent(agent_id: str) -> Dict[str, Any]:
        """Refresh agent and active claim heartbeat projection."""
        return tools.call_tool("heartbeat_agent", {"agent_id": agent_id})

    @mcp.tool()
    def create_task(
        title: str,
        scope: List[str],
        acceptance: List[str],
        priority: str = "P1",
        depends_on: Optional[List[str]] = None,
        reviewer: Optional[str] = None,
        created_by: str = "system",
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a task with scope, acceptance criteria, dependencies, and optional reviewer."""
        return tools.call_tool(
            "create_task",
            {
                "title": title,
                "scope": scope,
                "acceptance": acceptance,
                "priority": priority,
                "depends_on": depends_on,
                "reviewer": reviewer,
                "created_by": created_by,
                "expected_revision": expected_revision,
            },
        )

    @mcp.tool()
    def claim_task(
        task_id: str,
        agent_id: str,
        file_patterns: List[str],
        lease_minutes: float = 30,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Claim a task and file patterns, detecting active conflicts and expired leases."""
        return tools.call_tool(
            "claim_task",
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "file_patterns": file_patterns,
                "lease_minutes": lease_minutes,
                "expected_revision": expected_revision,
            },
        )

    @mcp.tool()
    def release_claim(
        task_id: str,
        agent_id: str,
        reason: str = "done",
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Release an active claim."""
        return tools.call_tool(
            "release_claim",
            {"task_id": task_id, "agent_id": agent_id, "reason": reason, "expected_revision": expected_revision},
        )

    @mcp.tool()
    def check_file_claims(paths: List[str]) -> Dict[str, Any]:
        """Return active claims covering concrete repo-root relative paths."""
        return tools.call_tool("check_file_claims", {"paths": paths})

    @mcp.tool()
    def update_task(
        task_id: str,
        agent_id: str,
        status: str,
        note: Optional[str] = None,
        evidence: Optional[str] = None,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update a task status except final done approval, which must use review_task."""
        return tools.call_tool(
            "update_task",
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "status": status,
                "note": note,
                "evidence": evidence,
                "expected_revision": expected_revision,
            },
        )

    @mcp.tool()
    def complete_task(
        task_id: str,
        agent_id: str,
        evidence: str,
        override_dependencies: bool = False,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Move an owned in-progress task to review after dependency checks."""
        return tools.call_tool(
            "complete_task",
            {
                "task_id": task_id,
                "agent_id": agent_id,
                "evidence": evidence,
                "override_dependencies": override_dependencies,
                "expected_revision": expected_revision,
            },
        )

    @mcp.tool()
    def review_task(
        task_id: str,
        reviewer_id: str,
        result: str,
        note: Optional[str] = None,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Approve a review task to done, or reject it back to in_progress."""
        return tools.call_tool(
            "review_task",
            {
                "task_id": task_id,
                "reviewer_id": reviewer_id,
                "result": result,
                "note": note,
                "expected_revision": expected_revision,
            },
        )

    @mcp.tool()
    def record_decision(
        title: str,
        decision: str,
        rationale: str,
        impact: Optional[str] = None,
        supersedes: Optional[str] = None,
        actor: str = "system",
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record an append-only project decision."""
        return tools.call_tool(
            "record_decision",
            {
                "title": title,
                "decision": decision,
                "rationale": rationale,
                "impact": impact,
                "supersedes": supersedes,
                "actor": actor,
                "expected_revision": expected_revision,
            },
        )

    @mcp.tool()
    def record_handoff(
        agent_id: str,
        task_id: str,
        summary: str,
        changed_files: List[str],
        verification: str,
        open_issues: str,
        expected_revision: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Record handoff summary, changed files, verification, open issues, and risks."""
        return tools.call_tool(
            "record_handoff",
            {
                "agent_id": agent_id,
                "task_id": task_id,
                "summary": summary,
                "changed_files": changed_files,
                "verification": verification,
                "open_issues": open_issues,
                "expected_revision": expected_revision,
            },
        )

    @mcp.tool()
    def get_audit_log(since_revision: Optional[int] = None) -> Dict[str, Any]:
        """Return append-only events after since_revision, or all events."""
        return tools.call_tool("get_audit_log", {"since_revision": since_revision})

    @mcp.tool()
    def render_markdown(expected_revision: Optional[int] = None) -> Dict[str, Any]:
        """Render generated Markdown status files from state.json."""
        return tools.call_tool("render_markdown", {"expected_revision": expected_revision})

    return mcp


def main() -> None:
    create_mcp().run(transport="stdio")


if __name__ == "__main__":
    main()
