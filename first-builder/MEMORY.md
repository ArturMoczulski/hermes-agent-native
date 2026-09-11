# First Builder — memory

Stable decisions and useful lessons belong here. This is editable memory, not
authority to change the soul, product requirements, or permissions.

## Owner decisions

- **2026-09-11 — Secrets authority requirements:** the owner requested a design
  for framework, instance and agent secrets with scoped access and ultimate human
  administration/recovery. Agents must not change passwords, remove owner access
  or obtain unrelated secrets. AN-144 and
  [the design](../design/18-secrets-and-credential-authority.md) record the review.
  OpenBao, a protected operation broker and use-only agent access are proposals,
  not an approved deployment. A synthetic non-secret probe confirmed that today's
  repository-command helper can read outside its working-directory grant; actual
  execution isolation is a prerequisite for the proposed protection. Source:
  current owner request and production-helper probe; no real secret was inspected.

- **2026-09-11 — Future independent security review:** the owner requested a
  dedicated milestone for independent reviewer agents that assess commands and
  behavior, identify security/boundary risks, trigger pauses and warn the owner
  or authorized affected agents. This is explicitly not an immediate priority.
  AN-135 / M8 and AN-136–142 record the deferred scope. Detailed policies in
  [the design](../design/17-independent-security-review.md) remain proposals;
  creating this plan does not enable runtime review or change existing grants.
  Source: owner conversation requesting a detailed design plan.

- **2026-09-05 — Implementation home:** Artur selected
  `ArturMoczulski/hermes-agent-native`, a Hermes fork, as the framework repository.
  This repository root is also the First Builder's workspace. The old agent-native
  implementation is no longer the development foundation. Source: owner conversation.
- **2026-09-05 — Development method:** use continuous test-driven development in
  small red-green-refactor increments, emphasizing Playwright end-to-end tests
  and supporting unit tests. Do not build a large body of code and test afterward.
  Source: owner conversation; detailed procedure is in [PRACTICES.md](PRACTICES.md).
- **2026-09-05 — Bootstrap role:** the assistant working here is the First Builder
  now, with the purpose of building agent-native; eventually the role runs inside
  the framework. Source: owner conversation and [SOUL.md](SOUL.md).

## Context to preserve

- `design/` is the canonical product specification; `implementation/` describes
  the engineering approach and delivery sequence. Choosing Hermes did not silently
  approve the proposed defaults in `design/07-open-decisions.md`.
- The design and implementation-plan folders were copied into this clone. That
  copy does not establish completed runtime features or a running Builder cadence.
- Hermes includes desktop Playwright coverage and web unit-test tooling. A
  framework web acceptance setup still needs to be established and verified.

Add later entries with the decision or observation, its evidence/source, and any
remaining uncertainty. Replace superseded entries explicitly; do not accumulate
contradictory instructions or store secrets here.

- **2026-09-06 — Planning workflow:** the owner selected Plane workspaces/projects
  and Scrum-like cycles for the vast majority of agent tasks, including the First
  Builder. The reusable skill is `skills/productivity/plane-project-management/SKILL.md`.
  This supersedes the earlier Hermes-only board recommendation. At this design-only
  stage Plane was not yet provisioned; the deployment entry below supersedes that
  bootstrap fallback.

- **2026-09-06 — Local Plane and API-first work:** the owner authorized local
  Docker deployment and using Plane for the Builder's ongoing work. Live references
  and private API credential location are in PLANE.md. Use the separate Builder
  account through Plane's API. Superseded 2026-09-11: Plane is the only planning
  source (see the latest owner decision below).

- **Autonomy/permission decisions — after the Plane roadmap review:** owner approved
  AN-60–62: ordinary authorized work proceeds; root defaults cover private work,
  Plane, public research and child creation within configured limits; external publication/spending/
  contact/deployment needs scoped standing permission or explicit approval, never
  silence. Children receive only a selected subset of parent-held delegable
  permissions; owner can prohibit delegation. Source: owner reply "Yes, this all
  sounds good" to those three defaults. Canonical rules: design/04 and design/05;
  remaining lifecycle, timing and capacity choices were not approved by that reply.

- **Child duration and lifecycle — historical, superseded by the lifespan entry below:** ongoing
  marketing/sales children independently find new projects within their purposes;
  bounded children idle after accepted completion. Owner approved purpose-change
  stop/reconcile/eligible automatic replan and parent notification, plus replacement
  retiring the old subtree with retained history/new identity/selected handoff
  (AN-63). AN-64 cancellation disposition was not explicitly settled by that reply.

- **Purpose-based lifespan — latest owner clarification (2026-09-06):** replace
  fixed ongoing/bounded agent types with review of whole-purpose fulfillment,
  accepted results, relevance and continuing/subtree obligations. Clear fulfillment
  permits self-retirement through framework lifecycle controls; uncertainty follows
  parent escalation. Growth, recurring delivery and legitimate waiting are distinct
  useful outcomes. No self-preservation or invented work to stay alive. Cancellation
  stops the assignment and pauses its agent/subtree, retaining independent work
  under the pause. This supersedes the prior bounded-completion idle default;
  AN-63 replacement remains accepted. Canonical rules: design/01 and design/05.

