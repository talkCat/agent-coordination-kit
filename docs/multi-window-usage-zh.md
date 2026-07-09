# Agent Coordination Kit 多窗口使用手册

本文说明多个 AI 对话窗口如何围绕同一个项目目标协作。它是通用操作手册，不绑定任何具体业务项目。

## 1. 核心约定

每个协作目标使用一个 `RUN_ID` 标识，由第一个“协调窗口”创建，后续窗口只复用这个 `RUN_ID`。

推荐变量：

```text
PROJECT_ROOT=<当前项目根目录>
RUN_ID=<YYYYMMDD-HHMMSS-任务简称>
DOCS_DIR=${PROJECT_ROOT}/.agent-coordinator/runs/${RUN_ID}
```

含义：

- `PROJECT_ROOT`：当前项目根目录，通常一个项目固定不变。
- `RUN_ID`：一次协作任务的编号，例如 `20260709-153000-langflow-sync`。
- `DOCS_DIR`：本次协作运行的 Markdown 输出目录，用于隔离不同协作目标的人类可读文档。

后续窗口不重新创建 `RUN_ID`，只接入同一个 `RUN_ID`。

## 2. 第一个窗口：协调窗口

第一个窗口建议命名为“协调窗口”，角色是 `coordinator`。它只需要做一次初始化。

建议开场输入：

```text
请使用 team-agent-coordinator skill，并使用 team-coordinator-mcp。
不要用 shell、Python 或 local facade 替代 MCP 工具。

你是 coordinator。

当前项目根目录是：
PROJECT_ROOT=<当前项目根目录>

请生成一个 RUN_ID，格式为：
YYYYMMDD-HHMMSS-任务简称

本次协作目标是：
<填写本次统一目标>

请执行：
1. init_workspace(root=PROJECT_ROOT, docs_dir=PROJECT_ROOT/.agent-coordinator/runs/RUN_ID, goal=本次协作目标)
2. get_context_bundle()
3. register_agent(role="coordinator", display_name="coordinator-RUN_ID", scope=["**"])
4. create_task 创建本次任务板
5. record_decision 记录关键决策
6. render_markdown()
7. 最后把 PROJECT_ROOT、RUN_ID、DOCS_DIR 和任务列表输出给我，供其他窗口使用。
```

协调窗口输出后，需要保存：

```text
PROJECT_ROOT=<项目根目录>
RUN_ID=<协调窗口生成的 run id>
DOCS_DIR=<Markdown 输出目录>
```

这三项就是后续窗口的接入口。

## 3. 其他窗口：第一次打开时输入一次

每个新窗口只需要在打开时输入一次启动说明，不需要每条消息重复。

通用模板：

```text
请使用 team-agent-coordinator skill，并使用 team-coordinator-mcp。
不要用 shell、Python 或 local facade 替代 MCP 工具。

PROJECT_ROOT=<协调窗口输出的 PROJECT_ROOT>
RUN_ID=<协调窗口输出的 RUN_ID>
DOCS_DIR=<协调窗口输出的 DOCS_DIR>

你是 <role>。
scope=<本窗口负责的 repo 相对路径 glob>

请先调用 get_context_bundle(role=<role>, scope=<scope>) 查看当前任务、active claims、decisions 和 handoffs。
然后 register_agent(role=<role>, display_name="<role>-<简短窗口名>", scope=<scope>)。
选择适合当前 role 的任务。
改代码前调用 claim_task()。
修改具体文件前调用 check_file_claims()。
完成后调用 complete_task()，结束前调用 record_handoff()。
```

之后同一个窗口继续工作时，不需要重复这段。直接说具体任务即可，例如：

```text
继续处理刚才 claim 的 FE-001，先检查当前 claim 和任务状态，然后继续实现。
```

## 4. 角色换窗口怎么办

如果一个角色换了新窗口，例如前端窗口断开、卡住或上下文过长，不要复用旧窗口的 agent 身份。新窗口按新的 agent 注册，然后接管旧任务。

新窗口开场：

