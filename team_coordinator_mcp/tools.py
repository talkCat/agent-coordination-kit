"""Tool facade used by both CLI and the stdio MCP server."""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .core import CoordinatorError, CoordinatorStore


class TeamCoordinatorTools:
    def __init__(self, default_root: Optional[Path] = None, default_docs_dir: Optional[Path] = None):
        self.default_root = Path(default_root or ".").resolve()
        self.default_docs_dir = Path(default_docs_dir).resolve() if default_docs_dir else None
        self.store: Optional[CoordinatorStore] = None

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            self._tool("init_workspace", ["root", "docs_dir", "goal", "expected_revision"]),
            self._tool("get_context_bundle", ["role", "scope"]),
            self._tool("register_agent", ["role", "display_name", "scope", "expected_revision"]),
            self._tool("heartbeat_agent", ["agent_id"]),
            self._tool(
                "create_task",
                ["title", "scope", "acceptance", "priority", "depends_on", "reviewer", "created_by", "expected_revision"],
            ),
            self._tool("claim_task", ["task_id", "agent_id", "file_patterns", "lease_minutes", "expected_revision"]),
            self._tool("release_claim", ["task_id", "agent_id", "reason", "expected_revision"]),
            self._tool("check_file_claims", ["paths"]),
            self._tool("update_task", ["task_id", "agent_id", "status", "note", "evidence", "expected_revision"]),
            self._tool("complete_task", ["task_id", "agent_id", "evidence", "override_dependencies", "expected_revision"]),
            self._tool("review_task", ["task_id", "reviewer_id", "result", "note", "expected_revision"]),
            self._tool("record_decision", ["title", "decision", "rationale", "impact", "supersedes", "actor", "expected_revision"]),
            self._tool(
                "record_handoff",
                ["agent_id", "task_id", "summary", "changed_files", "verification", "open_issues", "expected_revision"],
            ),
            self._tool("get_audit_log", ["since_revision"]),
            self._tool("render_markdown", ["expected_revision"]),
        ]

    @staticmethod
    def _tool(name: str, properties: List[str]) -> Dict[str, Any]:
        return {
            "name": name,
            "description": "Agent Coordination Kit tool: %s" % name,
            "inputSchema": {
                "type": "object",
                "properties": {prop: {} for prop in properties},
                "additionalProperties": True,
            },
        }

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = dict(arguments or {})
        try:
            handler = getattr(self, "_call_%s" % name)
        except AttributeError:
            return self._error(ValueError("unknown tool: %s" % name))
        try:
            return handler(args)
        except Exception as exc:
            return self._error(exc)

    def _error(self, exc: Exception) -> Dict[str, Any]:
        details = getattr(exc, "details", {})
        if isinstance(exc, CoordinatorError):
            message = str(exc)
        else:
            message = str(exc)
        return {"error": {"type": exc.__class__.__name__, "message": message, "details": details}}

    def _ensure_store(self) -> CoordinatorStore:
        if self.store is None:
            self.store = CoordinatorStore(self.default_root, self.default_docs_dir)
        return self.store

    def _call_init_workspace(self, args: Dict[str, Any]) -> Dict[str, Any]:
        root = Path(args.get("root") or self.default_root).resolve()
        docs_dir = Path(args["docs_dir"]).resolve() if args.get("docs_dir") else self.default_docs_dir
        self.store = CoordinatorStore(root, docs_dir)
        return self.store.init_workspace(goal=args.get("goal", ""), expected_revision=args.get("expected_revision"))

    def _call_get_context_bundle(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().get_context_bundle(role=args.get("role"), scope=args.get("scope"))

    def _call_register_agent(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().register_agent(
            args["role"],
            args["display_name"],
            args["scope"],
            expected_revision=args.get("expected_revision"),
        )

    def _call_heartbeat_agent(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().heartbeat_agent(args["agent_id"])

    def _call_create_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().create_task(
            args["title"],
            args["scope"],
            args.get("acceptance", []),
            priority=args.get("priority", "P1"),
            depends_on=args.get("depends_on"),
            reviewer=args.get("reviewer"),
            created_by=args.get("created_by", "system"),
            expected_revision=args.get("expected_revision"),
        )

    def _call_claim_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().claim_task(
            args["task_id"],
            args["agent_id"],
            args["file_patterns"],
            lease_minutes=args.get("lease_minutes", 30),
            expected_revision=args.get("expected_revision"),
        )

    def _call_release_claim(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().release_claim(
            args["task_id"],
            args["agent_id"],
            reason=args.get("reason", "done"),
            expected_revision=args.get("expected_revision"),
        )

    def _call_check_file_claims(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().check_file_claims(args["paths"])

    def _call_update_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().update_task(
            args["task_id"],
            args["agent_id"],
            args["status"],
            note=args.get("note"),
            evidence=args.get("evidence"),
            expected_revision=args.get("expected_revision"),
        )

    def _call_complete_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().complete_task(
            args["task_id"],
            args["agent_id"],
            args["evidence"],
            override_dependencies=args.get("override_dependencies", False),
            expected_revision=args.get("expected_revision"),
        )

    def _call_review_task(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().review_task(
            args["task_id"],
            args["reviewer_id"],
            args["result"],
            note=args.get("note"),
            expected_revision=args.get("expected_revision"),
        )

    def _call_record_decision(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().record_decision(
            args["title"],
            args["decision"],
            args["rationale"],
            impact=args.get("impact"),
            supersedes=args.get("supersedes"),
            actor=args.get("actor", "system"),
            expected_revision=args.get("expected_revision"),
        )

    def _call_record_handoff(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().record_handoff(
            args["agent_id"],
            args["task_id"],
            args["summary"],
            args.get("changed_files", []),
            args.get("verification", ""),
            args.get("open_issues", ""),
            expected_revision=args.get("expected_revision"),
        )

    def _call_get_audit_log(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().get_audit_log(since_revision=args.get("since_revision"))

    def _call_render_markdown(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return self._ensure_store().render_markdown(expected_revision=args.get("expected_revision"))
