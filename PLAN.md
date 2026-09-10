# Current implementation work

AN-110 resolves the output-integrity defect exposed by the Fantasy Game Builder.
The agent produced a valid PNG inside its granted project workspace, but the current
saved-output contract supports only Markdown and plain text. It therefore recorded a
note containing a filesystem path that the dashboard could not open. Managed media
publication now verifies image/audio/video signatures, rejects path and symlink
escapes, copies files into immutable host-owned storage, and records MIME type, size,
checksum, agent, run and work item. The authenticated dashboard renders images and
native audio/video players with Open/Download controls. Media elements fetch their
bytes through dashboard authentication before receiving a browser-local object URL;
the session credential is never placed in the media URL. The existing Greenmoor PNG
was backfilled and its 1024×768 image now renders in both its owner-review card and
Recent outputs. Selecting an image opens a large modal preview with keyboard and
visible close controls; the inline preview remains available for quick scanning.

The live Fantasy Game Builder has exposed a stale-wait defect after productive,
bounded attempts. AN-106 is the immediate reliability fix: a superseded `wait`
judgment must not prevent a cadence-enabled agent from starting its next attempt.
The next major capability is AN-107: persist measured model-token usage and
provider/model cost, aggregate it by attempt, agent and subtree, and enforce
owner-controlled soft and hard budgets. AN-108 then expands the compact Work
direction card with the current concrete step and its three newest related
activities. This must keep bounded-attempt outcomes distinct from whole-agent state.

AN-104 remains the active storage migration foundation. Its first TDD slice adds
the authoritative home resolver and safely provisions distinct practices,
default-project, output and attempt-runtime areas without relocating existing data.
AN-105 follows with functional durable memory and working-practice access.

AN-102 fixes the live Fantasy Game Builder continuation failure. Saved outputs now
use a stable host-owned evidence root, while an owner-granted coding workspace is
used only by repository tools and as the worker's project directory. Granting a
coding workspace can no longer make earlier outputs fail verification. Repeated
failure concerns now retain the latest concrete error in their owner-facing
summary. Focused storage and concern regressions pass; the live stale concern was
resolved after deployment and the Builder resumed with model calls advancing.

The owner selected the Hermes fork and Plane. The live
[Plane project](first-builder/PLANE.md) owns actionable items, priorities,
dependencies and cycles. Read it before selecting work; this is not another board.

Cycle 03 (**Shared agent work and the fantasy writer**) is reconciled: AN-73 is
accepted, while the unfinished portions of AN-74, AN-80 and AN-84 remain explicit
Backlog work outside the closed cycle. The current undated cycle is 04, focused on
the First Builder handoff. AN-57 is active.

