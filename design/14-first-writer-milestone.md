# First usable milestone: an autonomous fantasy writer

Status: owner-selected delivery priority, 2026-09-06. This is intended behavior,
not an implemented feature. The owner moved a smaller ordinary-agent milestone
ahead of the [First Builder handoff](08-first-builder.md). It uses the existing
product rules, including Plane planning, protected purpose and trusted owner control.

## Outcome

The owner creates an agent, gives it a purpose such as “Develop an original
fantasy setting and write and improve short stories in it,” and can watch it
work and talk to it. It starts discovery and planning immediately, produces saved
stories, evaluates them and returns to its purpose without a queue of human prompts.
Fantasy writing is the acceptance example, not a hard-coded profession or agent type.

The first checkpoint is one real saved story with visible activity and stopping.
The milestone also requires continuing conversation, proactive questions, a later
autonomous review and recovery. A single prompt/response is insufficient.

## Bounded first experience

Support one ordinary root on the existing local service, with a private filesystem
workspace and its own Plane planning workspace/project. The service establishes
that planning home; the owner does not create boards or paste IDs to start writing.
Do not put story assignments into the framework-development project. The writer
loads the project-management skill and keeps a small brief, backlog, undated cycle,
acceptance criteria and result links. Plane supplies the detailed board.

Use one configured model connection and a narrow set of authorized private writing,
planning and conversation tools. No repository-development privilege, desktop
control, publishing, spending, arbitrary integrations or child delegation is needed
to prove this milestone. Unsupported capabilities remain unavailable in this
installation; the full product's capability policy is unchanged.

Creation shows the configured cadence, model readiness and execution limits. The
owner can configure these in setup or advanced controls without supplying a task
list. Exact timing/capacity defaults remain [open decisions](07-open-decisions.md);
this milestone does not silently approve them. Numeric settings must be explicit
before real unattended activation. A cadence interval is not a cycle estimate.

## Screens and controls

Reuse the existing web application. Keep an Agents roster and one agent detail
page with Chat, Activity and Stories views. The same stable identity, current-work
summary, purpose, cadence, pending-question count and Pause/Resume controls remain
visible across these views. Refreshing or switching views never starts new work.

| Surface | Required contents and behavior |
| --- | --- |
| Agents | Create from name and purpose; show setup/queued/planning/working/waiting/paused/failure and last observed activity. Creation retries retain one identity and one initial activation. Selecting a row opens that agent. No second start prompt. |
| Chat | Durable owner conversation across execution sessions, readable replies and progress summaries, story links, proactive question cards, message composer, honest sent/handled/error state. Preserve drafts and history on reconnect. |
| Activity | Current assignment and stage, active session/run, activation cause, start/end times, last observation, cadence/last/next review or suspension reason. Show history with expandable model/tool actions, outcomes, errors, interruptions and recovery. Link each session to its work, messages and artifacts. |
| Stories | Open saved drafts and revisions, with title, version, creation time, originating assignment/session, evaluation against the brief and revision feedback. Link the underlying Plane project/cycle/item; do not build another board. |
| Agent controls | Inspect purpose and effective capabilities; explicit Pause, Resume and purpose editing. A purpose edit stops affected active work, preserves prior results and replans under the new revision when otherwise eligible. Show stopping until actual execution cessation is observed. |

“What is it thinking about?” is represented by its recorded plan, short decision
summaries intended for the owner, current action and wait reason. These are not
private chain-of-thought transcripts. Distinguish an agent's report from an observed
tool result. Unavailable details, stale observations and redactions are explicit;
no invented explanations, progress percentages or synthetic activity.

Routine chat can be sent during work without implicitly cancelling it. Explicit
owner redirection is retained and acknowledged when handled. Use Pause for immediate
interruption; purpose edits obey immediate stopping. While paused, messages and
answers remain accepted and inspectable without restarting project work. Any
conversation-only response must preserve the pause and cannot perform project tools.

A root asks the human when direction is missing. Show each pending question once,
with affected work and an answer control. Other clear work may continue. An answer
does not clear a pause or become authority for unrelated actions. A small pending
question list in the agent page is enough here; the global multi-agent Inbox follows.

## Acceptance journey

1. On a configured installation, create a writer with the ongoing purpose above.
   Observe its real setup and initial planning; do not send a separate work prompt.
2. Inspect the brief and first writing assignment in its Plane project. Follow the
   live session and recorded actions. Open a saved story from Stories and see its
   explicit evaluation against the current criteria.
3. Send feedback while it works. See durable receipt and handling, then a reply or
   corresponding revision. In a clarification case, answer one proactive question;
   repeated check-ins do not duplicate it or treat silence as an answer.
4. Observe a later cadence review without a human “continue” prompt. For the sample
   ongoing purpose with clear remaining work, it takes another useful writing or
   revision step. It records why; it does not repeatedly recreate the first story.
   Separate scenarios show legitimate waiting and purpose-fulfillment retirement.
5. Pause during actual execution. Observe stopping and then stopped, inspect the
   preserved output, and confirm cadence/late answers cannot restart work. Resume
   rechecks current direction and unfinished work. Edit purpose during a run and
   demonstrate the old work stopping before the new direction executes.
6. Close and reopen the browser while the service remains running: work and chat
   survive. Restart the service during an attempt: recover the same identity,
   messages, artifacts and work; reconcile uncertain outcomes before retrying.
   No duplicate story submission or overlapping attempt for one assignment.
7. Inspect model/Plane failures and disconnection states. Failures remain visible;
   retries are bounded and stop remains available during a Plane outage. No new
   assignments are admitted from stale plans.

Basic result and whole-purpose evaluation are part of this milestone. Finishing
one story does not end the ongoing purpose. A finite-purpose case can retire after
accepted completion and resolved obligations through framework lifecycle control;
uncertainty asks the owner. Agents do not invent work merely to stay active.

## Scope after this milestone

The next major handoff is the First Builder using this same run/chat/cadence
foundation with protected repository development and continuous TDD. Recursive
teams, a complete organization monitor/global Inbox, advanced progress detection,
many simultaneous roots, general provisioning repair and packaged Linux operation
remain in the roadmap. Basic owner control, source freshness, local restart
recovery and observable execution are required now.

Engineering slices and verification are in the
[writer delivery plan](../implementation/fantasy-writer-milestone.md). The general
[screen specification](12-control-center-screens.md) remains the fuller console brief.
