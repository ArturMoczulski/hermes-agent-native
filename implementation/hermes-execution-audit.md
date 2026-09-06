# Hermes execution boundary audit — AN-17

Audit snapshot: 2026-09-06, committed fork `f7c54d1452418bf63b110c98bdf40e50e002919d`.
This is a source inventory and delivery map. It does not enable managed execution.

The existing Hermes engine remains a suitable starting point for one controlled
Builder run. The framework currently exposes inactive root CRUD and separately
verified host primitives. Native model entry points do not call those controls.
Reuse the engine with explicit host admission and tool/environment enforcement;
a check only around the main chat loop would miss auxiliary model calls and
nested tool execution. The remaining live proof is specified below.

## Exact baseline and scope

- Upstream source: `006b1beb00d9d25230571d14277aca3d70e5e11f`, verified on the
  [official Hermes commit page](https://github.com/NousResearch/hermes-agent/commit/006b1beb00d9d25230571d14277aca3d70e5e11f).
  Pin this immutable commit for the current integration; the previously cited
  `v2026.8.31` release is research context, not the selected source snapshot.
- Fork snapshot: `f7c54d1452418bf63b110c98bdf40e50e002919d`, branch
  `codex/astra-capability-proof`, **19 fork commits after that baseline**.
  The only configured remote is `git@github.com:ArturMoczulski/hermes-agent-native.git`.
  This snapshot is local; this audit does not claim it was pushed.
- Local `main`, `origin/main` and `origin/HEAD` point to the upstream baseline at
  review. These local tracking refs are not claims about today's remote HEAD.
  The checkout is shallow; no upstream branch ancestry or release-tag equivalence
  beyond the verified immutable commit is inferred.
- [The machine-readable fork inventory](hermes-fork-inventory.json) records every
  changed path and its before/after Git blob: **90 paths, comprising 9 modified
  inherited files and 81 added files**. Its comparison deliberately ends at the
  snapshot above, before these audit documents. Later changes require a new review.
- Package metadata still declares Hermes `0.21.0`; it is not an agent-native
  release version. The inventory pins `pyproject.toml`, `uv.lock`, the npm and Nix
  locks, and Plane Compose/image records by blob. These describe source inputs,
  not a sealed running release or proof of the installed dependency tree.
- Existing uncommitted `AGENTS.md`, `README.md` and
  `tests/tools/test_astra_capture_pipeline.py` are excluded and preserved. The
  current checkout's First Builder entry instructions and that characterization
  test must not be mistaken for files contained in the pinned commit. AN-26/57
  must explicitly load and package the approved Builder instructions; AN-18
  must establish committed, reproducible capability evidence.

## Changes already made to inherited code

All other additions are listed individually in the JSON inventory. None of the
native model-entry or lower tool-dispatch files in the matrices below has yet
received a framework admission fence.

| Inherited file | Committed change | Established limit |
| --- | --- | --- |
| [cli_modal_mixin.py](../hermes_cli/cli_modal_mixin.py) | One-shot computer-use approval follows the existing explicit/default-deny policy instead of waiting for an unavailable modal. | Fixes the characterized CLI stall; no new permission or successful desktop-edit proof. |
| [kanban_db_connect.py](../hermes_cli/kanban_db_connect.py) | Initializes namespaced `agent_native` schema through the existing SQLite connection path. | Shared storage initialization, not run admission or a second planning board. |
| [web_server.py](../hermes_cli/web_server.py) | Registers the owner-authenticated root CRUD router. | No launch endpoint. |
| [Docker backend](../tools/environments/docker.py) | Adds the overridable automatic-mount seam used by the restricted environment. | Native defaults remain; only the explicit restricted factory applies its closed policy. |
| [pyproject.toml](../pyproject.toml) | Includes `agent_native` in package discovery. | Does not package or activate a protected Builder release. |
| [web/package.json](../web/package.json), [package-lock.json](../package-lock.json) | Adds the web Playwright command and pinned test dependency. | Browser tooling exists; desktop tests are not framework acceptance. |
| [App.tsx](../web/src/App.tsx) | Adds the Agents route and navigation. | Roster entries remain Not started. |
| [.gitignore](../.gitignore) | Excludes generated web test reports. | No runtime change. |

The added control code covers identity, protected profile projections, a restricted
Docker tool environment, scoped Plane reads/writes and uncertain-write recovery.
The added router and [Agents page](../web/src/pages/AgentsPage.tsx) expose only
inactive roots. Planning, product/Builder documents, the Plane skill and local
service/probes are additional source artifacts; their existence does not load
skills or start an agent.

## License and notice inventory

These are the notice files present in this source snapshot; they remain unchanged.
This inventory is not a dependency-wide distribution review. Packaging the
running release must retain applicable bundled notices and review its actual
selected dependencies and assets.

| Scope | Existing notice |
| --- | --- |
| Hermes source | [MIT, Nous Research 2025](../LICENSE). |
| Humanizer skill | [MIT, Siqi Chen 2025](../skills/creative/humanizer/LICENSE). |
| Document skills | MIT, Nous Research 2026: [docx](../skills/productivity/docx/LICENSE), [powerpoint](../skills/productivity/powerpoint/LICENSE), [xlsx](../skills/productivity/xlsx/LICENSE), [pdf](../skills/productivity/pdf/LICENSE). |
| Desktop bots plugin | [MIT, Nous Research 2026](../apps/desktop/src/plugins/hermes-bots/LICENSE). |
| Achievements plugin | [MIT, Hermes Achievements contributors 2026](../plugins/hermes-achievements/LICENSE). |
| Security-guidance plugin | [Apache 2.0 license](../plugins/security-guidance/LICENSE) and [Anthropic attribution notice](../plugins/security-guidance/NOTICE). |
| Optional ast-grep skill | [MIT, Yeongyu Kim 2026](../optional-skills/software-development/ast-grep/LICENSE). |
| Separate Plane service | Retained [AGPLv3 license](../ops/plane/LICENSE.plane); deployment/version evidence is in [Plane operations](../ops/plane/README.md). |

## Interpreting the execution matrices

**Current behavior** reports inspected code. Existing native authentication,
approval, session leases and sandbox controls are real, but are not framework
agent/run authority. A native profile/session/task ID cannot choose a trusted
actor. The only integrated product entry is owner CRUD; it never executes a run.
No native model entry below is claimed disabled today.

**Required managed disposition** is the explicit implementation target: integrate
selected paths through the framework or reject managed use until integrated.
That is the classification requested by AN-17, with the current enforcement gap
shown separately. AN-7/24/18/57 retain actual enforcement and live acceptance.
The matrices are documentation, not a runtime allowlist or granted capability.
Line numbers refer to the pinned fork snapshot.

## Foreground entry points and shared dispatch

| Surface | Exact call sites | Verified current behavior | Required managed disposition / delivery owner |
|---|---|---|---|
| Framework root API | [hermes_cli/web_routers/agent_native.py:13](../hermes_cli/web_routers/agent_native.py#L13) `owner_session`; `:30` `list_agents`; `:36` `create_agent`; `:45` `read_agent` | Owner token maps to `identity.OWNER`; CRUD only. No turn, planning-tool or activation route. | Keep trusted owner CRUD; connect explicit managed execution through admission, not by changing create into an untracked model call. AN-7, AN-24, AN-28. |
| Python CLI / direct programmatic execution | [hermes_cli/cli_agent_setup_mixin.py:474](../hermes_cli/cli_agent_setup_mixin.py#L474) `_init_agent` constructs at `:513`; [hermes_cli/cli_chat_turn_mixin.py:268](../hermes_cli/cli_chat_turn_mixin.py#L268) `_chat_run_agent` calls at `:306`; [cli.py:4096](../cli.py#L4096) `_run_quiet_single_query` calls at `:4099`; [run_agent.py:1433](../run_agent.py#L1433) `main` constructs/calls at `:1477,1491`; [run_agent.py:211](../run_agent.py#L211) `AIAgent` is directly importable | Native configured runtime and sessions, without framework admission. Quiet CLI has a separate native Kanban continuation at [cli.py:4040](../cli.py#L4040) `_run_kanban_goal_loop_q` (`:4068` calls the model). | Managed requests must carry host-issued admission; direct legacy creation/resume/continuation must reject managed identities until routed. AN-7, AN-24, AN-57. |
| Dedicated CLI one-shot | [hermes_cli/oneshot.py:163](../hermes_cli/oneshot.py#L163) `run_oneshot` → `:343` `_run_agent` → construction `:389`, conversation `:413` | Separate native agent creation/cleanup path. | Same admission gate; not an alternate untracked Builder launcher. AN-7, AN-18. |
| Dashboard PTY | [hermes_cli/web_routers/chat_ws.py:405](../hermes_cli/web_routers/chat_ws.py#L405) `pty_ws`; [hermes_cli/web_server_chat.py:298](../hermes_cli/web_server_chat.py#L298) `_resolve_chat_argv`; [hermes_cli/pty_session.py:164](../hermes_cli/pty_session.py#L164) `PtySessionRegistry.attach_or_spawn`; [hermes_cli/pty_bridge.py:83](../hermes_cli/pty_bridge.py#L83) `PtyBridge.spawn` | Authenticated PTY spawns native TUI, retains/reconnects it. `_resolve_chat_argv` inherits provider credentials and can select a profile; it does not select a framework agent/run. | Do not equate PTY attachment/profile selection with Builder identity or lifetime. Managed chat becomes a service-owned conversation; deny raw managed-profile TUI launches until integrated. AN-7, AN-28, AN-57. |
| Dashboard RPC / TUI turns | [hermes_cli/web_routers/chat_ws.py:542](../hermes_cli/web_routers/chat_ws.py#L542) `gateway_ws` → [tui_gateway/ws.py:239](../tui_gateway/ws.py#L239) `handle_ws`; [tui_gateway/methods_prompt.py:534](../tui_gateway/methods_prompt.py#L534) `prompt.submit` → `:468` `_run_after_agent_ready`; [tui_gateway/server.py:2259](../tui_gateway/server.py#L2259) `_make_agent` constructs at `:2281`; [tui_gateway/prompt_turn.py:753](../tui_gateway/prompt_turn.py#L753) `_run_prompt_submit`, `:82` `_admit_prompt_turn`, `:507` `_invoke_agent` calls at `:551` | Native socket authentication and active-session ownership gates; shared native agent loop. No framework identity or current Plane brief gate. | Translate authenticated owner input into durable framework conversation/activation. Preserve native lease mechanics; add framework admission/stop and record queued vs handled input. AN-7, AN-24, AN-28, AN-30, AN-32. |
| TUI session creation, resume and branch | [tui_gateway/methods_session.py:296](../tui_gateway/methods_session.py#L296) `session.create`; `:787` `session.resume`; `:1843` `_build_branch_agent`; `_resume_cold:712` schedules agent construction and `_maybe_schedule_auto_continue` at `:730` | Native session restoration can schedule continuation without a fresh prompt. A branch can construct another native agent. | Recheck framework identity, current revision, grants and lifecycle on creation, branch and resume. A transcript restore must not revive paused managed work. AN-7, AN-24, AN-30. |
| Optional TUI compute host | [tui_gateway/methods_prompt.py:603](../tui_gateway/methods_prompt.py#L603) dispatches via [compute_host_bridge.py:204](../tui_gateway/compute_host_bridge.py#L204); dispatch errors fall back inline at `methods_prompt.py:618–625`. [host_supervisor.py:309](../tui_gateway/host_supervisor.py#L309) starts a process with inherited credentials at `:314,321`; [compute_host.py:204](../tui_gateway/compute_host.py#L204) invokes the shared prompt turn at `:234` | Optional native process isolation, default off in [server.py:1082](../tui_gateway/server.py#L1082); this is source behavior, not evidence of a configured deployment. It has neither a framework admission context nor the restricted worker environment. | Reject managed use until host-issued authority, explicit credential boundaries and owned process stop are integrated. Never fall back to ungoverned inline execution when managed dispatch fails. AN-7, AN-24, AN-30, AN-57. |
| Foreground-triggered background task | [tui_gateway/methods_prompt.py:953](../tui_gateway/methods_prompt.py#L953) `prompt.background` constructs/runs at `:961`; [hermes_cli/cli_commands_mixin.py:1900](../hermes_cli/cli_commands_mixin.py#L1900) `_handle_background_command` constructs/runs at `:1927,1951` | Starts another native AIAgent from current runtime/tool settings. | Deny this alternate background launch for managed Builder until a separate authorized run/assignment is recorded. AN-7, AN-24, AN-30. |
| Side question / auxiliary fallback | [tui_gateway/methods_prompt.py:968](../tui_gateway/methods_prompt.py#L968) `prompt.btw`; [hermes_cli/cli_commands_mixin.py:1998](../hermes_cli/cli_commands_mixin.py#L1998) `_handle_btw_command`; [agent/side_question.py:102](../agent/side_question.py#L102) `_answer_via_fork`, `:137` `_answer_via_oneshot`, `:148` `answer_side_question`; fallback [agent/oneshot.py:80](../agent/oneshot.py#L80) `run_oneshot` calls `call_llm` at `:104` ([agent/auxiliary_client.py:6938](../agent/auxiliary_client.py#L6938)) | Fork explicitly denies all tools via an empty thread whitelist. On failure/empty answer, an auxiliary model call bypasses AIAgent.run_conversation. | Tool denial is already present; model usage still needs admitted ownership/budget/events or managed-side rejection. A facade-only guard is insufficient. AN-7, AN-24, AN-32, AN-70. |
| Preview repair agent | [tui_gateway/methods_prompt.py:1012](../tui_gateway/methods_prompt.py#L1012) `preview.restart`; construction/conversation `:1054,1057` | Starts hidden agent, applies task cwd override, deliberately leaves its background server alive (`:1052`). Prompt rules alone are not framework grants or job ownership. | Disable for managed profiles until host owns the repair assignment and background job, tool authority and actual stop. AN-7, AN-24, AN-30, AN-57. |
| Native OpenAI-compatible API | [gateway/platforms/api_server_openai_routes.py:409](../gateway/platforms/api_server_openai_routes.py#L409) `_handle_chat_completions`, `:730` `_handle_responses`; [gateway/platforms/api_server.py:2099](../gateway/platforms/api_server.py#L2099) `_create_agent`, `:3622` `_run_agent` calls conversation at `:3678` | Per-request profile/session/provider and native approval/cleanup handling; explicitly bypasses messaging TurnRunner. | Authenticate to framework actor, bind the target root and current admission, or reject managed-profile requests. Gating messaging TurnRunner alone will miss it. AN-7, AN-24, AN-30, AN-32. |
| Native durable runs API | [gateway/platforms/api_server.py:3762](../gateway/platforms/api_server.py#L3762) `_handle_runs` delegates to [gateway/platforms/api_server_runs.py:354](../gateway/platforms/api_server_runs.py#L354) `_handle_runs`; `:542` `_execute_run`; `:463` `_run_agent_sync` calls conversation at `:499` | Its own run/idempotency/stream/approval lifecycle, separate from `_run_agent` and TurnRunner. | Reuse suitable run primitives behind framework admission; native run IDs are not framework authorization. AN-7, AN-18, AN-24, AN-30, AN-32. |
| ACP editor interface | [acp_adapter/session.py:164](../acp_adapter/session.py#L164) `SessionManager.create_session`, `:328` `_restore`, `:367` `_make_agent` constructs at `:418`; [acp_adapter/server.py:776](../acp_adapter/server.py#L776) `HermesACPAgent.prompt` → `:712` `_run_agent_turn`, conversation `:768` | Separate session/cwd runtime with explicitly bound native approval/edit callbacks. Can restore/create agents without the framework. | Reject managed Builder sessions until routed through the same host admission and owner-channel policy. AN-7, AN-24. |
| Shared AIAgent turn facade | [agent/turn_facade.py:22](../agent/turn_facade.py#L22) `TurnFacadeMixin.run_conversation`; native lease at `:77` via [agent/turn_facade_lease.py:232](../agent/turn_facade_lease.py#L232) `admit_durable_turn_lease`; [agent/conversation_loop.py:1390](../agent/conversation_loop.py#L1390) `run_conversation` | Native session lease and relay accounting; no framework soul revision, pause, run or Plane source validation. | Add a fail-closed managed admission/continuation fence here as defense in depth, with actual host admission before model construction/execution. Cover auxiliary calls separately. AN-7, AN-24, AN-30, AN-32. |
| Main agent tool dispatch | [agent/tool_executor.py:628](../agent/tool_executor.py#L628) `_dispatch_authorized_once`; `:1383` `execute_tool_calls_concurrent`; `:1641` `execute_tool_calls_sequential`; `:1698` `execute_tool_calls_segmented` | Native scope, hooks and guardrails; no framework grant/current-run fence. | Revalidate admitted run and action authority immediately at controlled side effects; persist attributable intent/result. AN-24, AN-30, AN-32. |
| Lower/direct tool dispatch | [model_tools.py:801](../model_tools.py#L801) `handle_function_call`; `:697` `_pre_dispatch_guards`; `:754` `_execute_tool` → [tools/registry.py:810](../tools/registry.py#L810) `ToolRegistry.dispatch` | `handle_function_call` accepts caller task/session IDs and skip-hook/middleware flags. Registry dispatch directly invokes handlers. Neither verifies framework context. These are internal host APIs, not proof of worker authentication. | Keep protected dispatch objects/credentials out of workers; provide a run-bound dispatcher that cannot be bypassed by direct handlers or skip flags. A plugin hook alone is insufficient. AN-24, AN-26, AN-57. |
| execute_code nested tools | [tools/code_execution_tool.py:657](../tools/code_execution_tool.py#L657) `execute_code`; [tools/code_execution_rpc.py:28](../tools/code_execution_rpc.py#L28) `_default_dispatch`, `:41` `_handle_rpc_request`, `:70` `_rpc_server_loop`, `:130` `_rpc_poll_loop` | RPC authenticates its token and enforces allowed-tool/count limits; default dispatch calls `model_tools.handle_function_call` with task_id, below `agent.tool_executor`. | Nested calls need the same host-owned run/grant/stop fence and event correlation. Do not treat RPC token or task_id as framework ownership. AN-24, AN-26, AN-30, AN-32. |
| Terminal and file environment selection | [tools/terminal_tool.py:956](../tools/terminal_tool.py#L956) `_acquire_env`; [tools/terminal_tool_backends.py:209](../tools/terminal_tool_backends.py#L209) `_create_environment` selects `_ENV_BUILDERS` at `:204`; [tools/file_tools.py:296](../tools/file_tools.py#L296) `_get_file_ops`, `:254` `_create_terminal_env_for_file_ops`; [tools/terminal_tool_lifecycle.py:184](../tools/terminal_tool_lifecycle.py#L184) `ensure_task_env`; actual restricted primitive [agent_native/environment.py:94](../agent_native/environment.py#L94) `open_environment` | Native terminal/file/lazy-image paths independently create/reuse configured environments. The factory has no framework connection; task-ID normalization/caches can share native containers. Restricted environment primitive exists but is not wired to these paths. | All managed coding/file/nested-tool access must use the explicitly admitted environment and stable run mapping. No fallback to native local/config-selected backend on missing context. AN-24, AN-25, AN-57. |
| TUI shell command RPC | [tui_gateway/methods_tools.py:1362](../tui_gateway/methods_tools.py#L1362) `shell.exec` calls `_captured_exec:170`, reaching `subprocess.run` at `:175` with `shell=True` from `:1377` | Native hardline/dangerous-command checks run first. The subprocess uses the host working directory and has no framework run/environment fence. This differs from the allowlisted dashboard console. | Deny this raw managed shell route until it uses approved run-bound execution and the managed environment. Native command screening does not grant access to the service host. AN-24, AN-25, AN-57. |
| Dashboard command console | [hermes_cli/web_routers/chat_ws.py:249](../hermes_cli/web_routers/chat_ws.py#L249) `console_ws`, `:160` `_execute_console_line` → [hermes_cli/console_engine.py:387](../hermes_cli/console_engine.py#L387) `HermesConsoleEngine.execute`; native cron control `:782` `_cron_run` | Allowlisted command engine, not arbitrary shell and not a model loop; it can invoke native control operations under a selected profile. | Keep owner administration separate from generated-code capability. Managed-profile mutation/dispatch commands must route through domain operations or reject; do not let profile selection bypass the managed boundary. AN-24, AN-7. |


## Background and secondary entry points

| Route | Exact source evidence and present behavior | Required managed disposition |
| --- | --- | --- |
| Gateway scheduled jobs | [gateway/run.py:5022](../gateway/run.py#L5022) `_start_gateway_start_cron_and_housekeeping` resolves the scheduler and starts its thread at `:5055`; [cron/scheduler_provider.py:359](../cron/scheduler_provider.py#L359) `InProcessCronScheduler` calls `tick` at `:406`. Default provider resolution falls back to the built-in on missing/unavailable/error (`:317`). [cron/scheduler.py:2290](../cron/scheduler.py#L2290) `run_job` constructs `AIAgent` through `_construct_cron_agent` (`:2229`, constructor `:2232`) and calls the watchdog (`:2347`); `_run_agent_with_watchdog:1785` calls `agent.run_conversation`. | Treat due job as an activation request bound to a framework agent, current purpose and run authority. Native profile/job identifiers, scheduler fire claims and drain flags are not framework authority. Native cron must not independently launch the managed identity. |
| Other cron fire entrances and catch-up | [tools/cronjob_tools.py:203](../tools/cronjob_tools.py#L203) manual execution and `:300` call the shared `run_one_job`; [gateway/platforms/api_server.py:3494](../gateway/platforms/api_server.py#L3494) supports provider fire over API. [cron/scheduler_provider.py:232](../cron/scheduler_provider.py#L232) `fire_overdue_jobs` spawns provider fire work (`:302`); gateway housekeeping invokes catch-up via [gateway/run.py:4420](../gateway/run.py#L4420). External provider choice does not remove housekeeping or manual/API fire. | Gate the common execution boundary as well as scheduled registration; explicit run and recovery/catch-up cannot bypass it. |
| Detached cron worker | [cron/scheduler.py:3113](../cron/scheduler.py#L3113) `_launch_external_cron_worker` creates an execution payload and launches `python -m cron.scheduler --external-worker-file ...`; `:3181` `Popen` detaches it outside a systemd gateway cgroup when that topology requires it. It subsequently uses the common native execution path. | Propagate host-issued run identity and revocation to the child, or reject this native path for managed profiles. Stopping the gateway is not proof that its detached work stopped. |
| Cron script and monitor branches | [cron/scheduler.py:1252](../cron/scheduler.py#L1252) `_run_no_agent_job` is deliberately model-free; `_apply_monitor_gate:1307` suppresses the model on unchanged observations. Script execution itself starts a subprocess at [cron/scheduler_script.py:357](../cron/scheduler_script.py#L357). A changed monitor continues toward normal agent launch. | Distinguish observation/script effects from model activation. Script execution needs scoped effect authority even when no model runs; changed observations must enter the same managed activation boundary. |
| Gateway heartbeat | [gateway/run_goals.py:105](../gateway/run_goals.py#L105) `_register_heartbeat_watch` starts a poller; `_heartbeat_poll_once:118` skips busy sessions and enqueues the due prompt at `:135`; `_start_heartbeat_poller:139` starts its task at `:155`. State persists, but watcher registration is in-memory and firing resumes only after the user touches `/heartbeat` again (`:107`). | One framework cadence source, with purpose-bound wake events and coalescing/admission; do not claim native heartbeat alone is durable managed autonomy. |
| Gateway goal continuation and judge | [gateway/run_goals.py:230](../gateway/run_goals.py#L230) `_post_turn_goal_continuation` calls `GoalManager.evaluate_after_turn` through an executor at `:252`, then enqueues a new turn at `:269`. [hermes_cli/goals.py:836](../hermes_cli/goals.py#L836) `_call_goal_judge_llm` calls auxiliary `goal_judge` at `:842`; `evaluate_after_turn:1332` also runs completion gates before judging. `run_kanban_goal_loop` calls another worker turn at `:1572`. | Both auxiliary judge expenditure/effects and each continuation need the current managed run/owner policy. Native goal completion must not automatically substitute for framework result acceptance or agent retirement. |
| Independent `/loop` scheduler | [gateway/run_goals.py:398](../gateway/run_goals.py#L398) `_loop_wakeup_watcher` scans persisted loops; `_loop_wakeup_fire_one:332` defers for busy sessions, active goals and missing routes, then calls `adapter.handle_message` at `:388`. `_post_turn_loop_completion:310` calls `complete_tick`, whose optional `--until` judge invokes `judge_goal` at [hermes_cli/loops.py:561](../hermes_cli/loops.py#L561). This watcher is started by [gateway/run_startup.py:1205](../gateway/run_startup.py#L1205). | Explicitly route or deny `/loop` for managed identities. Cover it separately from cron and heartbeat; persisted loop records are another scheduler. |
| CLI heartbeat, loop and goal hooks | [hermes_cli/cli_loops_mixin.py:355](../hermes_cli/cli_loops_mixin.py#L355) `_start_heartbeat_watchdog` starts a daemon at `:387`, placing due prompts in `_pending_input` at `:382`; `_maybe_fire_loop_tick:389` queues a loop prompt at `:424`; `_maybe_continue_goal_after_turn:490` judges and queues continuation. | Managed CLI/first-builder launcher must not inherit an ungoverned second scheduling loop. Ordinary native CLI behavior can remain outside the managed boundary. |
| Delegated child agents | [tools/delegate_tool.py:105](../tools/delegate_tool.py#L105) `_build_child_agent` constructs a fresh `AIAgent` at `:177`, using inherited runtime/toolsets and native `parent_session_id`. [tools/delegate_tool_child_run.py:632](../tools/delegate_tool_child_run.py#L632) `await_child` submits `child.run_conversation` at `:659`. Model-facing top-level dispatch defaults to background ([tools/delegate_tool.py:581](../tools/delegate_tool.py#L581)), even though direct Python callers retain a synchronous default. Output-schema correction can issue another child turn ([tools/delegate_tool_child_run.py:393](../tools/delegate_tool_child_run.py#L393), call `:411`). | Framework child identity, lineage, purpose/grants, run admission, limits and subtree cancellation must wrap child creation and every continuation. A Hermes session-parent relationship is not an Agent Native ownership boundary. |
| Detached delegation and completion wake | [tools/delegate_tool_dispatch.py:290](../tools/delegate_tool_dispatch.py#L290) `_dispatch_background` detaches children from the parent's interrupt list at `:308`, then runs the batch with `honor_parent_interrupt=False` at `:322`; async registry owns its cancellation. [tools/async_delegation.py:30](../tools/async_delegation.py#L30) has a process-local executor and `:79` a durable completion ledger. [gateway/run_notifications.py:1338](../gateway/run_notifications.py#L1338) drains completions; `:1279` groups/delivers them; `_inject_watch_notification:879` can call `adapter.handle_message` at `:936`. | Subtree stop must reach the async registry and detached children. Completion delivery/replay is an observation; any new turn requires current admission. Durable completion receipts do not mean child execution survives process death. |
| Explicit review | [agent/review_engine.py:151](../agent/review_engine.py#L151) `start_review` calls `delegate_task(background=True, credentials_cfg=...)` at `:164`, potentially using a separate configured model. | Treat as a secondary managed run/delegation with the same admission, budget and cancellation; review text alone does not confer independent authority or acceptance. |
| Automatic memory/skill review and `/refine` | [agent/turn_finalizer.py:605](../agent/turn_finalizer.py#L605) spawns reviews after non-empty, uninterrupted final responses when nudges are due and `skip_background_review` is false. [run_agent.py:734](../run_agent.py#L734) `_spawn_background_review` applies native depth/enabled/defer gates; `:765` `_spawn_background_review_now` creates the thread at `:796`. [agent/background_review.py:841](../agent/background_review.py#L841) creates another `AIAgent` and `:1003` runs it. `load_background_review_settings:187` is enabled by default and fail-open on config errors. `focus`/explicit refine paths differ from automatic gates. Native cron explicitly sets `skip_background_review=True` ([cron/scheduler.py:2259](../cron/scheduler.py#L2259)), but that does not suppress all secondary routes. | Disable this background side effect in managed mode until explicitly admitted, or model it as authorized maintenance with owned memory/skill writes, attribution and cancellation. Test `/refine` as well as automatic nudges; a single automatic toggle is not enough. |
| Deferred background review scheduler | [agent/review_idle_queue.py:110](../agent/review_idle_queue.py#L110) `_ensure_thread` starts an idle queue thread; `_run:141` rechecks native enabled state then calls `_spawn_background_review_now` at `:160`. It can also dispatch aged-out work. [run_agent.py:803](../run_agent.py#L803) may requeue preempted reviews. | Admission must be rechecked at actual dispatch/requeue, not just at initial review request. A paused/retired/revised agent cannot be revived by an old idle queue entry. |
| Curator periodic maintenance and optional model | [gateway/run.py:4429](../gateway/run.py#L4429) `_housekeeping_curator` calls `maybe_run_curator(idle_for_seconds=inf)`; its independent housekeeping schedule registers it at `:4528`. CLI invokes it at [cli.py:3755](../cli.py#L3755). [agent/curator.py:103](../agent/curator.py#L103) defaults maintenance enabled; `:128` defaults LLM consolidation off. `maybe_run_curator:1075` applies native due/idle gates, then `run_curator_review:877` can mutate skill lifecycle state and run a daemon at `:943`. With consolidation enabled/candidates present, `_run_llm_review:1013` creates a skills-only agent at `:1030` and runs it at `:1053`. | Separate deterministic skill lifecycle writes from optional model consolidation. Both need owned-resource policy; only the latter is a model activation. Do not falsely report curator always invokes a model or is disabled by cron configuration. |
| Kanban dispatcher, reviewer lanes and auto-decomposition | [gateway/kanban_watchers.py:185](../gateway/kanban_watchers.py#L185) `_kanban_dispatcher_boot` defaults `dispatch_in_gateway=True` with explicit native env/config/import/lock exits. `_kanban_dispatcher_watcher:234` calls auto-decompose and dispatcher each allowed tick (`:279`). [gateway/kanban_watchers_common.py:87](../gateway/kanban_watchers_common.py#L87) defaults auto-decompose true; [gateway/kanban_watchers_dispatcher.py:237](../gateway/kanban_watchers_dispatcher.py#L237) invokes `decompose_task`; [hermes_cli/kanban_decompose.py:298](../hermes_cli/kanban_decompose.py#L298) calls auxiliary `kanban_decomposer`, through [hermes_cli/kanban_specify.py:146](../hermes_cli/kanban_specify.py#L146) `_call_aux`. [hermes_cli/kanban_db_dispatch.py:1259](../hermes_cli/kanban_db_dispatch.py#L1259) defaults review dispatch true and fail-open on configuration errors; `dispatch_once:1418` considers native lanes, including review at `:1784`. `_default_spawn:2163` launches a detached process at `:2260`; `_worker_argv:2086` runs `hermes -p <profile> --cli --accept-hooks ... chat -q 'work kanban task ...'`, with optional goal mode. | Plane planning must not accidentally feed a competing native execution authority. For managed identities, disable/reject native Kanban activation/decomposition/review until explicitly mapped to framework intents. An embedded-dispatcher toggle alone does not cover direct dispatch or forced standalone daemon. Native emergency pause merely prevents future dispatch while running workers finish ([gateway/kanban_watchers.py:272](../gateway/kanban_watchers.py#L272)), which does not meet immediate subtree stop. |
| Standalone Kanban dispatch | [hermes_cli/kanban_ops.py:85](../hermes_cli/kanban_ops.py#L85) calls `dispatch_once` for explicit dispatch. `_cmd_daemon:154` is deprecated and exits by default, but hidden `--force` still enables the loop; [hermes_cli/kanban_db_dispatch.py:2285](../hermes_cli/kanban_db_dispatch.py#L2285) implements `run_daemon`. | Include explicit/forced native dispatch in the boundary; “deprecated” is not “unreachable.” |
| Startup/reconnect auto-resume | [gateway/run_startup.py:836](../gateway/run_startup.py#L836) `_start_recover_previous_run` restores process checkpoints and marks interrupted sessions resumable (clean-marker handling differs). `_resume_pending_candidates:394` filters flags, reasons and platform; `_resume_owner_authorized:423` checks current native allowlist. `_schedule_resume_pending_sessions:438` checks freshness at `:451–453`, claims a session and schedules a synthetic turn at `:476`; `_run_startup_resume_event:40` calls `adapter.handle_message:47`. Startup invokes scheduling at `:1179`; reconnect also reuses the path. | Reconcile durable framework run state, purpose revision, grants and pause/retirement before resume; a native session allowlist is necessary native authentication, not sufficient lifecycle permission. Separate reply redelivery from starting another model turn. |
| Process-completion and handoff wakes | [gateway/run_startup.py:1184](../gateway/run_startup.py#L1184) restarts recovered process watchers; [gateway/run_notifications.py:1456](../gateway/run_notifications.py#L1456) `_run_process_watcher` queues completion notifications when `notify_on_complete` is set (`:1495`). Some modes only send a status message. [gateway/run_adapters.py:455](../gateway/run_adapters.py#L455) `_handoff_watcher` claims pending CLI handoffs; [gateway/run_startup.py:1409](../gateway/run_startup.py#L1409) `_process_handoff` constructs an internal event and directly invokes `_handle_message:1443`. | Preserve event source and distinguish data-only notifications from model wakes. Handoff, completion and recovered delivery cannot bypass current managed run admission or impersonate a fresh owner instruction. |
| Self-update and deployment/restart | [gateway/slash_commands.py:1199](../gateway/slash_commands.py#L1199) `_handle_update_command` checks allowed platforms, inherited `is_managed()` and a Git checkout, then `_spawn_detached_update:116` launches an updater surviving gateway restart. [hermes_cli/update_contract.py:39](../hermes_cli/update_contract.py#L39) `evaluate_update_admission` checks installation provenance/type, not framework purpose/agent authority. [hermes_cli/update_cmd.py:738](../hermes_cli/update_cmd.py#L738) `_pull_updates` advances code; `_apply_pulled_update:1167` refreshes Python/Node/UI and maintenance then restarts the gateway fleet at `:1217`. [hermes_cli/update_restart_recovery.py:101](../hermes_cli/update_restart_recovery.py#L101) can launch fresh `hermes ... gateway restart`, and `:242` restarts serve units during recovery. | First Builder can propose/build/test framework changes, but managed deployment must remain an explicit host-authorized operation with pinned version/rollout/rollback and run reconciliation. Native self-update cannot be treated as harmless tool maintenance. No evidence was found that an Agent Native deployment boundary is installed. |


## Initial managed-route disposition

For the first controlled Builder proof, use this narrow target. These are work
instructions for the existing delivery items, not toggles installed by this audit.
Ordinary owner-run Hermes outside the managed deployment is a separate context.

| Route family | First controlled-run target |
| --- | --- |
| Existing owner root CRUD | Retain the integrated authenticated, model-free operations. |
| Service-owned embedded `AIAgent` and approved coding/Plane tools | Integrate one admitted run with current identity, purpose, grants, scoped environment and recorded effects. This is the selected engine path. |
| Raw native CLI/one-shot, PTY/TUI profile launch, native API/ACP, console dispatch, preview and side/background prompts | Reject direct managed execution. Later persistent chat calls the service-owned path through AN-28; it must not revive raw launch as an alternate authority. |
| Native cron, heartbeat, goals, `/loop`, Kanban and their catch-up/forced dispatch routes | Reject managed activation during the controlled-run proof. Later framework cadence submits the same durable admission intent; a native timer must not become a second dispatcher. |
| Native children, manual/automatic/deferred reviews, curator mutation/model maintenance, secondary plugin pipelines and completion-driven model wakes | Reject managed use until explicitly integrated. The first handoff may run without children. Data-only notifications remain distinguishable from a new run. |
| Required engine auxiliary calls such as compression | Account for them within admitted model usage, authority and event budgets; reject unbound auxiliary use. Optional background/side consumers stay off for the first proof. |
| Native self-update, profile/permission mutation and release restart | Reject agent-origin administration. Owner-authorized deployment remains separate; source edits cannot change the protected running release. |

Selected integration points require negative coverage too. Calling a lower-level
handler, setting a skip-middleware flag, importing `OWNER`, constructing a fake
`task_id` or invoking an alternate CLI must not acquire managed authority. Keep
host objects, credentials and the control database outside generated code. Pin
and protect the installed engine and approved plugins; a registry hook alone
cannot protect a host process that executes arbitrary Builder-supplied code.

### Auxiliary providers and extensibility

The facade does not see every model request. Besides the side-question and goal
judge routes above, native [context compression](../agent/context_compressor.py),
[micro-compaction](../agent/micro_compaction.py), [title generation](../agent/title_generator.py),
[smart approval](../tools/approval_smart.py), [vision](../tools/vision_tools.py),
[browser vision](../tools/browser_tool_vision.py),
[MCP sampling](../tools/mcp_tool_sampling.py) and
[plugin LLM helpers](../agent/plugin_llm.py) use auxiliary/provider paths.
[Teams pipeline](../plugins/teams_pipeline/pipeline.py) and memory plugins also
make model requests. This is why admitted ownership, budget and recording must
survive component calls as well as whole turns. No conclusion that all installed
plugins, external MCP servers or user hooks are covered follows from static
repository searches; the first installed tool/plugin set must be explicit.

Native liveness/backend heartbeats, notification-only delivery and ordinary
catalog refresh are not automatically model turns. Conversely, model-free
scripts, curator writes and subprocess hooks can still have controlled effects.
Classify by the action and authority, not by whether a model call appears nearby.

## Existing evidence retained

| Evidence | What it establishes | Remaining boundary |
| --- | --- | --- |
| [Identity and authenticated roster](../agent_native/README.md), [web acceptance setup](../web/e2e/README.md) | Persistent inactive roots and owner-only creation/listing through the real API/browser workflow. | No managed creation/activation, chat or dispatcher. |
| [Private provisioning and restricted environment](../agent_native/README.md#private-profile-provisioning), [Builder record](../first-builder/STATE.md) | Protected projections and explicit mounts; existing real-container checks cover the restricted factory and cleanup. | Native terminal/file factories and actual admitted engine are not connected to it. The literal prototype CPU/memory/PID settings are testable existing controls, not approval of AN-70 defaults. |
| [Scoped reads](plane-scoped-reads.md), [writes](plane-scoped-writes.md), [outcome recovery](plane-write-recovery.md) | Host-bound operations, scoped data, durable receipts and GET-only recovery, including isolated live Plane proof. | No model-callable run-derived transport, source freshness gate or managed skill/context assembly. |
| [Storage recovery](plane-recovery-validation.md) | Accepted existing-Builder storage/reconnect and bounded uncertain-write evidence. | Managed-run reconciliation and general provisioning recovery remain separate. |
| [Astra characterization](astra-capability-proof.md) and later [Builder state](../first-builder/STATE.md) | Configured inference and real screenshot reading through Hermes; later one-shot approval guard was fixed and tested. | Edit/save was not proved, nor app-tool parity or an admitted Builder run. The local characterization test is untracked at this snapshot. |

These records remain historical evidence. No test, model call, browser workflow,
container launch or native scheduler was run for AN-17. Existing pass counts are
not new audit test results.

## Delivery handoff and remaining live proof

| Existing Plane work | Concrete audit handoff |
| --- | --- |
| AN-24 — owner/run authority | Start with a failing boundary test for missing or forged actor context, including read access. Derive authority at trusted ingress; caller text, `task_id`, skip flags and nested RPC must not select the actor. Recheck current grants/revisions at effects and deny unsupported child/admin routes. This is the next implementation item. |
| AN-23 / AN-5 — source freshness | Verify and reconcile Plane source changes before admission. Preserve the distinction between owner edits and service comments; Plane notifications are not the immediate Stop transport. |
| AN-70 — configured limits | Obtain the genuinely missing runtime settings before dependent launch. Development WIP and prototype sandbox constants do not settle runtime capacity, model/tool budget or exhaustion behavior. |
| AN-7 / AN-8 — durable admission and purpose | One host-issued run/attempt binds root, purpose revision, existing Plane work and freshness. Reject duplicate/stale triggers before model construction; no unknown actor defaults to owner. |
| AN-26 / AN-4 — tools, skills and planning | Assemble actual approved Builder context and schemas; bind direct and nested tool dispatch to the current run, host-owned Plane credential and restricted environment. No native local/backend fallback. |
| AN-30 / AN-32 — stopping and events | Revoke further actions first, reach engine/container/background children, and independently confirm process death. Persist model, auxiliary-model, tool and control observations; retain stopping/unknown when evidence is incomplete. |
| AN-18 / AN-57 — controlled live run and Builder deployment | Prove the real engine boundary in isolated fixtures, then the protected installed Builder with an explicit repository mount. Test rejected native side paths and source/deployment isolation, not just the happy path. |

AN-18 must show one admitted run with an explicitly configured model account,
persistent agent/work/session/run identity and a real granted tool result. While
work is active, interrupt it and independently inspect the sandbox and owned
background work. Exercise a stale/revoked context, failed or unknown effect and
service restart; paused work stays paused and uncertain effects are not replayed.
Repeat a selected native/auxiliary/nested-tool bypass attempt and show denial
before its effect. Real HTTP/process/storage tests and Playwright for exposed
owner workflows accompany implementation in small red/green increments.

AN-57 then connects the actual repository and approved Builder instructions to a
protected installed release, outside that writable checkout. A browser connection
must not own the run. AN-58/16 still require persistent conversation, a real TDD
improvement, owner steering, restart and a subsequent autonomous step. This audit
does not complete M0's live integration gate or the First Builder handoff.

## Audit verification and refresh

The audit compared all 90 delta entries and before/after Git blobs, verified the
19-commit range and all six dependency/deployment records and 12 notice records.
Relative file and heading links were checked; linked source line references were
checked against unchanged content at the pinned fork revision. Two independent
source reviews covered foreground and background dispatch. Their session-resume,
optional compute-host and shell-RPC additions and reference corrections are
included above. All 24 product and 20 UX coverage mappings remain intact.
`git diff --check` passed. These are documentation/source checks, not runtime tests.
The JSON inventory is reproducible with the following read-only comparison:

```sh
git -c core.fsmonitor=false diff --name-status 006b1beb00d9d25230571d14277aca3d70e5e11f..f7c54d1452418bf63b110c98bdf40e50e002919d
rg -n 'agent_native' --glob '*.py' --glob '!tests/**' --glob '!ops/**' --glob '!scripts/**' --glob '!agent_native/**' .
rg -n 'AIAgent\(|run_conversation\(' cli.py run_agent.py hermes_cli tui_gateway gateway acp_adapter agent tools --glob '*.py'
rg -n 'call_llm\(|handle_function_call|registry.dispatch|_create_environment|ensure_task_env' agent model_tools.py tools plugins --glob '*.py'
```

Refresh the inventory and execution map when changing the pinned engine,
launch/dispatch paths, enabled plugin/tool set or installation layout. A static
map is not an admission test and cannot establish dynamically installed behavior.
