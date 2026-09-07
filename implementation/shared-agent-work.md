# Shared agent work and outputs

Status: owner-requested plan, 2026-09-07. This planning change implements no
runtime behavior. It is the next refinement within the current usable-agent
milestone; the First Builder handoff remains later. The successful bounded writer
at `9c0bd0b` and live demo/refresh fix at `4164226` remain accepted evidence.

Product authority: [shared work/results](../design/03-projects-and-delegation.md#shared-work-and-results),
[common UX](../design/10-user-experience.md#work-and-results),
[screen contracts](../design/12-control-center-screens.md), and
[writer plus analyst checkpoint](../design/14-first-writer-milestone.md).
This extends those contracts rather than introducing another product specification.

## What changes and what is reused

The current `work_service.py` and `agent/work_policy.py` supply fiction-specific
instructions and a fixed story tool. Completion relies on saved stories. The
API/renderer expose stories, and `story_store.py` assumes Markdown story lineages.
These are current constraints, not general framework requirements.

Reuse Hermes AIAgent/SessionDB, the service-owned worker, native TUI conversation,
protected purpose and operation checks, actual stopping and finite run limits.
Reuse the private publication/content verification machinery and Plane's scoped
operations, freshness checks and uncertain-write journal. Do not create another
agent engine, chat implementation, task board or speculative plugin platform.

Separate common execution instructions from selected domain skills. Common
instructions describe purpose, current plan, available operations, result reporting
and evaluation. A writer's fiction guidance belongs to its purpose/skill context;
a supplied-material analyst receives its own task/skill context. Approved skills
cannot grant new tools. Tool availability follows existing enforceable grants and
supported operations, with explicit missing-capability reporting. Do not silently
expose shell, browsing, spending or delegation to make the example seem general.

Use common result and output records: stable result/output identity, agent,
assignment and attempt, purpose/criteria revisions, format, content or reference,
version, integrity and evaluation references. One result can link multiple outputs;
several results may arise from an assignment. Saved content, unverified external
references and independently observed effects must remain distinguishable.
Plane's artifact-reference operation alone is not proof of a stored output.

Ending an attempt, submitting a result, accepting work and fulfilling a purpose
are separate operations. Valid discovery, an observed plan change, a wait or a
blocker need not produce a file. Provider failure, uncertain effects or exhausted
limits remain explicit; an agent's success claim does not erase them.

The initial shared implementation may still admit only one bounded attempt per
agent. Model that as an explicit current admission restriction, not the definition
of agent identity or lifetime. Multiple activations, cadence and Resume remain
in the existing continuity slice; do not enable them by a schema rename.

## Sequence and evidence

Keep implementation WIP one and the existing cycle undated. Each behavior uses
red/green/refactor, with Playwright for its human workflow and actual worker,
storage and permission checks underneath. Planning does not authorize a new live
model run or change any existing agent's capabilities.

| Order | Work | Completion evidence |
| --- | --- | --- |
| 1 | Generalize bounded work and result/output records. | Writer and analyst get appropriate purpose/skills through the same native boundary. Both can save a Markdown output, with verified version/origin. A plan-only outcome is representable without a story. Pause/limits/unknown effects and source authority remain enforced. |
| 2 | Expose shared Work and Saved outputs in the existing interface. | One create/detail flow uses neutral labels. Show the real plan/current assignment/criteria with Plane links and freshness, output opening and result evaluation. Both domains use the existing safe Markdown reader. Reload/switching agents retain correct output and controls. Unsupported decisions/children are honest unavailable states. |
| 3 | Continue shared conversations, decisions and inspection. | Extend existing work items for native chat/work steering and session/history; use shared result links. A question has one durable identity across Chat, Work and Inbox, with observed response handling and pause preserved. General image/audio viewing and full result acceptance reuse existing capability items. |
| 4 | Continue cadence and later child supervision. | Existing continuity/full-writer acceptance remains required. Later registered children reuse these same views, explicit parent scope, result handoff and escalation; own activity differs from descendant activity. Full recursive teams do not block the first shared root checkpoint. |

Near-term acceptance uses two private purposes: a fantasy writer and an analyst
summarizing supplied fictional operational data with recommendations and stated
limitations. The analyst requires no external research, publication or repository
privilege. Also exercise a plan-only result and legitimate waiting/clarification
without manufacturing files. These examples establish general shared mechanics,
not that every profession or integration is already supported.

Begin with text/Markdown production and preview. The existing media-viewer item
owns image/audio preview and a safe open/download fallback, added with real
producers or imports. No agent-authored executable renderer. Controls advertised
as supported must have a real backend operation; future features are not empty
mock dashboards.

## Plane work mapping

- [AN-78 — Generalize bounded agent work and result records](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/4b7a3d8b-a48d-4e0b-9e01-0645a126cffd/) is the next urgent item; it depends on the accepted first-story checkpoint.
- [AN-79 — Show shared Work and Saved outputs for every agent](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/d4143b70-112e-421d-ad5a-288dfc92b48c/) follows the shared records and exposes their common human workflow.
- AN-73 continues native conversations, decisions and steering; AN-74 owns deeper session/activity/output inspection. Their existing records are generalized, not copied.
- AN-75/76 retain continuity and full owner-journey acceptance; the analyst is an added bounded generality proof.
- AN-6/26/48 retain broader planning, skills and media/review scope. AN-37–45 retain actual child creation, delegation, escalation, recursive monitoring and global Inbox. Narrow subset evidence links back to them.

Current cycle: **03 — Shared agent work and the fantasy writer**, with no planned
dates. Both new items are Todo; planning has not started runtime implementation.
The original writer milestone/module remains the acceptance home. The new items
also link into the existing governed-work and control-center capability modules.

## Existing work and data

The current story demo stays readable. At implementation time, introduce an
explicit local schema migration mapping its immutable content, versions, origin,
Plane links and evaluations into the shared model, with verification before
switching readers. Do not delete records, rerun generation or overwrite evidence.
No old-prototype compatibility layer is required; this preserves current accepted
user data. The migration itself is part of the first implementation slice, not
performed by this plan.

The first story checkpoint stays Done. Broader native-chat ordering remains
owner-deferred. Existing conversation/inspection items adopt shared terminology;
child creation/delegation/escalation and global Inbox keep their original scope
and IDs. Narrow subset evidence links back to broad capability records without
claiming those records complete. See the [coverage index](plane-roadmap-coverage.md)
and live Plane for work IDs, priorities and dependencies.
