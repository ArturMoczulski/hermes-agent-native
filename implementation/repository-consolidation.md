# Consolidate the two project directories

Status: proposed execution plan, 2026-09-11. Planning is authorized; this document
neither performs nor authorizes the filesystem cutover. Owner review selects the
repository arrangement before execution. No directory, remote or agent grant has
been changed as part of writing this plan.

## 1. Recommended outcome

Use one active source checkout:

```text
/Users/arturmoczulski/Projects/agent-native/
    .git/                       # today's Hermes fork history and main branch
    AGENTS.md                   # today's fork contributor instructions
    first-builder/              # soul, practices, memory, handoff and Plane context
    design/                     # current product specification
    implementation/             # implementation plans and evidence
    agent_native/               # framework control code
    agent/, hermes_cli/, ...     # Hermes runtime and our integration
    web/, ui-tui/, apps/         # existing frontend and chat implementation
    ops/                        # Plane and dashboard operations
    tests/, scripts/, skills/   # existing development infrastructure
```

Keep the existing remote `git@github.com:ArturMoczulski/hermes-agent-native.git`
and its `main` branch. A local directory name does not have to match a GitHub
repository name. Do not rename GitHub repositories, force-push, erase branches,
merge the abandoned implementation, or perform a dependency upgrade as part of
this cleanup. Preserve the fork's upstream ancestry and license notices.

The old checkout does not need to remain as a maintained project or permanent
archive. It must not remain a second active source tree in the normal Projects
location. A temporary private preservation copy may be kept only until the
cutover and verification checkpoints pass; after the owner is satisfied, it may
be removed. Do not place obsolete AGENTS.md files under the active source path
where they could become contributor instructions.

Runtime data remains outside the source checkout. One project directory means
one authoritative place to develop the framework, not putting every database,
credential and agent's project under the First Builder's writable repository.
This follows [workspace boundaries](../design/04-workspaces-and-skills.md) and
[First Builder authority](../design/08-first-builder.md).

## 2. What exists today

These are observations, not immutable preconditions; recheck them at cutover.

| Location | Observed state | Disposition |
| --- | --- | --- |
| `Projects/agent-native` | Old independent Git checkout; `docs/gpt6-design-review` at `cd6d7f6`; origin `ArturMoczulski/agent-native` | Vacate the desired final path; retaining a temporary rollback copy is optional |
| `Projects/hermes-agent-native` | Current implementation; `main` at `50279f0`, with uncommitted work | This checkout and its Git identity become the final `agent-native` directory |
| `~/.hermes-agent-native-preview` | Live profile, databases, credentials, protected runtime/instructions, agent state, outputs and logs | Preserve in place |
| `~/.hermes-agent-native` | Earlier separate profile | Leave alone; do not merge credentials or state |
| `~/.local/share/agent-native/plane` | Private Plane deployment configuration and API credentials | Preserve in place, outside Git |
| Docker project `agent-native-plane` | Plane services and named storage volumes | Keep project name, data and port 19230 |
| `Projects/fantasy-game-builder` | An agent's separately authorized output/source workspace | Preserve in place; it is not duplicate framework code |
| Codex saved project `agent-native` | Points to `Projects/agent-native` | Retain desired path; refresh project/repository context after replacement |

The old checkout has a modified PLAN.md and untracked browser/demo artifacts.
Its PLAN.md contains a later adaptive-model-selection note worth reconciling.
Its remote main also has history not represented by the checked-out branch:
an earlier remote inspection returned `f67ddd5205d1344b5745dfa28946aa44bc9e5cb1`.
Inspect and preserve that history; do not assume the local old branch contains
all work worth keeping or that it is safe to discard the remote.

The current fork has uncommitted AN-132 code, tests and documentation, plus
pre-existing changes to AGENTS.md, README.md and a tool test. Preserve each.
PLAN.md currently overstates AN-132 completion: browser verification is unfinished
and these changes are not in the inspected main commit. Reconcile that evidence
before migration; moving files must not turn incomplete work into accepted work.

## 3. Submodule alternative and why it is not recommended now

A valid alternative would keep the original Agent Native Git repository as a
thin parent and put our fork at `runtime/hermes/` as a pinned submodule:

