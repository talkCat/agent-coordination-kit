# Agent Coordination Kit

Generic repo-local coordination kit for multiple AI agents working in one shared workspace.

中文设计方案和使用手册：[docs/design-and-usage-zh.md](docs/design-and-usage-zh.md)

V1 scope:

- single repo
- single shared filesystem/workspace
- one MCP server per workspace
- no multi-machine strong consistency

## Contents

- `team_coordinator_mcp/core.py`: event-sourced state machine, lock, claims, review, handoff, Markdown render.
- `team_coordinator_mcp/server.py`: dependency-free stdio MCP server.
- `team_coordinator_mcp/cli.py`: local smoke-test CLI.
- `skills/team-agent-coordinator/SKILL.md`: client behavior skill.
- `tests/`: stdlib `unittest` coverage.

## Install For Local Development

```bash
cd /home/dev/bxc/longflow_combine/agent-coordination-kit
python3 -m pip install -e .
```

The implementation has no runtime dependencies beyond Python stdlib.

## MCP Server

Example MCP command:

```bash
ACK_WORKSPACE_ROOT=/home/dev/bxc/longflow_combine \
ACK_DOCS_DIR=/home/dev/bxc/longflow_combine/plan \
python3 -m team_coordinator_mcp.server
```

Client configuration can point to the same command. The server exposes:

- `init_workspace`
- `get_context_bundle`
- `register_agent`
- `heartbeat_agent`
- `create_task`
- `claim_task`
- `release_claim`
- `check_file_claims`
- `update_task`
- `complete_task`
- `review_task`
- `record_decision`
- `record_handoff`
- `get_audit_log`
- `render_markdown`

## CLI Smoke Test

```bash
cd /home/dev/bxc/longflow_combine/agent-coordination-kit
python3 -m team_coordinator_mcp.cli --root /tmp/ack-demo init --goal "Demo"
python3 -m team_coordinator_mcp.cli --root /tmp/ack-demo context
python3 -m team_coordinator_mcp.cli --root /tmp/ack-demo render
```

## Skill

The repo-local skill is:

```text
skills/team-agent-coordinator/SKILL.md
```

To make it discoverable by Codex globally, copy or symlink that directory into:

```text
${CODEX_HOME:-$HOME/.codex}/skills/team-agent-coordinator
```

## Langflow Validation Scenario

Use:

- root: `/home/dev/bxc/longflow_combine`
- docs dir: `/home/dev/bxc/longflow_combine/plan`

Do not call `render_markdown()` into `/home/dev/bxc/longflow_combine/plan` until you decide whether existing files with the fixed generated names should remain manual. The renderer will skip non-generated fixed files instead of overwriting them.
