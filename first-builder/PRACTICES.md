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

## Targeted verification by default

The owner requires fast feedback through **individual test cases** during normal
feature work. Run the smallest set that proves the changed behavior; do not turn
each small increment into tens or hundreds of loosely related checks.

- Before a run, select an explicit file and named case(s), including relevant
  parameter variants. A whole file is not automatically focused. Avoid name-only
  filters across the repository, which still discover unrelated files.
- During red-green-refactor, run the new failing case and the directly affected
  regression cases. Keep the real end-to-end boundary when it matters; speed is
  not a reason to replace the required browser/process workflow with unit mocks.
- Expand only for identified impact: callers affected by a shared contract,
  storage migrations, test setup/dependency changes, an unexplained failure, or
  required CI/release coverage. Select the affected cases first. Before a whole
  file, group or suite, briefly state what extra risk it checks. Use judgment;
  necessary broad coverage needs no additional permission and has no fixed count
  limit. Being in the same folder alone is not a reason to run everything.
- After relevant checks pass, move on. Reuse that evidence until another edit,
  failure or unresolved concern invalidates it. A commit, handoff or documentation
  edit is not by itself a reason to rerun previously passing application tests.
- Confirm the intended cases actually ran. Zero selected tests or all-skipped
  output is not verification. Record the selector and result, with the reason
  for broader coverage when used; a large test count is not the goal.

Documentation-only work uses consistency and link checks. Keep required build and
type checks appropriate to the change; run a production build after relevant
frontend changes, not repeatedly while verifying unrelated backend or text edits.
This policy applies to the externally hosted Builder, delegated contributors and
the future framework-hosted Builder.

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

Replace example paths and test names below with the cases for the current change.

| Area | Focused command |
| --- | --- |
| Python unit/integration | `scripts/run_tests.sh tests/path/to/test_file.py -k 'test_name' --file-retries 0`; retain the canonical runner's isolation, never bare pytest. |
| Web unit tests | `npm run test --workspace web -- src/path/to/file.test.ts -t 'case name'`. |
| Agent-native browser acceptance | `npm run test:e2e --workspace web -- feature.spec.ts --grep 'case name' --retries 0`. |
| Desktop browser acceptance, after the required desktop build | `npm exec --workspace apps/desktop -- playwright test e2e/feature.spec.ts --grep 'case name' --retries 0`. |

Python's runner converts node IDs into a leaf-name filter, dropping class and
parameter specificity. Prefer explicit file plus `-k` and check the selected cases.
Use disabled retries for a clear red/green result; investigate failures instead of
accepting a later retry as proof the defect is fixed.

`npm run check --workspace web` includes the whole web unit suite and lint; it is
a broader check, not the default feature loop. A bare browser test command runs
its whole suite. The desktop `test:e2e` wrapper also rebuilds and selects `e2e/`;
reuse a current build and the selected-case command above for iteration.

The framework browser/backend setup is documented in
[web/e2e/README.md](../web/e2e/README.md). Reuse the installed Chromium with the
local executable override when needed; the owner requested no redundant browser
downloads. Desktop tests do not replace framework browser acceptance. Include
`npm run build --workspace web` for frontend changes to verify the production
TypeScript and bundle paths as well as browser behavior.

Choose final verification with the same targeted policy above; finishing an
increment does not automatically require a suite run. An unavailable required
check remains an explicit gap, not a pass.

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