```text
agent-native/                   # parent repository
    AGENTS.md, design/, ops/     # deliberate parent-owned files
    runtime/hermes/              # our customized fork, separate .git identity
```

This provides one top-level filesystem location but still two repositories.
It is useful when a parent application has its own meaningful implementation or
release lifecycle and consumes Hermes through a defined interface.

Today our framework changes span the fork's runtime, managed tools, dashboard,
chat, tests and skills. There is no independent parent application to compose.
A submodule would therefore nest nearly the entire product instead of separating
a reusable runtime from a separate framework application.

| Consideration | Fork directly at project root | Fork as submodule |
| --- | --- | --- |
| Ordinary framework change | One commit/push workflow | Fork commit/push, then parent gitlink commit/push |
| Clean clone | Standard clone/setup | Recursive clone/setup and pinned submodule verification |
| Atomic code/docs change | One commit if both live in fork | Cross-repository coordination if docs live in parent |
| First Builder workspace | Matches current root-based design | Must define parent versus nested repository tools and authority |
| Upstream Hermes merges | Resolve fork modifications | Same fork modifications still need resolution |
| Runtime security isolation | Enforced separately by runtime | A submodule supplies no execution isolation |
| Fit for current code | Direct | Adds management work without an established boundary |

If the owner selects the submodule option instead, change this plan before
cutover: remove obsolete parent source, explicitly assign canonical docs to one
repository, pin the fork's published commit, define CI/recursive checkout rules,
start/test commands and cross-repository release order. Test detached submodule
checkouts and missing initialization. Update First Builder's root assumptions
through an owner-authorized grant change, not an implicit wider grant. Do not
keep duplicate active specs or a permanent parent/submodule copy synchronization.

A Git subtree/vendor import is another possibility, but would add an upstream
synchronization mechanism we do not currently need. It is outside this migration.

## 4. Invariants throughout the migration

- No lost commits, staged/unstaged changes, untracked work or private artifacts
  during the cutover; long-term preservation of the old checkout is optional.
- No secrets, API keys, model weights or runtime databases enter Git.
- Preserve agent IDs, purposes, memory, output versions, decisions and Plane links.
- Preserve manual pauses, disabled cadence, unanswered questions and review gates.
- Preserve uncertain-effect records; never replay mutations just to clear a gate.
- First Builder remains held for the owner's final test. Keep its configured
  OpenAI GPT-5.6 Sol with Low reasoning; migration is not launch authorization.
- No concurrent old and new dashboard/dispatcher instances on the same profile.
- No source/history rewrite to make directory names appear uniform.
- No permanent symlink workaround. Repository guards reject symlink roots, and
  old-path aliases would hide unresolved dependencies instead of fixing them.

## 5. Execution sequence and checkpoints

### Step A — Establish the exact source of truth

Read both repositories' current status, remotes, branches, worktrees and HEADs.
Inspect remote refs without rewriting them. Fetch missing history into the
private preservation copy if required, then compare ancestry and unique commits.
Classify old-only material as relevant requirement, historical documentation,
private artifact, obsolete source, or unresolved work.

Use current fork design/implementation chapters as the active specification.
Do not overwrite them with older chapters simply because filenames match.
If a historical document is useful in active docs, import only that document with
explicit historical status and repaired links; do not import obsolete contributor
instructions. Any temporary old-checkout copy is optional and may be discarded
after verification.

Record exact before/after paths, commits, dirty-file checksums, remote refs,
profile locations, project grants, ports and process commands in a private
migration manifest. Keep credentials and sensitive file contents out of reports.

Exit: a reviewed inventory explains every source of data and every intended move.

### Step B — Checkpoint unfinished development

Stop editing feature code during migration. Either complete and verify a coherent
AN-132 slice first, or leave it explicitly unfinished and preserve it in the
private snapshot. Do not force an arbitrary WIP commit into main or combine
unrelated changes with migration commits.

Preserve the index separately from the working tree, including untracked and
ignored valuable files. A Git bundle alone does not preserve these. Exclude
regenerable caches only after classifying them; an ignored directory can contain
valuable runtime or demo data. Record interrupted checks accurately in Plane.