The First Builder preparation path pins `openai-codex/gpt-5.6-sol` with Low
reasoning, deploys owner-controlled instructions and an immutable compute-runtime
snapshot outside the writable repository, and grants bounded repository development
tools only to that identity. Preparation leaves its queued work behind an enforced
`held_for_owner_test` gate. The dashboard shows this checkpoint but exposes no
launch action. Run and record the owner's final ordinary test agent before confirming
the checkpoint and activating the Builder; do not launch it as part of preparation.
AN-95 is the live final ordinary-agent checkpoint. Fantasy Game Builder is using
MiniMax M3, approval-driven specification review and a 60-second cadence. AN-96
adds its separately granted coding workspace before implementation begins. A live
Plane project-description write exposed trailing-newline normalization; the adapter
now canonicalizes that field before delivery and during read-only recovery, avoiding
a false unknown outcome. The exact affected receipt was reconciled and cadence
continued in a fresh attempt.
AN-76 is now active for the complete owner journey. Its first missing product control
is implemented as a focused slice: Agent settings can revise the protected purpose
without replacing the stable agent identity, using the current purpose revision as a
compare-and-swap guard. The complete purpose-redirection slice now passes: purpose
revision closes the provider connection, retains the old attempt as `interrupted`,
produces no late output, atomically refreshes the protected soul projection while
preserving workspace and memory, creates a revision-specific Plane discovery item,
and starts exactly one fresh bounded attempt using the existing limits and cadence.
The browser proof finishes with a saved output for revision 2 under the same agent ID.
AN-76's representative owner journey and evidence review are complete. A live
MiniMax-M3 writer created its own Plane brief, undated cycles and work items, kept
planning material out of saved outputs, published two linked stories, exchanged
owner chat and a proactive question, and continued the selected second story on
cadence without a human continuation prompt. The owner then paused its active run
and disabled further cadence. Focused browser proofs cover feedback-to-output,
question-to-output, pause/resume, service restart and purpose redirection without
requiring another paid-model run. Recovered Plane conflicts remain visible and are
the next reliability concern; they do not invalidate the accepted journey.
AN-94 closes that focused concern: a known pre-write conflict returns the current
typed resource and fingerprint in the same tool result, already-satisfied cycle and
dependency relationships confirm without another mutation, and malformed Plane
calls receive an actionable operation-specific result rather than generic
`ContractError` activity. Unknown delivery remains blocking and unchanged.
The compact owner header now shows the protected purpose beside the agent's identity
and places a tooltip-labeled pause/resume control next to execution status. Pausing from
this control atomically stops current subtree work and disables its cadence; resuming
restores only the applicable prior automatic-work state. The live AN-76 writer was
paused after its real-model continuity proof so it cannot consume further model tokens.
AN-93 is complete. Compact view places applicable owner questions before output decisions
and progress concerns in Compact view. A labeled Current/Latest work card follows the
attention area with the ongoing stage, latest bounded-attempt outcome and direct Plane
work-item link. Exact-output review is available directly from the compact decision,
while Full view retains exhaustive diagnostics. Focused browser journeys verify question
and decision ordering, compact/full state preservation, cadence feedback, output and
Plane links, and distinct working, waiting, paused, failed, automatic-off and retired states.
AN-91 completed the shared planning/output boundary exposed by the live fantasy
world agent: Plane owns briefs, cycles, task descriptions, criteria and planning
notes, while Saved outputs contain the actual purpose-level deliverables. Planning
changes may be reported as results with no file. The only exception is an
assignment that explicitly requests a planning document as its deliverable. A
clean replacement agent proved this behavior with a Plane-only planning result
and one actual World Bible output.
**AN-9 deliverable review is complete.** It separates bounded
attempt records from reviewable purpose-level outputs. Attempt summaries, planning,
discovery and waiting/blocked records remain operational history and never imply an
owner approval request. Show Accept / Request revision only on an exact output version
when an explicit owner or policy gate actually requires a decision; optional review
must not block cadence. Add a trusted, version-bound owner workflow to accept a gated
deliverable or request revisions;
the decision must wake the cadence agent and either unlock dependent work or
deliver the requested change. The live Fantasy World Setting Builder is the first
end-to-end case: its discovery result must appear as history without acceptance
controls, while its Cosmology Foundation Draft v1 is the reviewable output. At
balanced autonomy, optional review of that draft must not stop later cadence runs.
Plane Done alone remains insufficient when a real gate exists, and accepting one
output does not declare the agent's whole purpose complete.
The first AN-9 enforcement slice records the review requirement on each result
from the attempt's frozen autonomy level. Approval-driven level 1 requires review
for a submitted result that names at least one exact output version. Ordinary
results and balanced-autonomy deliverables do not expose decision controls, and
the owner API rejects attempts to accept them. The compact view surfaces only
currently gated deliverables; Full view retains all evaluations and prior decisions.
Assignment- and policy-authored gates are covered independently of autonomy level.
The owner-policy half is implemented: Agent settings can require review of every
submitted deliverable independently of autonomy level. The policy is revisioned,
frozen onto admission, visible to the worker, and stored as the exact result gate
source. Assignment-authored gates are now implemented for the agent's selected
Plane work item. The owner toggle binds to the immutable observed assignment
fingerprint; submitted deliverables record `assignment_policy` as their gate source.
If Plane criteria change afterward, submission stops with a stale-policy conflict
until the owner refreshes the gate from a newly observed selection.
Owner decisions also carry the exact criteria revision displayed by the client; the
API rejects a stale decision before accepting or requesting revision.
The review interface is now output-centered: Work results retain evaluation and gate
history but direct required review to the referenced immutable saved-output version.
The output reader clearly distinguishes required, optional, accepted and
revision-requested states, and only a pending required review exposes Accept output or
Request revision. Focused required-review and balanced-autonomy browser journeys pass.
Level 5 autonomous progression is also verified in a focused browser journey: the
agent completes a cosmology output, leaves review optional, then a distinct cadence
session selects and completes a different ready magic-system assignment without owner
input or acceptance controls.
The exact-output Request revision journey is now verified end to end: trusted revision
feedback wakes an enabled one-day cadence immediately, starts a distinct attempt and
saves the requested version 2. The neighboring exact-output Accept journey also passes.
Cadence enforcement now treats an existing required review as an actual gate: no
new automatic attempt is queued while an exact result awaits its owner decision.
Accepting or requesting revision resolves that gate and makes the decision immediately
eligible for the next cadence attempt. Optional review continues without interruption.
AN-92 completes the paired owner-controlled autonomy policy: five eagerness
levels from approval-driven through highly autonomous, with Level 3 as the new-agent
default. The level controls when review blocks continuation; it never weakens an
explicit owner, assignment, authority or mandatory-policy gate. AN-9 supplies the
Accept / Request revision workflow when the resulting gate is genuinely required,
and AN-75 resumes cadence work after the decision.
An accountable parent can now configure one direct child's eagerness level for future
attempts through a revision-bound, reasoned and idempotent managed operation. It cannot
target deeper or unrelated agents, change other configuration, or clear an explicit
owner deliverable-review policy. Paired deterministic browser journeys prove Level 5
continues between ordinary assignments without approval, while the same level stops at
an explicit owner gate and resumes only after the exact output version is accepted.
AN-90 fixes continuation reads: complete immutable saved outputs and stale-question
applicability without terminating work. Targeted regression and native browser proof
pass. Follow-up Plane429 failure prompted local600/minute capacity and bounded
GET-only backoff. Existing writer recovery on Luna completed with a saved next
adventure brief and recorded result; continuing milestone acceptance remains open.
Owner-directed AN-85–87 address recoverable Plane conflicts, agent removal, and
recreating the failed Fantasy Wizard Series. Known rejected conflicts now allow
fresh inspection within the same run; unknown delivery still stops work.
**AN-75 cadence/continuation is In Progress.** Opt-in cadence and retained
attempts are implemented; a live agent has picked up Plane feedback and saved a
revised output without a manual continuation prompt. The demo exposed a false
cycle-assignment conflict after timestamp-only Plane updates; that is now fixed
with focused backend and browser coverage. Restart recovery now records a settled
process interruption explicitly and lets enabled cadence begin a fresh attempt;
it never replays the interrupted process, and any effect or Plane delivery without
a settled receipt remains outcome-unknown for owner review. Owner pause remains
terminal and cannot auto-recover. Cadence failures now receive the same conservative
classification: a stopped attempt with fully settled effects becomes retryable and
continues in a fresh session at the next check-in; all other failures remain blocked.
Actionable-input wake-up is now durable and distinct from routine interval scheduling.
Owner answers, owner result decisions, parent evaluations and new direct-child results
make enabled cadence promptly eligible after current work settles, even when the normal
interval is long. The retained wake survives busy work and restart, is consumed only
with fresh admission, and never enables disabled cadence.
Repeated failures remain visible as separate attempts for later no-progress policy.
A normal per-attempt runtime limit is now recorded separately
from owner pause and remains eligible for a later cadence attempt; legacy timeout
records are repaired on startup. Agent creation uses 900 seconds and 50 model
steps per attempt by default, with overrides collapsed under advanced controls.
AN-73 conversations and AN-84 comment review have implemented
increments, with broader acceptance still open. AN-80 remains in Backlog:
uncertain-delivery reconciliation and safe description merging are deferred.
The reasoning-default clarification is complete: actionable labels and explicit Astra Low.
See [model settings and verification](implementation/agent-model-selection.md).
The owner moved this earlier usable-agent milestone ahead of the First Builder:
create an ordinary root from a purpose, talk to it, see it write and save stories,
steer its work, inspect activity/sessions, then observe useful continuation on cadence.
The first saved story is a checkpoint; continuing conversation, real stopping,
evaluation and basic recovery belong in the completed milestone.

