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
  This supersedes the earlier Hermes-only board recommendation. Plane is not yet
  provisioned; repository handoff files are the explicit bootstrap fallback.