Exit: a separate restoration copy can reconstruct each checkout's commits,
index and working files without relying on the future moved directory.

### Step C — Prepare and verify backups

Choose a private, owner-controlled backup location outside both checkouts,
with available disk space and restrictive permissions. Record its actual path;
do not assume a placeholder path exists. Create Git bundles of all preserved
refs and verify them. Preserve local-only remote-tracking refs and any separately
fetched old remote history. Snapshot source worktrees and valuable ignored data.

For the live profile, stop its writers before a consistent full snapshot, or use
supported database backup mechanisms with coordinated filesystem snapshots.
Never copy only an open SQLite .db file while ignoring WAL/related files. Include
all relevant databases, protected deployments, agent homes, outputs, configuration
and private authentication material in a restricted backup. Record hashes of
immutable outputs and protected files for comparison.

Plane data will not move. Before cutover, have a verified PostgreSQL and upload
backup/restore procedure; if making fresh backups use the existing
[Plane operations](../ops/plane/README.md). Record Docker volume names and compose
project identity. Do not run `down -v`, prune volumes, reset users or rotate keys.
Plane serves other projects, so avoid unnecessary downtime for them.

Exit: verified source backups and consistent runtime recovery points exist.

### Step D — Enter controlled maintenance

Record existing per-agent cadence settings, owner pauses, current work, pending
questions/reviews and First Builder's launch hold. Stop new work admission before
stopping workers. Use supported graceful service stop/drain paths and verify actual
process exit; a UI label alone is insufficient. Include dashboard, chat/compute
hosts, gateway, dispatcher and running project commands tied to this installation.

Do not implement maintenance by permanently changing every agent's owner pause
state. If the current host lacks a safe admission/drain operation, implement and
test that small prerequisite with isolated storage before live cutover. Preserve
interrupted work and unknown external effects for reconciliation on restart.

Exit: one consistent backup boundary and no old processes writing during moves.

### Step E — Move the checkouts

Execute from a stable directory outside both checkouts. Verify destination paths
are absent and canonical parents are correct; do not overwrite a populated folder.

1. Move the old `Projects/agent-native` into a temporary private preservation
   location.
2. Move `Projects/hermes-agent-native` to `Projects/agent-native`.
3. Verify the new root retains the fork's .git, HEAD, remotes, index and worktree.
4. Verify the old checkout is either in the temporary preservation location or
   has been intentionally removed after its backups were verified.

Prefer same-filesystem renames for live cutover; each rename is atomic but the
pair is not. Record completion of each step so failure between them is recoverable.
Do not delete either directory, initialize a replacement Git repository, or copy
one repository over another. Keep the separate verified backup even if a rename
succeeds. No source subdirectories are reorganized in this step.

Exit: one active checkout at the desired path, with unchanged source identity.

### Step F — Repair paths and development setup

Audit only operational references: service commands, editor tasks, scripts,
editable installations, shebangs, project bindings and First Builder metadata.
Do not globally replace the string `hermes-agent-native`: the remote name and
runtime profile name remain valid, and historical evidence should remain intact.

Recreate the Python virtual environment at the new path using the existing
Python version and pinned project dependency mechanism. Its current executable
shebangs and editable package mappings embed the old checkout path; renaming the
folder alone does not repair them. Preserve the previous environment in the
backup, reuse caches and avoid an unrelated version upgrade. Verify imports and
the `hermes` executable resolve to the new checkout.

Check Node workspace links and native modules; rebuild/reinstall only where
needed. Retain Node 24.19.0 or another already verified compatible runtime.
The system Node 24.3.0 does not satisfy this checkout's engines. Verify the real
TUI entry point/build rather than assuming a web build also prepares chat.
Reuse the installed Playwright browser; do not download it again.

Refresh the saved Codex project's repository state at the same `agent-native`
path. Reload contributor instructions and terminate old-directory terminals so
future commands cannot accidentally operate in an archived checkout. Verify no
active IDE/task continues writing the old location.

Exit: CLI, imports, tests and build tooling identify the new root consistently.

### Step F2 — Consolidate contributor instructions and prompt loading