```text
请使用 team-agent-coordinator skill，并使用 team-coordinator-mcp。
不要用 shell、Python 或 local facade 替代 MCP 工具。

PROJECT_ROOT=<原项目根目录>
RUN_ID=<原 RUN_ID>
DOCS_DIR=<原 DOCS_DIR>

你是 frontend。
scope=["前端相关路径/**"]

这是 frontend 的新窗口，用于接手之前的 frontend 工作。
请调用 get_context_bundle(role="frontend", scope=scope)，查看已有 frontend agent、active claims、handoffs 和 FE 任务状态。
然后 register_agent(role="frontend", display_name="frontend-takeover-<时间>", scope=scope)。
如果发现旧 frontend agent 有 active claim：
1. 如果旧窗口还在，请提示我先让旧窗口 record_handoff 并 release_claim。
2. 如果旧窗口已经不可用，请检查 claim 是否过期；过期后再 claim_task 接管。
3. 如果未过期且必须接管，请让 coordinator 决策后再处理。
```

推荐旧窗口退出前执行：

```text
record_handoff
release_claim
render_markdown
```

如果旧窗口已经丢失，则新窗口通过 `get_context_bundle()` 查看旧窗口留下的 claim、handoff、task 状态，再按 lease 过期或 coordinator 决策接管。

## 5. 是否每次都要输入完整说明

不需要。

规则：

- 新开一个窗口：输入一次启动说明。
- 同一窗口持续工作：不用重复。
- 同一窗口上下文压缩后：建议简短提醒一次 `PROJECT_ROOT/RUN_ID/role/scope`。
- 换新窗口接手：必须输入一次接手说明。
- 换角色：必须重新注册 agent，不要沿用旧角色。

最小续接提示：

```text
继续使用 team-agent-coordinator 和 team-coordinator-mcp。
PROJECT_ROOT=<项目根目录>
RUN_ID=<RUN_ID>
你是 <role>，scope=<scope>。
请先 get_context_bundle，然后继续上次任务。
```

## 6. 推荐角色模板

### 6.1 Frontend

```text
你是 frontend。
scope=["apps/**", "frontend/**", "src/views/**", "src/api/**"]
```

### 6.2 Backend

```text
你是 backend。
scope=["backend/**", "server/**", "src/backend/**", "src/api/**"]
```

### 6.3 Platform / Third Party

```text
你是 custom。
scope=["platform/**", "vendor/**", "third-party/**"]
```

如果是 Langflow 类任务，可以写：

```text
你是 langflow。
scope=["langflow-new/**", "langflow/**"]
```

### 6.4 Tester

```text
你是 tester。
scope=["**"]
```

tester 负责验证并调用：

```text
review_task(result="approved")
```

或：

```text
review_task(result="rejected", note="失败原因")
```

## 7. 当前 V1 限制

当前 V1 中：

- `PROJECT_ROOT` 主要由 MCP server 启动配置和 `init_workspace(root=...)` 决定。
- `RUN_ID` 主要体现在 `docs_dir`，用于隔离 Markdown 输出。
- `RUN_ID` 还不是 MCP 的一等对象。
- 同一个 `PROJECT_ROOT` 默认只有一份机器事实源：`.agent-coordinator/events.jsonl` 和 `.agent-coordinator/state.json`。

因此，当前最稳妥的操作是：

- 一个 `PROJECT_ROOT` 同一时间只维护一个主要协作目标。
- 协调窗口创建并输出 `PROJECT_ROOT/RUN_ID/DOCS_DIR`。
- 其他窗口开场时复制这三个值。
- 如果需要多个不相关协作目标并行运行，优先使用不同项目根目录，或等待后续 `start_run()` 模型。

## 8. 建议后续增强

为了减少手工输入，可以把 MCP 扩展为“运行会话模型”。

建议新增工具：

```text
start_run(project_root, title, goal)
get_current_run(project_root?)
list_runs(project_root?)
join_run(run_id, role, scope)
switch_run(run_id)
```

建议新增状态文件：

```text
${PROJECT_ROOT}/.agent-coordinator/current-run.json
```

这样新窗口只需要说：

```text
请使用 team-agent-coordinator，加入当前项目的 current run，角色是 frontend。
```

MCP 就能自动找到当前 `PROJECT_ROOT`、`RUN_ID` 和 `DOCS_DIR`。

## 9. Practical Default

当前版本最可行的使用方式：

1. 协调窗口先初始化并输出 `PROJECT_ROOT/RUN_ID/DOCS_DIR`。
2. 其他窗口打开时复制一次这三个值和自己的 `role/scope`。
3. 同一窗口内不用重复。
4. 换窗口接手时重新注册 agent，并根据旧 claim/handoff 接管。
5. 每次结束前都 `record_handoff()`，这样换窗口不会丢上下文。
