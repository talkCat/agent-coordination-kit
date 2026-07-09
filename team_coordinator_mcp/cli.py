"""Small local CLI for smoke testing the coordinator without an MCP client."""

import argparse
import json
from pathlib import Path

from .server import main as serve
from .tools import TeamCoordinatorTools


def print_json(value):
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="team-coordinator")
    parser.add_argument("--root", default=".", help="Workspace root")
    parser.add_argument("--docs-dir", default=None, help="Markdown output directory")
    sub = parser.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init")
    init.add_argument("--goal", default="")

    sub.add_parser("context")
    sub.add_parser("render")
    sub.add_parser("audit")
    sub.add_parser("serve")

    args = parser.parse_args()
    if args.cmd == "serve":
        serve()
        return

    tools = TeamCoordinatorTools(Path(args.root), Path(args.docs_dir) if args.docs_dir else None)
    if args.cmd == "init":
        print_json(tools.call_tool("init_workspace", {"root": args.root, "docs_dir": args.docs_dir, "goal": args.goal}))
    elif args.cmd == "context":
        print_json(tools.call_tool("get_context_bundle", {}))
    elif args.cmd == "render":
        print_json(tools.call_tool("render_markdown", {}))
    elif args.cmd == "audit":
        print_json(tools.call_tool("get_audit_log", {}))


if __name__ == "__main__":
    main()
