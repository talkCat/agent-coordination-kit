---
name: team-agent-coordinator
description: Use when multiple AI agents or chat sessions coordinate work in one repo, especially before editing files, taking over tasks, resolving file-claim conflicts, handing off progress, or reviewing another agent's task.
---

# Team Agent Coordinator

## Core Rule

Treat `team-coordinator-mcp` as the coordination authority. `events.jsonl` is the fact source, `state.json` is a projection, and generated Markdown is a read-only human view.

This skill is a behavior contract, not a safety boundary. If a rule matters, call the MCP tool that enforces it.

## Window Bootstrap

For a new chat window, ask for or use the coordinator-provided `PROJECT_ROOT`, `RUN_ID`, `DOCS_DIR`, `role`, and `scope` once at startup. Do not require the user to repeat them in every message.

Use `RUN_ID` as the human coordination label for the current run. In V1, the MCP state is still rooted at `PROJECT_ROOT`; `RUN_ID` is mainly reflected by `DOCS_DIR`.

If a role moves to a new window, register a new agent session instead of reusing the old agent identity. Inspect existing claims and handoffs before taking over.

Do not use shell, Python scripts, or a local facade as a substitute for available `team-coordinator-mcp` tools.

## Start Workflow

1. Call `get_context_bundle(role?, scope?)`, or read generated `AGENTS.md`, `TASK_BOARD.md`, `DECISIONS.md`, and `HANDOFF_LOG.md` when MCP is not connected.
2. Call `register_agent(role, display_name, scope, expected_revision?)`.
3. Pick a task that matches your role and scope.
4. Before editing code, call `claim_task(task_id, agent_id, file_patterns, lease_minutes?, expected_revision?)`.
5. Before modifying concrete files, call `check_file_claims(paths)`.

If another active claim covers your target path, do not edit it. Choose another task, narrow your scope, or mark your task `blocked` with the reason.

## Work Rules

- Work only inside the registered scope and claimed file patterns.
- Treat `claim_task` warnings about unfinished dependencies as permission to investigate, not permission to deliver.
- If dependencies, interfaces, acceptance criteria, or file ownership are unclear, call `update_task(..., "blocked", note=...)`.
- Use `heartbeat_agent(agent_id)` during long sessions to keep the lease fresh.
- Do not edit generated Markdown files directly. Use MCP calls and `render_markdown()`.
- Do not treat file claims as a replacement for tests, review, or Git conflict resolution.

## Completion Workflow

1. Run the narrowest useful verification for your changes.
2. Call `complete_task(task_id, agent_id, evidence, override_dependencies=false, expected_revision?)`.
3. Call `record_handoff(agent_id, task_id, summary, changed_files, verification, open_issues, expected_revision?)`.
4. Call `render_markdown(expected_revision?)` when you need refreshed human-readable status.

Executors move tasks to `review`; they do not approve their own work. A reviewer, tester, or coordinator calls `review_task()`.

## Review Rules

- If the task has a reviewer, only that reviewer, a tester, or a coordinator can approve it.
- If the task has no reviewer, a tester or coordinator can approve it.
- The owner cannot approve their own task unless the owner role is `coordinator`.
- Use `review_task(..., "rejected", note=...)` for missing acceptance criteria or failed verification; this returns the task to `in_progress`.

## Handoff Content

Keep handoffs concise and evidence-based:

- `summary`: what changed and current state.
- `changed_files`: repo-root relative paths only.
- `verification`: commands run and observed results.
- `open_issues`: blockers, risks, or next decisions.

MCP records out-of-scope or unclaimed changed files as risks.