The current external contributor conversation is configured against the old
`Projects/agent-native` directory and receives its old AGENTS.md. That is an
active instruction-loading dependency even though running Hermes services use
the fork. Treat correcting it as required migration work, not optional cleanup.

1. Inventory the old root AGENTS.md, CONVENTIONS.md, `.agents/builder/` prototype,
   `.kilo/` profile and any editor-specific prompt configuration. Compare them
   with the current fork's instructions and identify genuinely unique, still-valid
   owner requirements. Do not copy historical files into the active tree; do not
   copy stale authority or abandoned implementation choices into active prompts.
2. Keep the current fork's root AGENTS.md as the contributor entry point at the
   final path. Its links must resolve to `first-builder/INSTRUCTIONS.md`, SOUL.md,
   PRACTICES.md, MEMORY.md, STATE.md, PLANE.md, the current specification and skills.
   The inherited generic root SOUL.md is not the First Builder's soul; keep the
   explicit First Builder selection. Do not independently rewrite owner-controlled
   soul content as part of a path cleanup.
3. Refresh/reopen the saved coding workspace after cutover using supported app
   controls, and explicitly read the new root instructions before continuing.
   Existing conversation context can retain old instructions: replacing a file
   does not retroactively remove them. Use a fresh session if necessary, with a
   concise handoff of current work, owner decisions and unfinished verification.
   Verify the configured cwd, Git identity and loaded entry point agree.
4. Separately verify framework-hosted instruction provenance: retain deployed
   protected soul/instruction copies and runtime authority outside the writable
   repository. A source-directory move must not silently replace the running
   agent's prompts, expose them for self-editing or launch the held First Builder.
5. Check active startup/editor configuration for references to archived instruction
   paths. Remove or correct operational references, while preserving historical
   mentions as history. Record which instructions the contributor loads and which
   protected instructions the hosted Builder uses.

Exit: the external contributor loads the current fork's instructions from the
final project root; no old prototype profile is active; hosted protected prompts
and the First Builder launch hold remain intact. Recovery from verified backups
remains possible.


### Step G — Rebind the First Builder without broadening authority

The prepared First Builder is
`254b3be7-f672-4a8b-8e5e-c1d15cef74c0`. Its registered repository currently points
to `Projects/hermes-agent-native`; protected instructions and runtime releases
live outside that checkout in the preview profile.

Inspect the current supported provisioning/migration API. Existing preparation
rejects a different repository path, so simply preparing it again is not an
adequate migration. If necessary, implement a narrowly scoped owner-operated
repository relocation command first, driven by tests against temporary profiles.
It must validate expected old path, identity, destination and stopped state;
change only the approved binding; preserve IDs, protected hashes, model,
permissions and launch hold; record an audit result; and be idempotent and
transactional. Test wrong identity/path, active execution and partial failure.
Do not use an ad-hoc broad database rewrite or let the Builder approve its own
new authority. If protected deployment metadata also needs relocation, include
that exact field in the reviewed migration rather than silently re-provisioning.

Historical session cwd strings and output evidence may legitimately retain old
paths. Distinguish history from active resume metadata. Correct the latter through
a supported migration if necessary; do not rewrite transcripts or signed/hash-
checked outputs. The Fantasy Game Builder's separate project grant stays intact.

Exit: same prepared Builder, correct new repository, still held for owner testing.

### Step H — Restore a reliable development service

Today's recovered setup is Vite on `127.0.0.1:19221` and the Hermes backend on
`127.0.0.1:19222`, using `~/.hermes-agent-native-preview`. Keep those external
addresses stable, including `dashboard.public_url`. Preserve authenticated API
and WebSocket forwarding and all required output/media/preview routes.

Document one start/status/stop procedure using the consolidated root. Prefer
standard macOS supervision for the development services, with explicit stop,
retained exit logs, health checks and bounded restart behavior. Reuse suitable
existing lifecycle tooling instead of inventing another runtime orchestrator.
Keep production/Linux packaging as separate work. AN-15 records the observed
outage and the missing durable dashboard/frontend recovery proof.

Start exactly one instance of each required service and reconcile interrupted
work before admitting new work. Restore original eligibility and owner controls;
do not bulk-enable agents. Keep the First Builder's final-test hold. Keep Plane
running under its original Docker project and volumes. Verify its compose
configuration is discoverable from the new checkout without recreating data.

