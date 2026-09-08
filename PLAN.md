# Current implementation work

The owner selected the Hermes fork and Plane. The live
[Plane project](first-builder/PLANE.md) owns actionable items, priorities,
dependencies and cycles. Read it before selecting work; this is not another board.

The current undated cycle 03 is **Shared agent work and the fantasy writer**.
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
with focused backend and browser coverage. Recovery after interrupted/failed work
remains unfinished. A normal per-attempt runtime limit is now recorded separately
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
Recovery/resume and whole-purpose lifecycle acceptance remain subsequent work;
see STATE.md and Plane for verified scope. AN-84 broader acceptance is deferred.
