# First Builder — memory

Stable decisions and useful lessons belong here. This is editable memory, not
authority to change the soul, product requirements, or permissions.

## Owner decisions

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
  account through Plane's API. PLAN.md is now a pointer, not a duplicate backlog.

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
