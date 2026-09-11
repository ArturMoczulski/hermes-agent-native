# First Builder workspace

This repository is the implementation home and working space of the agent-native
First Builder. Before substantive work, read `first-builder/INSTRUCTIONS.md`;
it routes to the First Builder soul, practices, memory, and current state. Also
read the applicable area-specific `AGENTS.md` before editing code in that area.

## Operating contract

- Treat the latest human request as the source of task scope and authority.
- Plane is the only source for long-term planning, current work, next priorities,
  cycles and milestones. Run `.venv/bin/python first-builder/tools/plane_status.py
  summary` (or `/plane`) on resume.
- Preserve existing user changes. Inspect `git status --short` before editing.
- Use small red-green-refactor increments for behavior changes. Write and run a
  focused failing test before the minimum implementation, then verify the real
  boundary and record evidence.
- Prefer Playwright for user-visible workflows and the repository's canonical
  `scripts/run_tests.sh` for Python tests; do not claim checks that were not run.
- Keep the core narrow, preserve prompt caching and message-flow invariants, and
  prefer extending existing surfaces over adding speculative infrastructure.
- Do not expose secrets or private runtime state in the repository. Do not widen
  permissions, deploy, contact third parties, or spend money without explicit
  authorization.
- Update `first-builder/STATE.md` with the active behavior, evidence, blockers,
  and next step before handing work back.

## Tool and command discipline

Use `rg`/`rg --files` for repository search. Use `apply_patch` for manual file
edits. Never use destructive git commands unless the human explicitly requests
them. Follow the nearest area-specific instructions when they are more specific.
