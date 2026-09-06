# First Builder — development practices

These are the working conventions for developing agent-native. Improve details
as evidence warrants, but do not weaken the owner's rules in [SOUL.md](SOUL.md).
Use the existing Hermes tooling and relevant area instructions where compatible
with the human's requirements and this framework's specification.

## Required test-driven development loop

1. **Choose one behavior.** Identify its observable outcome and acceptance criteria.
   Keep the slice small enough to complete and verify before starting another.
2. **Write the test first.** For a user-facing workflow, begin with a focused
   Playwright end-to-end acceptance test. Add unit tests for the domain rules and
   edge cases, and integration tests for service/storage/process boundaries.
3. **Observe red.** Run the relevant new test and confirm it fails because the
   intended behavior is absent or incorrect. A missing dependency, broken fixture,
   or unavailable server is a setup problem, not a valid red result.
4. **Implement the minimum.** Change only what is needed for this behavior. Run
   the targeted tests during development, rather than building adjacent features.
5. **Observe green.** Re-run the acceptance test and affected unit/integration
   checks. For a browser workflow, unit tests alone do not finish the increment.
6. **Refactor and recheck.** Improve structure while preserving behavior; run the
   affected checks again. Record evidence, commit when appropriate, and repeat.

Use this cycle inside every milestone. If a complete workflow requires several
small changes, keep the acceptance test as the target and use smaller failing
tests to drive each step. Do not mark the workflow complete until it passes.

For internal behavior with no browser surface, start with a unit or integration
test at the real boundary. Add Playwright coverage when that behavior enters a
user workflow; do not invent a UI solely to test an internal function. A pure
refactor uses existing behavioral tests as its baseline. Documentation-only edits
need consistency and link checks, not artificial runtime tests.

## Playwright as the primary product-level verification

- Exercise the actual application in a browser against its real backend and
  isolated storage. Cover the user's interaction and the resulting persistent
  state, not just whether a page rendered.
- Cover complete relevant flows: creating an agent, starting work, asking and
  answering a question, observing progress, accepting results, and stopping work.
  Add each flow alongside its implementation, not as a later testing project.
- Keep our UI, API, authorization, scheduling, and database real. Replace external
  paid/model services at their boundary with controlled responses when needed for
  repeatability. Do not mock away the agent-native behavior being verified.
- Use isolated test workspaces, credentials, databases and service processes.
  Clean them up. Do not point tests at personal profiles or production accounts.
- Prefer observable state and readiness checks over arbitrary sleeps. Capture
  failure traces and useful logs; investigate flaky results rather than hiding
  them with retries or weaker assertions.
- Pair browser assertions with real process/container checks for cancellation
  and recovery. A UI label saying "stopped" does not establish that work stopped.

Model-driven evaluations supplement deterministic end-to-end tests where agent
judgment matters. A scripted model response proves integration behavior, not
independent planning ability; record that distinction in completion evidence.

## Unit and integration coverage

Keep unit tests focused on behavior and invariants: authority, soul ownership,
parentage, lifecycle transitions, decision applicability, and work acceptance.
Exercise real persistence, worker boundaries, restart and cancellation in
integration tests where an isolated unit cannot establish the requirement.

Fix regressions by reproducing the defect with a failing test first. Do not freeze
incidental implementation details, assert on source text, or substitute mocks for
the boundary whose correctness is in question. Maintain relevant existing tests.

## Test commands and initial setup

Use the repository's existing commands and inspect package scripts before adding
new ones. Current entry points, relative to the repository root:

| Area | Existing command |
| --- | --- |
| Python unit/integration tests | `scripts/run_tests.sh tests/path/to/test_file.py` (replace the example path); do not invoke bare pytest. |
| Web unit tests | `npm run test --workspace web -- <test-file>` (replace the example path). |
| Web type checks, unit tests and lint | `npm run check --workspace web`. |
| Agent-native browser acceptance | `npm run test:e2e --workspace web` (real isolated backend and installed Chromium; see setup below). |
| Existing desktop Playwright tests | `npm run test:e2e --workspace apps/desktop` (builds and runs the existing desktop suite). |

The framework browser/backend setup is documented in
[web/e2e/README.md](../web/e2e/README.md). Reuse the installed Chromium with the
local executable override when needed; the owner requested no redundant browser
downloads. Desktop tests do not replace framework browser acceptance. Include
`npm run build --workspace web` for frontend changes to verify the production
TypeScript and bundle paths as well as browser behavior.

Run focused tests during each loop and affected regression checks before declaring
the increment complete. Broaden verification for cross-cutting changes and release
gates; do not run the entire upstream suite after every tiny edit. An unavailable
required check remains an explicit gap, not a pass.

## Continuous work and completion

Keep one active behavior clearly identified in [STATE.md](STATE.md). Record the
test that drove it, the meaningful red result, the passing checks and any remaining
gap. Update implementation progress only when its completion evidence exists.
Preserve unrelated work and use small coherent commits; follow the human's scope
when they request only a review, file copy, or documentation change.

Continue the next authorized step without requiring the owner to issue another
prompt for every increment. Ask when blocked on a real decision or permission,
and record the blocker. Keep reports brief and factual. Never claim tests, runtime
integration, background work, or deployment that has not actually happened.

## Planning and sprint delivery

Apply the [Plane project-management skill](../skills/productivity/plane-project-management/SKILL.md)
to most substantive work. Organize small verified increments into ordered cycles
with a goal, scoped items, dependencies, accepted exit criteria/evidence and a WIP
limit. Advance when the outcome is accepted or explicitly re-scope with a reason
and a disposition for unfinished work. Never wait for a calendar boundary to
continue, test or deliver.

Use native Plane cycles without planned start/end dates. Do not add cycle date
ranges, duration estimates in days or weeks, or placeholder dates. Retain actual
activity timestamps and thinking cadence. Record genuine externally required deadlines separately on affected work
with their source; they are constraints, not cycle estimates.

Link work items to commits, red/green evidence and evaluations. Once Plane is
connected, PLAN.md is a roadmap and STATE.md a handoff pointing to authoritative
Plane IDs, not duplicate boards.
