"""Minimal stdio MCP server.

This implements the JSON-RPC surface needed by MCP clients without requiring
the external `mcp` Python package in the target environment.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .tools import TeamCoordinatorTools


def read_message() -> Optional[Dict[str, Any]]:
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        line = line.decode("utf-8").strip()
        if not line:
            break
        key, _, value = line.partition(":")
        headers[key.lower()] = value.strip()
    length = int(headers.get("content-length", "0"))
    if length <= 0:
        return None
    payload = sys.stdin.buffer.read(length).decode("utf-8")
    return json.loads(payload)


def write_message(message: Dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(b"Content-Length: " + str(len(payload)).encode("ascii") + b"\r\n\r\n" + payload)
    sys.stdout.buffer.flush()


class MCPServer:
    def __init__(self):
        root = Path(os.environ.get("ACK_WORKSPACE_ROOT", ".")).resolve()
        docs = os.environ.get("ACK_DOCS_DIR")
        self.tools = TeamCoordinatorTools(default_root=root, default_docs_dir=Path(docs).resolve() if docs else None)

    def handle(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = request.get("method")
        request_id = request.get("id")
        if method and method.startswith("notifications/"):
            return None
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "team-coordinator-mcp", "version": "0.1.0"},
                }
            elif method == "tools/list":
                result = {"tools": self.tools.list_tools()}
            elif method == "tools/call":
                params = request.get("params") or {}
                result_data = self.tools.call_tool(params.get("name"), params.get("arguments") or {})
                is_error = "error" in result_data
                result = {
                    "isError": is_error,
                    "content": [{"type": "text", "text": json.dumps(result_data, ensure_ascii=False, indent=2)}],
                }
            else:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method not found"}}
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": str(exc)}}

    def serve_forever(self) -> None:
        while True:
            request = read_message()
            if request is None:
                break
            response = self.handle(request)
            if response is not None and "id" in request:
                write_message(response)


def main() -> None:
    MCPServer().serve_forever()


if __name__ == "__main__":
    main()