- Next refinement: [shared agent work and outputs](implementation/shared-agent-work.md).
- Product acceptance: [first writer](design/14-first-writer-milestone.md).
- Delivery slices and scope: [writer implementation](implementation/fantasy-writer-milestone.md).
- Full requirements: [design](design/README.md).
- Unadopted design ideas: [brainstorming notes](design/ideas/README.md); these do not change delivery priorities.
- Capability roadmap: [delivery plan](implementation/delivery-plan.md).
- Work traceability: [Plane coverage](implementation/plane-roadmap-coverage.md).
- Session evidence: [Builder state](first-builder/STATE.md).
- Local services: [Plane operations](ops/plane/README.md), [dashboard operations](ops/dashboard/README.md).

Reuse accepted identity, creation UI, private provisioning, restricted environments
and Plane host read/write/recovery work. AN-24's verified inspection/revocation
increment remains evidence, but broad remaining enforcement returns to backlog;
the writer slices enforce all operations they actually expose. Minimal ordinary-root
Plane provisioning comes forward; Builder repository privileges, broader native
integration and full teams stay later. No completed evidence is reopened or erased.

AN-77 is deferred by the owner: selected agents now open the existing Hermes TUI with their
protected purpose, private workspace and separate retained native conversations.
See [managed conversation](implementation/native-agent-chat.md) for scope and
verification. Conversation is available independently of Plane readiness and
cannot start project work. Native drafts and submission receipts now support
renderer restart and safe explicit retries. Each message now runs in an isolated
native worker with a hard host deadline and receipt checks at persistence.
Browser recovery now survives a full service crash, preserving drafts/history
and marking interrupted messages uncertain without replay. Remaining acceptance
covers purpose-revision/transcript ordering. A live managed subscription exchange
is verified. Reuse native conversation storage, composer and model loop throughout; do not build a second chat implementation.