Exit: frontend hot reload and backend work through the normal owner URL, with
clear lifecycle commands and retained diagnostics.

## 6. Verification before declaring consolidation complete

Run focused checks for the changed boundaries, not the entire inherited suite.
Any new migration/supervision behavior follows red-green-refactor with isolated
fixtures before applying it to live data. A documentation-only plan needs no
runtime test suite; these checks are requirements for eventual execution.

| Boundary | Required evidence |
| --- | --- |
| Git/source | Same fork ancestry/HEAD at cutover; all intentional edits and staged state preserved; bundles/backups verifiable; no secrets staged |
| Paths | CLI/imports/tool cwd resolve to new root; no live process depends on old checkout; legitimate profile/remote names unchanged |
| Runtime storage | Agent identities, souls, memory, outputs/version hashes, questions, decisions, receipts and grants match expected pre-migration state |
| Hermes UI | Agents and one existing detail/output page render; authenticated requests succeed; known media opens; hot-reload connection works |
| Chat | Existing conversation is retained and channel connects; use deterministic isolated replies if exercising tools, not live paid-model prompts for a smoke check |
| Plane | Authenticated project/states/items read works; correct workspace/project IDs and data retained; no duplicate provisioning |
| Scheduling | Isolated restart test admits at most one eligible run; manual pauses, required owner decisions and uncertain-effect barriers survive |
| First Builder | Correct repository binding, protected deployment preserved, Sol/Low settings retained, held for owner test and no autonomous run started |
| Process lifetime | Dashboard/frontend survive launcher exit; supervised failure recovery and deliberate stop are distinguishable; one dispatcher only |
| Contributor experience | Saved project opens current main; refreshed instruction loading uses the current fork AGENTS and First Builder files; no archived prototype profile is active; protected hosted prompts remain unchanged |

Select exact named Python/Playwright cases once the affected implementation is
known. Record command, result and any omitted check with its reason. Reuse passing
evidence until relevant edits invalidate it. Do not call the whole migration
complete merely because ports return HTTP 200.

## 7. Rollback

If a checkpoint fails before writers restart, keep maintenance active. Stop any
new processes, preserve failure logs and partial migration journal, reverse the
specific binding/configuration changes, move the fork back to its original
location and restore the old directory from its temporary copy or verified backup. Restore the old
virtual environment and launch configuration from backup, then verify services
and original owner holds. Validate all path preconditions before each rename.

If work has already resumed, stop admissions and drain again first. Take a fresh
snapshot of new writes. Do not restore an older database/profile blindly: that
could erase new outputs or repeat external actions. Prefer rolling source paths
back while retaining current data, using the inverse supported binding migration.
If schema/data cannot be reversed safely, perform reviewed forward repair and
reconcile effects instead of destructive rollback.

Keeping the temporary preservation copy is optional. Remove it only after the
owner has reviewed the active checkout and the verified Git/working-tree backups.
There is no automatic delete-after-N-days step. Archive/read-only status for the
old GitHub repository is outside this local cutover.

## 8. Tracking, scope and completion report

Plane: [AN-134 — Review and sequence one-directory repository consolidation](http://localhost:19230/agent-native/browse/AN-134/), In review.

Use one Plane consolidation planning item, then small linked execution items:

1. Inventory, backup and accurate unfinished-work handoff.
2. Tested maintenance/repository-relocation prerequisites, only where missing.
3. Filesystem cutover and development environment repair.
4. Service restoration and focused end-to-end verification.
5. Final contributor handoff and owner acceptance of the directory arrangement.

No calendar cycle estimates or placeholder dates. Keep one implementation item
active at a time; dependencies determine order. Reuse AN-15 for service-hardening
criteria and link the migration dependency instead of duplicating its scope.
AN-132/AN-133 remain separate runtime reliability work; this cleanup does not
complete them or unblock the First Builder's launch gate by itself.

The final execution report must identify the active absolute path, Git remote,
branch/commit, private backup location, operational commands, verified runtime
state, completed checks and any remaining limitations. The success condition is
one clear development home with preserved working agents/data and a recoverable
history—not merely two differently named folders.
