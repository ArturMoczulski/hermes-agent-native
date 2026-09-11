# First Builder — live Plane planning context

Plane is the ongoing source of truth for this project's backlog and planning
cycles. Read this file and apply the [planning skill](../skills/productivity/plane-project-management/SKILL.md)
at the start of substantive work. This file contains connection references, not
an independently maintained task board.

- Local service: [http://localhost:19230](http://localhost:19230).
- Workspace: `agent-native` (`34f36591-6596-40c9-bf66-564529b2c4df`).
- Project: [Agent Native Framework](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/), identifier `AN`, ID `0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897`.
- Initial cycle: [01 — Establish the Builder planning home](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/cycles/29a92720-d45b-49eb-8939-9c779427dd01/). The numbered cycle sequence is undated; advance on accepted outcomes, not calendar time.
- Builder Plane user ID: `be4115f9-e7c5-47fb-863d-daeae60347cd`. This is a planning account, not a framework agent identity.
- Human login: `owner@agent-native.test`; Builder login: `builder@agent-native.test`.
- Credentials: `~/.local/share/agent-native/plane/accounts.json` (private local file).
- Builder API configuration: `~/.local/share/agent-native/plane/builder-api.json`.
- Operation/restart instructions: [local deployment](../ops/plane/README.md).

## Fast status (do this first)

Before reading the board turn by turn, run the read-only status tool. It reads
the private Builder credential and never prints it:

```sh
.venv/bin/python first-builder/tools/plane_status.py summary       # default resume view
.venv/bin/python first-builder/tools/plane_status.py last-worked    # last five items the Builder touched
.venv/bin/python first-builder/tools/plane_status.py current        # in-progress work + next ready priorities
.venv/bin/python first-builder/tools/plane_status.py milestones     # current / next / last milestone
```

Plane is the only planning source. Never choose work from a repository planning
file or copy Plane status back into one.

## Resume through the API

1. Read the skill, current human instruction and this connection context, then run
   the status tool above.
2. Load the Builder credential from the private configuration using the available
   file/HTTP capability. Keep the key out of command arguments, output, logs, Git
   and work-item descriptions. Never use the owner credential for routine planning.
3. Confirm focus from the status tool and the live cycles, work items, dependencies
   and recent comments it does not show. The initial cycle above is a stable
   reference, not a claim that it remains active forever. Determine current focus
   from the ordered sequence, recorded cycle review and unfinished outcomes. Do not
   infer it from today's date. Select the next cycle when prerequisites are accepted;
   never fill planned dates or duration estimates.
4. Check active work and blockers before selecting an item. WIP starts at one
   implementation item for this external Builder. Read acceptance criteria, update
   the selected item, and perform the next authorized small increment using TDD.
5. Record evidence, evaluation and next action in Plane. Keep STATE.md as a brief
   session handoff with item IDs; do not duplicate the backlog in repository files.

Base API: `http://localhost:19230/api/v1/`, authenticated with `X-API-Key`.
Paths verified in Plane Community v1.4.2 (prefix below is project-relative):

`workspaces/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/`

| Operation | Method and suffix |
| --- | --- |
| Read work | `GET work-items/?per_page=100` (follow pagination when needed) |
| Create item | `POST work-items/` with name, description_html, priority, state and assignees |
| Read/update an item | `GET` / `PATCH work-items/{item_id}/` |
| Read/create dependencies | `GET` / `POST work-items/{item_id}/relations/`; creation uses relation_type and issues |
| Read states | `GET states/` |
| Read/create cycles | `GET` / `POST cycles/`; omit planned dates or set them to null |
| Update a cycle | `PATCH cycles/{cycle_id}/`; null start_date/end_date is verified for this release |
| Read/assign cycle work | `GET` / `POST cycles/{cycle_id}/cycle-issues/`; creation uses issues |
| Work comments | `GET` / `POST work-items/{item_id}/comments/`; check current schema before writing |

Use `relation_type: "blocked_by"` for an item's prerequisites. Keep existing stable
IDs; reconcile before retrying uncertain creates. Item `external_source` and
`external_id` identify this bootstrap import but are not a universal API guarantee
of idempotency. Respect 429 and Retry-After, and discover endpoint-specific schemas.

## Scope and bootstrap status

The API account is a member of the local workspace and administers the project it
created. It is not an installation administrator. This is human-authorized local
Builder planning, not proof of managed-agent isolation. No API credential is
forwarded into managed sandboxes. The future adapter must enforce narrower scopes.

The original AN-1 through AN-16 records remain, with native dependency links.
The full design is mapped into capability modules and a product-decision module;
see the [coverage index](../implementation/plane-roadmap-coverage.md). The current
cycle 03 is **Shared agent work and the fantasy writer**. Its acceptance is in the
[writer specification](../design/14-first-writer-milestone.md), with the delivery
sequence in [implementation](../implementation/fantasy-writer-milestone.md).
After the first-story proof, the [shared work/output refinement](../implementation/shared-agent-work.md)
adds AN-78/79 before further conversation/inspection work, with a nonwriter
validation case. Existing writer and First Builder acceptance remain intact.

Cycles 01/02 retain accepted evidence. Cycle 03 is explicitly re-scoped from the
unachieved controlled-Builder goal to the earlier usable writer. The AN-16/M7
Builder handoff follows and retains its history; later Builder cycles reuse accepted
writer foundations. Full teams and broader operation remain backlog work. Use the
live module/cycle/item descriptions for exact membership, state and dependencies.
All cycles remain undated. No planning edit establishes a running managed agent.

Plane does not schedule this external coding agent. These instructions support
continuity across invocations; they do not claim an autonomous Builder cadence.
