# UX acceptance scenarios

These scenarios make the [UX design](10-user-experience.md) reviewable and testable.
They supplement the [24 product scenarios](06-product-scenarios.md), not replace
them. They are completion targets, not claims that tests or features exist.
Interaction defaults retain the UX document's review status.

| ID | Given / action | Expected experience | Product scenarios |
| --- | --- | --- | --- |
| UX-01 | An empty installation; create an agent from a purpose and submit twice or retry after a delayed response. | One identity appears in Chat and Monitor without a required lifetime selector. Purpose, supplied outcomes and continuing obligations are retained; initial work is queued immediately, and the UI distinguishes queued from observed planning. | 1, 7, 15 |
| UX-02 | Two same-named agents under different parents; open one, type a draft, switch agents and return. | Parent context disambiguates recipients. Each draft and conversation stays with its agent; selecting an agent creates no work or extra identity. | 5, 10, 14 |
| UX-03 | An agent is working; send additional direction without selecting pause. | The message persists with observed delivery state. Work does not implicitly cancel; acknowledgement/application is distinguished from receipt. | 3, 8, 14 |
| UX-04 | A coordinator has no active turn while two children work and one assignment waits for an answer. | Monitor distinguishes own activity, descendant activity and the blocked branch; the organization is not shown as entirely idle. | 3, 18 |
| UX-05 | An agent creates a child which creates a descendant; search for the descendant. | The expandable tree exposes the relationship with ancestor context, supports keyboard navigation and opens the descendant's chat directly. | 5, 10, 15 |
| UX-06 | A child asks a question which two parents cannot resolve. | History shows the route; one human inbox item appears when it reaches the root-to-human step. Its chat card and work dependency point to that same request. | 4, 19, 21, 24 |
| UX-07 | Answer that request from Inbox, then inspect its original work. | The recorded answer and returning delivery are visible. The UI distinguishes answer accepted, delivered and eligible continuation; it does not invent execution. | 4, 21, 24 |
| UX-08 | A pending request belongs to a paused agent; answer it. | The response is recorded, but the agent remains paused and has no ordinary next activation until separately resumed. | 8, 18, 24 |
| UX-09 | A purpose change or another tab makes an open approval obsolete; submit the old approval. | The obsolete/conflicting state is visible. The answer cannot authorize revised work or create a duplicate request. | 8, 14, 24 |
| UX-10 | Pause an agent with running descendants, or cancel its assignment while it has independent work. | Scope is explicit and interruption begins immediately. Cancellation abandons the selected assignment and durably pauses its performing agent/subtree; independent assignments remain recorded but paused. Stopping is shown until confirmed, unrelated roots continue, and actual worker/action evidence backs the stopped display. | 8, 20 |
| UX-11 | Edit a purpose, retire a parent, or observe an agent retiring after established whole-purpose completion. | Purpose Save triggers interruption. Owner retirement confirmation identifies the whole subtree; agent-initiated retirement shows its evaluation, applicable accountable acceptance and resolved obligations without an extra blanket approval. Both retirement paths use the framework operation, retain inspectable records and retire descendants; stale answers do not revive work. | 6, 8, 17 |
| UX-12 | An external action cannot confirm cancellation, or a worker stops reporting. | Monitor shows last observation and stopping/unknown state. A false done badge is never inferred from silence. | 13, 20 |
| UX-13 | Close the browser during work, then reopen and reconnect. | Agent identity, conversation, pending decisions and work remain. Execution is independent of the browser and updates are reconciled without duplication. | 9, 11, 20 |
| UX-14 | A purpose review finds recurring delivery or monitoring still needed but no action due; another agent is paused or has never worked. | The continuing obligation and wait reason are visible without implying retirement or requiring invented growth work. The review is not a completed task. Last check-in, last work and last completion stay distinct; paused cadence and never-worked states are explicit. | 2, 18 |
| UX-15 | A worker submits an artifact that fails the criteria, then submits an acceptable revision; review the wider purpose. | Work distinguishes submitted, needs revision and accepted, linking evaluator, evidence and criteria. Acceptance alone does not declare the whole purpose fulfilled: remaining growth, service or monitoring obligations stay visible, and uncertain relevance or commitments follow normal escalation. | 23 |
| UX-16 | Repeated attempts yield no new evidence; another agent waits legitimately for an external result. | One linked progress concern shows evidence and response for the first. Waiting alone does not label the second unsuccessful. Neither a concern nor a lack of activity automatically retires an agent; its purpose evaluation remains inspectable, and continued existence is not treated as success. | 22 |
| UX-17 | Inspect a multi-agent exchange that quotes human words and contains a redacted value. | Actual sender and known delivery stages are shown, quoting does not change authority, and redaction is explicit. | 13, 14, 19, 21 |
| UX-18 | Switch Chat/Monitor/Work through a deep link and return with browser Back. | Selected agent/scope and filters remain understandable. Inbox's global versus filtered scope is explicit; unrelated drafts are not lost. | 10, 18, 24 |
| UX-19 | Use keyboard navigation or a narrow screen through creation, chat and an inbox response. | Controls remain reachable and labeled, focus returns sensibly, selection is clear and meaning does not depend on color. | Cross-cutting UX |
| UX-20 | Loading fails, search matches nothing, or an artifact is unavailable. | Loading/error/empty/filtered-empty are distinct; drafts are retained where appropriate, retry is safe, and missing content is not represented as empty success. | 13, 20 |

## Evidence required during implementation

For a user-facing increment, write the relevant Playwright acceptance test before
implementing the behavior, observe a meaningful failure, then implement and verify
small steps. Add unit tests for rules and integration tests for real persistence,
processes and lifecycle boundaries. Follow the [First Builder practices](../first-builder/PRACTICES.md).

Browser tests should exercise the actual frontend, API and isolated backend state.
Use controlled external/model responses where needed; label that evidence as
deterministic integration rather than proof of autonomous judgment. For stopping,
recovery and authority, checking UI text alone is insufficient: inspect real
backend and worker effects. Record commands, expected failures, passing outcomes
and limitations as each slice is completed.

Start with UX-01 and a basic portion of UX-02/UX-04, not all twenty at once.
Layer the remaining cases alongside their features. Screens and screenshots alone
do not satisfy these scenarios.
