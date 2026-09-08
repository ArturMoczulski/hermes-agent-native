# Current implementation work

The owner selected the Hermes fork and Plane. The live
[Plane project](first-builder/PLANE.md) owns actionable items, priorities,
dependencies and cycles. Read it before selecting work; this is not another board.

The current undated cycle 03 is **Shared agent work and the fantasy writer**.
**The compact agent operating view is now the immediate priority.** The default page
must lead with applicable owner questions/decisions, ongoing lifecycle state, current
work, recent purpose-level outputs linked to Plane, and compact recent activity. Move
configuration and destructive controls into dialogs and retain the current exhaustive
surface as Full view. Separate lifecycle from the latest attempt outcome and give clear
confirmation after cadence changes; disabling cadence must visibly say that automatic
work is off rather than leaving the primary status as Completed.
AN-91 completed the shared planning/output boundary exposed by the live fantasy
world agent: Plane owns briefs, cycles, task descriptions, criteria and planning
notes, while Saved outputs contain the actual purpose-level deliverables. Planning
changes may be reported as results with no file. The only exception is an
assignment that explicitly requests a planning document as its deliverable. A
clean replacement agent proved this behavior with a Plane-only planning result
and one actual World Bible output.
**AN-9 deliverable review is now the owner's immediate priority.** Separate bounded
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
Explicit assignment- and policy-authored gates beyond autonomy level 1 remain the
next AN-9 increment.
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
The exact-output Request revision journey is now verified end to end: trusted revision
feedback wakes an enabled one-day cadence immediately, starts a distinct attempt and
saves the requested version 2. The neighboring exact-output Accept journey also passes.
Cadence enforcement now treats an existing required review as an actual gate: no
new automatic attempt is queued while an exact result awaits its owner decision.
Accepting or requesting revision resolves that gate and makes the decision immediately
eligible for the next cadence attempt. Optional review continues without interruption.
AN-92 now defines the paired owner-controlled autonomy policy: five eagerness
levels from approval-driven through highly autonomous, with Level 3 as the new-agent
default. The level controls when review blocks continuation; it never weakens an
explicit owner, assignment, authority or mandatory-policy gate. AN-9 supplies the
Accept / Request revision workflow when the resulting gate is genuinely required,
and AN-75 resumes cadence work after the decision.
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
records are repaired on startup. Agent creation uses 180 seconds and 50 model
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
owner-selected 180-second and 50-model-step defaults unless advanced values are set.

Owner promoted AN-84 (incoming Plane comment review/replies) next, after the AN-73
question-comment increment. AN-84 now supplies scoped in-run discussion review;
AN-75 still owns cadence wake-up/continuation. See Builder state for verification
and remaining acceptance. Keep cycles undated.

AN-75 remains active behind the immediate AN-9 acceptance slice: opt-in cadence
and retained attempts bring the agent beyond a single run. The first cadence increment includes bounded
check-ins, prior-work context, Plane-feedback revision and visible attempt history.
Whole-purpose lifecycle acceptance and activity-without-progress policy remain subsequent work;
see STATE.md and Plane for verified scope. AN-84 broader acceptance is deferred.
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