AN-72's bounded first-writer checkpoint is complete. The authorized live demo
used GPT-6 Astra through the existing ChatGPT subscription, authored its Plane
plan and saved a verified story. A separate live browser Pause stopped its actual
native worker. The original three preview agents remain unchanged. See
[managed writing](implementation/writer-managed-run.md) for scope and evidence.
The demo's explicit 300-second/20-step limits are not global defaults. The
captioned video is verified and AN-72 is Done in Plane. The owner then requested
a shared interface for the framework. AN-78 now provides shared bounded work and results plus the verified shared
Saved outputs/Results reader in the local preview. AN-79 now adds the verified
shared Work planning view: project and cycles, explicitly selected work and
requirements, direct Plane links and independent refresh/stale states. Existing
runs keep their history without an invented selection. The owner added AN-80 for continuous Plane progress comments, per-agent verbosity and
verified output links/description sections; it follows AN-79 and precedes AN-73,
which connects proactive questions and steering to the shared work. The writer and an
analyst on supplied material must use the same path; a useful outcome need not
produce a story or a file. The Plane skill now directs incremental comments during
work, not a retrospective batch at completion; enforceable reporting configuration
and delivery remain AN-80, following the owner-prioritized AN-27 model selection. AN-81 now provides a verified
recording of all 30 current framework browser scenarios, with 47 readable proof
checkpoints and a chapter index. AN-82 adds a separate 4:38 narrated tour of the main
implemented features, with readable screen holds, chapter navigation and a transcript.
AN-27 is now complete: defaults, per-agent overrides, immutable attempt choices
and exact native routing are verified with local scripted model responses. AN-80 is next. The external Builder used
progress comments on AN-78 and AN-79 throughout implementation and verification.
AN-74–76 retain detailed inspection, continuity and full milestone acceptance.
AN-74 includes the owner-requested shared Activity table: newest first, twenty
rows by default, 20/50/100 choices and true bounded pagination.
See [Builder state](first-builder/STATE.md) for the exact handoff.