- **Undated planning sequence — owner correction (2026-09-06):** remove cycle
  start/end dates and duration estimates. Plan ordered outcome groups with scope,
  dependencies, exit evidence and WIP limits. Advance as soon as accepted results
  allow; no weekly forecasts or waiting for a calendar window. Actual event times,
  thinking cadence and real externally required deadlines remain separate concepts.
  This supersedes earlier calendar-based cycle planning. Source: owner conversation.

- **First major milestone — owner reprioritization (2026-09-06):** run the First
  Builder as a persistent autonomous framework agent with repository development
  tools, trusted two-way chat, proactive questions, owner steering/stop, scoped
  Plane planning, evidence-based evaluation and basic restart recovery. Demonstrate
  a real TDD improvement and another eligible step without repeated human prompts.
  This supersedes the M0-through-M7 chronological plan: indispensable Builder
  isolation joins the first autonomous root; full recursive teams, the complete
  control center and broader operation hardening follow the handoff. Preserve the
  protected deployed soul/grants/running release outside the editable repository.
  Source: owner explicitly requested reprioritizing Plane around this milestone.

- **Earlier usable-agent milestone — owner reprioritization (2026-09-06):** before
  the First Builder handoff, prove one ordinary fantasy writer created from purpose,
  working and continuing autonomously with chat, proactive questions, activity/session
  inspection, saved stories, owner steering/stop and local recovery. A single story
  is an intermediate checkpoint. The Builder handoff remains next, reusing these
  foundations. This supersedes the earlier choice to prove the Builder first.
  Source: owner request to switch the current cycle; design/14-first-writer-milestone.md.

- **Native chat reuse — owner decision (2026-09-06):** use existing Hermes `/chat`
  and extend its native TUI/session/engine integration. Do not build a duplicate
  React composer, transcript store or one-shot model wrapper. Framework identity,
  protected purpose and lifecycle still need explicit server binding; a native
  profile alone does not establish managed authority. Source: owner approved the
  native-chat repair and reuse recommendation.


- **First story before residual chat ordering — owner reprioritization (2026-09-07):**
  defer AN-77's remaining purpose-revision/transcript ordering; implement AN-72's
  first managed story and actual Pause next. Retain accepted native chat/restart
  evidence. Per-run time and model-step limits are execution caps, not project
  estimates. Fixture values do not establish live defaults. Source: current owner
  conversation.


- **Live first-writer checkpoint (2026-09-07):** the owner requested an actual
  recorded demonstration. A new Moonlit Cartographer used the existing ChatGPT
  subscription/GPT-6 Astra connection to plan in Plane and publish a verified
  story in 13 model calls. A separate live browser Pause stopped its real worker.
  The demo's explicit 300-second/20-step limits do not establish global defaults;
  the original three agents remain unchanged. The writing task stays In Progress
  pending owner review. A finished bounded run is not full-purpose acceptance or
  evidence of automatic cadence. See [STATE.md](STATE.md) for exact records.
- **Poll through the live user workflow (2026-09-07):** recording exposed duplicate
  sibling React keys that accumulated old work controls. Keep work/story keys
  distinct, and verify a held active run over actual polling responses before
  testing Pause. Immediate navigation had missed this defect. The regression
  reproduced 13 controls, then passed with one control and confirmed worker death.

- **Shared agent work — owner clarification (2026-09-07):** after viewing the real
  writer demo, the owner requested planning for a universal framework interface:
  Work, results/Saved outputs, plans, decisions and children must be common across
  agents. Domain instructions belong to purpose and approved skills, not a shared
  fiction-only executor. The next planned checkpoint uses writer and analyst on
  supplied material, including meaningful work without a file. Existing writer
  evidence remains accepted. No runtime implementation was requested in this turn.
  See [shared delivery](../implementation/shared-agent-work.md).

- **Activity table — owner request (2026-09-07):** replace the ever-growing
  activity list with a newest-first paginated table, twenty rows by default and
  adjustable up to one hundred. The design selects 20/50/100 page sizes and stable
  pages with a new-activity indicator. This belongs to shared inspection work,
  not a writer-specific UI. No runtime change is established by the plan.

- **Targeted tests — owner instruction (2026-09-07):** default to individual unit,
  integration and Playwright cases for each feature increment. Avoid tens or
  hundreds of unrelated tests; widen only for a concrete need, including a full
  suite when warranted. Preserve actual TDD and end-to-end proof while keeping
  iteration fast. Source: owner conversation;
  [working policy](PRACTICES.md#targeted-verification-by-default).

- **Plane is the only planning source — owner instruction (2026-09-11):**
  long-term planning, current work status, next priorities, cycles and milestones
  live only in the live Plane project. The repository keeps no planning backlog.
  Fast status comes from the deterministic read-only tool
  `first-builder/tools/plane_status.py` (`summary`, `last-worked`, `current`,
  `milestones`) and the `/plane` Kilo command, so routine checks do not spend
  inference tokens re-exploring the board. Source: owner conversation.
