# Activity-without-progress detection decision

Status: **Option B approved by the owner on 2026-09-08.**

This document records the owner decision tracked by Plane AN-67 and the first
implementation slice of AN-51.

## First detectable pattern

Start with the failure loop that automatic cadence can create. An attempt counts
as an **unproductive failure** only when all of these are true:

- it ended as a safely retryable failure;
- it published no new output version;
- it recorded no new result, including discovery or useful learning; and
- no applicable owner answer or direction changed the work since the preceding
  attempt.

Waiting results, useful discovery, a new purpose-level output, owner direction and
a successful result reset the consecutive count. Plane edits, model calls, cadence
ticks and repeated progress comments alone do not count as progress. This narrow
definition does not attempt to judge artistic quality or whether a valid long-running
operation is taking too long.

## Options

| Option | Trigger and response | Tradeoff |
| --- | --- | --- |
| A — aggressive | After 2 consecutive unproductive failures, create one concern and suspend cadence. | Minimizes spend but treats one repeated transient failure as owner-blocking. |
| B — balanced (**recommended**) | After 3 consecutive unproductive failures, create one concern and suspend cadence. | Allows two automatic recoveries while bounding a persistent failure loop. |
| C — permissive | After 5 consecutive unproductive failures, create one concern and suspend cadence. | More opportunity for transient recovery with materially higher wasted work and model cost. |
| D — advisory only | Create a concern after 3, but continue cadence indefinitely. | Preserves autonomy but does not bound the failure loop that motivated this slice. |

## Recommended behavior

Option B is the initial framework default. Store the threshold as an
owner-controlled per-agent setting with a default of 3 and an allowed range of
2–10. The first UI may use the default without exposing customization; exposing
the setting belongs in Agent settings rather than the compact operating view.

At the threshold, create one durable, evidence-linked progress concern covering
the consecutive attempt IDs and reasons. Disable future cadence scheduling and
show **Needs your attention: repeated work without progress** on the compact agent
view. This is an automatic-work suspension, not purpose completion, retirement,
result rejection or a claim that the agent itself is defective. Existing outputs,
results, questions and attempt history remain intact.

The owner can inspect the evidence and choose **Resume automatic work**, change the
model or settings, revise the purpose, or leave the agent suspended. Resuming closes
the current concern with the owner's response and resets the consecutive count.
A later recurrence creates a new concern; repeated check-ins must not create
duplicate concerns while one is open.

## Acceptance for the first slice

1. Three consecutive cadence failures with no new result or output create exactly
   one concern and prevent a fourth automatic attempt.
2. A result containing useful discovery or a new output resets the count.
3. A waiting result and a known external wait do not create a concern merely from
   elapsed time.
4. The compact view explains the suspension and links to the three supporting
   attempts; Full view retains their events and errors.
5. Owner resume is explicit and idempotent. It does not replay an attempt or an
   external effect.
6. Restart preserves the concern and suspended cadence state.

Later AN-51 work can detect repeated replanning, repeated approaches across nominally
successful attempts, and unresolved delegation. Those signals need domain-aware
evidence and must not be inferred from activity volume alone.