The subsequent AN-16/M7 First Builder handoff adds protected repository development
and demonstrates a real TDD improvement using the writer's run/chat/continuity
foundation. The First Builder remains hosted by the external coding environment.
Existing preview agents are not automatically enabled. The Builder handoff remains later.

Follow small TDD increments and the existing Playwright setup, using
[named test cases by default](first-builder/PRACTICES.md#targeted-verification-by-default). Keep one active
implementation slice, no cycle dates or duration estimates. Runtime cadence and
finite limits remain explicit agent configuration; creation starts with the
owner-selected 900-second and 50-model-step defaults unless advanced values are set.

Owner promoted AN-84 (incoming Plane comment review/replies) next, after the AN-73
question-comment increment. AN-84 now supplies scoped in-run discussion review;
AN-75 still owns cadence wake-up/continuation. See Builder state for verification
and remaining acceptance. Keep cycles undated.

AN-75 is complete: opt-in cadence and retained attempts bring the agent beyond a
single run. Its continuity behavior includes bounded
check-ins, prior-work context, Plane-feedback revision and visible attempt history.
whole-purpose evaluation, legitimate waiting and clarification, guarded retirement,
actionable-input wakeups, bounded recovery, and restart-safe continuation. Broader
purpose-change handoff remains AN-41, activity-without-progress policy remains AN-51,
and broader comment acceptance remains AN-84.
The restart boundary now also has native browser evidence: restarting the actual managed
work service during a held provider call retains the stopped attempt as interrupted,
admits exactly one distinct cadence attempt, and leaves cadence eligible without replaying
the old process. Unsettled effects remain covered by the paired backend rejection case.
The first whole-purpose lifecycle slice is now implemented: a managed agent records
an immutable `continue`, `wait`, `clarify`, or `retire_candidate` judgment with the
protected purpose revision, evidence, remaining obligations, uncertainty and next
action. Later attempts receive those records and the compact view shows the latest.
Guarded root-agent retirement is now implemented as a separate managed operation.
The agent must cite its latest current-revision `retire_candidate` evaluation, and
the host independently rejects retirement while uncertainty, remaining obligations,
unanswered questions, required result reviews, unresolved tool receipts or uncertain
Plane writes remain. Success disables cadence, invalidates earlier work authority and
preserves the evaluation and all history. The present runtime exposes root agents only;
subtree review and cascade remain part of the hierarchy increment rather than being
simulated in this root-only data model.
The paired owner UX is also implemented: the ordinary roster remains limited to
active agents, an explicit retired-agents view keeps retired identities discoverable,
and a retired detail page shows the exact purpose evaluation and evidence that
authorized retirement. Retirement and owner removal have distinct labels and
records; neither permits new chat, settings changes or autonomous work.
The first M3 hierarchy foundation is now implemented under AN-37. Every agent has
an immutable direct-parent relationship or is a root; arbitrary nesting is supported,
creation retries cannot change parentage, and a child cannot be attached to a missing,
removed or retired parent. The owner can select a parent during creation, inspect
parent/child links, and browse the recursive active-agent tree. Until atomic subtree
controls land, removal and self-retirement reject a parent with active descendants so
the framework cannot leave an active orphan. The next hierarchy increment grants a
managed parent a scoped child-creation operation with explicit delegated purpose and
frozen configuration. That increment is now implemented: an admitted parent can create
one direct child per idempotent tool-call identity, and the child starts queued with an
immutable parent link plus the parent's frozen model, autonomy level, work limits and
enabled cadence. The managed operation accepts no credentials or configuration overrides,
and its audit record binds the child to the parent run, reason and inherited settings.
The accountable-parent supervision increment is now implemented. Each fresh parent
attempt receives a bounded direct-child roster; managed inspection exposes descendant
status, result/output metadata and verified chunks of exact saved-output versions while
excluding private reasoning and credentials. Only the direct parent can record an
immutable accepted, revision-requested or rejected evaluation of an exact submitted
child result. The evaluation remains separate from human acceptance, wakes the child's
cadence, and routes revision or rejection as applicable child feedback. Owner pause is
now a durable, atomic subtree operation: it disables cadence, stops or pauses active
attempts, blocks new autonomous work and child creation, preserves attempt history, and
exposes every applicable pause source. Repeating the request is safe, and a separately
paused descendant retains its own pause cause. Explicit owner resume now removes only
the selected source, restores each finally-unpaused agent's prior cadence, makes it due
for fresh reconsideration, and leaves independently paused descendants paused. Verified
whole-purpose retirement now applies atomically to the entire active descendant tree.
Every descendant is checked for unanswered questions, required owner reviews and
unresolved effects before any identity changes; one blocker aborts the operation. The
parent's evaluation is retained as shared provenance, descendants identify the deciding
parent, active work is stopped, cadence is disabled and all history remains readable.
The first explicit replacement control is now implemented for the owner: it atomically
creates a distinct successor under the same parent, copies bounded model/autonomy/work/
cadence configuration, records the reason and selected handoff, retires the predecessor
subtree, and links both identities. It fails closed on unresolved subtree authority and
replays safely after a lost response. The successor receives the handoff in its managed
work context; private memory and descendants are not copied. Accountable parents now
receive the same operation as `child_replace`, scoped strictly to one direct child and
bound to the live parent attempt and tool-call identity. The child records the deciding
parent, replays return the same successor, and attempts to skip the accountable parent
by targeting a deeper descendant fail without lifecycle changes.
Clarification enforcement is now connected: the judgment must name an applicable
unanswered framework question, cadence suppresses redundant attempts while it is open,
and the trusted owner answer wakes the next review without overriding owner pause.
`wait` retains normal cadence. Guarded retirement remains next.

AN-67's recommended threshold and response are now owner-approved in
[activity-without-progress detection](implementation/no-progress-detection.md).
The first AN-51 slice counts only consecutive safely retryable cadence
failures with no result, output, useful learning or new owner direction; after three,
it records one concern and suspends cadence. The owner-controlled threshold defaults
to three, accepts two through ten, and explicit resume resolves and resets the sequence.
The next AN-51 slice applies the same bounded response when three consecutive cadence
attempts report completion but record neither a result nor a saved output. It records
a distinct concern so the UI and evidence identify silent completion separately from
terminal failure. Any recorded result or output resets the sequence.

## Rejected managed-tool receipts — 2026-09-09

AN-97 is In Progress in Cycle 04. The Fantasy Game Builder test exposed that
validation and scoped authorization failures after effect admission left NULL
receipts, making a failed bounded attempt look like an uncertain external write
and stopping cadence. Safely rejected calls now receive durable, replayable
rejection receipts with their tool name and error class; diagnostics omit the
arguments and private provider data. Full authority revocation still stops the
run, and uncertain external delivery remains unknown and blocks automatic retry.
Focused broker, scoped-progress, unknown-write and cadence-classification tests
pass. The restarted local preview migrated the existing receipt table. A clean MiniMax M3
Fantasy Game Builder encountered invalid and conflicting Plane calls, retained zero
unresolved receipts, continued through 20 model steps, published GDD v1, asked a
consolidated owner question, and completed its bounded attempt at the intended
approval gate. AN-97 is complete; the First Builder remains held behind the owner
test gate.

## Self-driven creation and truthful waiting state — 2026-09-09

Cycle 04 defects AN-98 and AN-99 correct the final-test lifecycle mismatch. Creating
an agent with bounded work now atomically enables a 60-second cadence by default.
Questions and required reviews remain eligibility gates while cadence stays enabled.
The compact header now shows Enable automatic work when cadence is actually off,
uses the cadence endpoint to enable it, and reserves Pause automatic work for an
enabled cadence. Completed work with an unresolved owner dependency reads Waiting
for your decision rather than Automatic work off or a generic next check-in. Focused
API and installed-Chromium browser journeys pass. The deployed build repaired the
existing Fantasy Game Builder through the normal UI: cadence is enabled at 60 seconds,
its unresolved GDD question remains the active eligibility gate, and no redundant run
was started. AN-98 and AN-99 are Done. The First Builder remains held.

## Ordinary-agent protected workspace — first increment — 2026-09-09

AN-96 is In Progress. The owner can now grant one existing repository root to one
ordinary agent through an authenticated API operation. The durable grant is scoped
to that identity, compare-and-swap bound to its soul revision, rejects symlink or
missing roots and cannot reuse the First Builder launch authority. Managed work now
resolves the granted root and exposes the existing bounded read, CAS write and
command tools only when that grant is active; ordinary ungranted agents retain no
repository tools or visibility. Focused grant, denial, First Builder separation and
adjacent creation tests pass. Next: add the owner-facing provisioning flow and a
protected build/serve lifecycle with a stable playable link before granting the
Fantasy Game Builder. The First Builder remains held.

## Owner workspace provisioning — 2026-09-09

AN-96 now includes an owner-facing Agent Settings flow. The agent API exposes the
current project-workspace grant, the settings dialog accepts an existing absolute
root, and successful provisioning replaces the form with the exact active boundary
and an isolation explanation. A focused installed-Chromium journey proves the
request and visible readback; focused backend grant/denial and adjacent API tests,
TypeScript, ESLint and Ruff pass. Next: run builds in the granted boundary and
publish a stable owner-visible playable URL without granting host-wide process or
network authority. The Fantasy Game Builder remains ungranted pending GDD acceptance,
and the First Builder remains held.

## Stable project previews — 2026-09-09

AN-96 now provides a generic managed `repository_preview_publish` operation for
ordinary coding agents. It publishes a static directory only inside the agent's
active project-workspace grant, requires a regular `index.html`, rejects absolute,
parent and symlink escapes, and records a versioned stable agent preview URL. The
authenticated dashboard serves the current preview without granting the agent a
long-running host process or arbitrary network listener. The compact agent header
shows an Open project preview control with a tooltip. Six focused repository and
isolation tests, the installed-Chromium preview-link journey, TypeScript, ESLint,
Ruff, compilation and the production build pass. The local dashboard is deployed
with both workspace and preview schema. AN-96 remains In Progress until the accepted
Fantasy Game Builder is provisioned and proves a real build increment. The First
Builder remains held.

## Current checkpoint clarification — AN-100 and AN-101

AN-100 and AN-101 remove the ambiguity exposed by the Fantasy Game Builder checkpoint.
Compact output reading omits optional, undecided review UI while Full view retains the
evaluation evidence. The compact Work direction card now states what the agent is
working on and what it intends to do next. A whole-purpose `wait` judgment makes
enabled cadence dormant without model calls until durable actionable input arrives;
owner feedback now supplies that wake signal and admits one fresh attempt. The owner
acceptance of Fantasy Game Builder GDD v2 was delivered through that path, the exact
output decision was recorded, and its isolated coding workspace was granted for
implementation.
