# Current implementation work

The owner selected the Hermes fork and Plane. The live
[Plane project](first-builder/PLANE.md) owns actionable items, priorities,
dependencies and cycles. Read it before selecting work; this is not another board.

The current undated cycle 03 is **Shared agent work and the fantasy writer**.
The owner moved this earlier usable-agent milestone ahead of the First Builder:
create an ordinary root from a purpose, talk to it, see it write and save stories,
steer its work, inspect activity/sessions, then observe useful continuation on cadence.
The first saved story is a checkpoint; continuing conversation, real stopping,
evaluation and basic recovery belong in the completed milestone.

- Next refinement: [shared agent work and outputs](implementation/shared-agent-work.md).
- Product acceptance: [first writer](design/14-first-writer-milestone.md).
- Delivery slices and scope: [writer implementation](implementation/fantasy-writer-milestone.md).
- Full requirements: [design](design/README.md).
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
Saved outputs/Results reader in the local preview. AN-79
retains the fuller Work view, including real planning context and criteria. The
owner added AN-80 for continuous Plane progress comments, per-agent verbosity and
verified output links/description sections; it follows AN-79 and precedes AN-73,
which connects proactive questions and steering to the shared work. The writer and an
analyst on supplied material must use the same path; a useful outcome need not
produce a story or a file. The Plane skill now directs incremental comments during
work, not a retrospective batch at completion; enforceable reporting configuration
and delivery remain AN-80. The external Builder used comments on AN-78 throughout this increment.
AN-74–76 retain detailed inspection, continuity and full milestone acceptance.
AN-74 includes the owner-requested shared Activity table: newest first, twenty
rows by default, 20/50/100 choices and true bounded pagination.
See [Builder state](first-builder/STATE.md) for the exact handoff.

The subsequent AN-16/M7 First Builder handoff adds protected repository development
and demonstrates a real TDD improvement using the writer's run/chat/continuity
foundation. The First Builder remains hosted by the external coding environment.
Existing preview agents are not automatically enabled. The Builder handoff remains later.

Follow small TDD increments and the existing Playwright setup. Keep one active
implementation slice, no cycle dates or duration estimates. Runtime cadence and
finite limits must be explicitly configured before launch; open defaults remain open.
