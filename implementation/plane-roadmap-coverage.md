# Specification coverage in Plane

Planning review: 2026-09-06, based on specification/engineering snapshot `cc88df3`
and the owner's request to organize the full design into Plane. This is a
traceability index, not a second backlog. **Live Plane owns priorities, states,
assignments, dependencies and cycle membership.** Follow those records on resume.
Product authority remains in `design/`; proposed defaults still require decisions.
Work-item source paths refer to this local repository snapshot; no unpublished
GitHub commit URL is presented as an available source link.

The review covered all 14 product files, the engineering architecture/delivery/UI/
Plane plans and evidence, and the First Builder instructions and planning skill.
Inherited Hermes documentation and old prototype research are implementation
context, not a mandate to implement every upstream feature or old plan.

## Future roadmap addition — independent security review

Later roadmap addition, 2026-09-11: [M8 — Independent security review and containment](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/7c8f10b7-7689-475b-a1c1-1f3e31cda7ed/)
is a deferred capability milestone. AN-135 is its acceptance umbrella, with
AN-136–142 for policy/coverage, action evidence, independent reviewers, continuous
audits, containment, owner interaction and evaluated rollout. All remain Backlog
without cycle dates or current-cycle membership. The
[product chapter](../design/17-independent-security-review.md) and
[delivery/evaluation plan](security-review-milestone.md) define the proposal.
Existing authority, lifecycle, observability and First Builder work is reused;
this addition does not reprioritize current autonomous recovery.

## Latest refinement — shared agent work

Owner direction after the live writer demo, 2026-09-07: the common framework and
interface must serve different purposes. [Shared-work delivery](shared-agent-work.md)
now precedes further writer-specific work. Added [AN-78](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/4b7a3d8b-a48d-4e0b-9e01-0645a126cffd/)
for bounded execution/results and [AN-79](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/d4143b70-112e-421d-ad5a-288dfc92b48c/)
for shared Work/Saved outputs, both Todo in cycle **03 — Shared agent work and the
fantasy writer**. AN-73/74 retain their identities and now describe generic
conversation/decision/inspection behavior. AN-71/76 add a bounded analyst proof
without waiving full writer acceptance. AN-72 stays Done; AN-77 remains deferred.

AN-78 links selected AN-7/9/18/24/26/48 behavior; AN-79 links AN-6/43/47/48.
Existing child/delegation/escalation/monitor and Inbox records stay the source for
those later capabilities, with references to the common work/result model. No
new child or decision implementation is claimed. Existing modules aggregate the
same new items; no duplicate work board or calendar dates were introduced.
This current sequence supersedes historical next-action notes below.

## Milestones and modules

Plane Community modules retain M0–M7 as capability groups. The owner now selects
the earlier **Autonomous fantasy writer** milestone ([AN-71](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6a70b94c-2c1f-483f-9c7c-93cd1a55cd05/)),
before the M7 First Builder handoff. The writer uses scoped ordinary-root execution,
Chat/Work/Activity/Saved outputs, Plane planning and continuing cadence. M7 then adds protected
repository development and a real TDD improvement; full M3–M6 completion is not a
blanket prerequisite for either narrow handoff.

The new writer slices refine selected portions of existing broad capability items.
They link their evidence back without completing unrelated acceptance or creating
a second implementation of the same behavior. Existing IDs, module memberships,
comments and completed evidence are preserved. Module percentages count records,
not proven product completion; acceptance aggregates are not extra implementation.
The initial full-spec mapping below remains useful; the writer section adds its
narrow delivery mapping and takes precedence for current sequence.

| Module / milestone | Outcome |
| --- | --- |
| [First usable milestone - Autonomous fantasy writer](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/283b8ac8-c4e0-4609-a9a6-3909c57eb469/) ([AN-71](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6a70b94c-2c1f-483f-9c7c-93cd1a55cd05/)) | Create from purpose, real saved writing, persistent chat and owner steering, activity/session/story inspection, cadence and basic restart recovery. A single story is an intermediate checkpoint. |
| [Next handoff - Autonomous First Builder (M7)](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/38d8aafd-cc77-4d6a-bb98-e610c8a77acd/) | Subsequent self-bootstrap acceptance gate AN-16: the real managed Builder completes a bounded TDD improvement from the repository workspace, survives interruption and owner steering, and cannot grant itself deployment or soul-edit authority. |
| [M0 - Validate the Hermes foundation](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/f2e73bd1-3c26-44c2-8e01-1b638c6936c8/) | Gate: pinned baseline, maintained patch map and a real engine/tool/stop/restart proof. |
| [M1 - Governed agents and Plane work](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/af3769db-cd94-4209-a6ae-f52ccea00b51/) | Gate: protected identity, scoped authority and planning, durable admission, private layers and readable state. |
| [M2 - One autonomous root](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/e71a7b80-4ba5-4402-a14d-12aa3dee999e/) | Gate AN-12: create from purpose, plan, act, ask, evaluate results and continued need, then continue, wait or retire; basic chat, decisions, stopping and recovery work before unattended cadence. |
| [M3 - Persistent recursive teams](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/e0af2be9-04d3-4ded-9e0d-00ddfdc18f82/) | Gate AN-13: children with purpose-based lifespans, recursive delegation, accountable results, parent-chain questions, subtree control and authorized lateral communication. |
| [M4 - Complete owner control center](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/2d24874b-89c0-452c-8d97-676a85519cde/) | Gate AN-14: connected Chat, Monitor, Inbox, Work, Settings and durable history; truthful freshness/delivery, accessible navigation and complete UX evidence. |
| [M5 - Evaluate outcomes and detect stalled work](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/a758b594-f81b-4343-898b-bbff2e623a98/) | Gate: domain-appropriate result review and one evidence-linked concern per recurring no-progress pattern. |
| [M6 - Reliable always-on operation](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/95e8fc96-2b57-4679-b0dd-ac52def9c32f/) | Gate AN-15: failure-tested recovery, consistent backups, revocation/cancellation, measured capacity and a documented Linux deployment independent of the personal computer. |
| [Product decisions - resolve before dependent behavior](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/modules/3ceeb4bd-b69d-4543-8d4c-9be5684b9011/) | Product policy choices from design/07-open-decisions. |

## Rolling cycles and priority

The owner replaced calendar forecasts with ordered, undated cycles and has now
moved the writer ahead of the Builder. Live cycle start/end fields remain null.
Advance on accepted outcomes or explicit re-scope, never elapsed time.

1. **Establish the Builder planning home — accepted:** retain setup/API/scoped-read
   evidence and its original stable records.
2. **Scoped writes and recoverable planning — accepted host scope:** retain AN-20/22
   and AN-3's bounded recovery evidence; runtime integration remains unfinished.
3. **Shared agent work and the fantasy writer — current:** [AN-71](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6a70b94c-2c1f-483f-9c7c-93cd1a55cd05/)
   aggregates [AN-72](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/887162ef-fc5e-49e5-a53a-4db81b5b1d13/), [AN-73](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/af1fd8d1-d834-47cb-8058-43311469688c/), [AN-74](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2c4884af-2513-4c0b-908d-e2df1cb39686/), [AN-75](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/05338859-4138-411a-a36e-222ebdc8c420/), [AN-76](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cce1926f-51cb-4476-a658-a8d3553d1126/).
   Preserve accepted AN-17 audit in the cycle. AN-66/70 record explicit first-use
   timing and limit configuration; re-scoping does not approve their defaults.
4. **First Builder setup and remaining owner-control work:** AN-57 moves here;
   reuse writer execution/chat/continuity and add protected repository authority.
   Existing broad chat/control records retain any remaining acceptance.
5. **First Builder continuity and remaining root behavior:** reuse accepted writer
   cadence/evaluation/recovery; implement outstanding full-root/development cases.
6. **First Builder handoff proof:** a real hosted TDD improvement, owner steering,
   browser closure/restart and another useful authorized step accept AN-16/58.

The previous cycle-03 controlled-Builder goal was not achieved; the owner explicitly
re-scoped it. Unfinished broad AN-4/5/7/8/18/23/24/25/26/30/32 work returns to
backlog outside that cycle. Writer-relevant portions are now in the new slices;
AN-24's verified dispatch/revocation increment is retained, not undone or declared
full completion. AN-57 moves to cycle 04. AN-66 moves from cycle 05 to cycle 03.
AN-70 remains in 03 for writer-first configuration. All other original cycle
membership and completed states are retained.

Minimal new-root Plane provisioning moves forward as part of [AN-72](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/887162ef-fc5e-49e5-a53a-4db81b5b1d13/);
it creates the writer's own planning home, not story tasks in framework development.
Broad repair/team provisioning, full organization monitoring/Inbox, advanced
progress detection and packaged Linux operation remain later capabilities.

One external Builder has implementation WIP 1. Runtime capacity is separately
configured. Never infer a duration from cycle order, or treat broad capability
parents as dependencies on every deferred sibling. Testing happens inside each
small behavior; final real-model acceptance complements those tests.

## Current writer delivery mapping

| Record | Selected requirement | Shared capability references |
| --- | --- | --- |
| [AN-72](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/887162ef-fc5e-49e5-a53a-4db81b5b1d13/) | Configured create, own planning home/discovery, protected actual run, visible result and Pause | AN-4/7/18/21/23/24/25/26/30/32/37; real launch uses AN-70 settings |
| [AN-73](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/af1fd8d1-d834-47cb-8058-43311469688c/) | Durable chat, question/answer, feedback, purpose edit/stop and owner steering | AN-8/10/25/28/29/30/31/41/43 |
| [AN-74](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2c4884af-2513-4c0b-908d-e2df1cb39686/) | Activity/session history, truthful events, story versions and evaluations | AN-32/42/43/44/46/48 |
| [AN-75](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/05338859-4138-411a-a36e-222ebdc8c420/) | Cadence, result/purpose review, fresh planning, browser/restart continuity, no duplicate work | AN-9/11/23/27/33/34/35/36/66/69 |
| [AN-76](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cce1926f-51cb-4476-a658-a8d3553d1126/) | Complete real-model owner journey | Earlier writer slices; [AN-71](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6a70b94c-2c1f-483f-9c7c-93cd1a55cd05/) aggregates acceptance |

Sources: [writer product specification](../design/14-first-writer-milestone.md)
and [writer delivery plan](fantasy-writer-milestone.md). Those define the selected
subset; existing records retain full-product acceptance and history.

## Product chapter mapping

| Canonical specification | Representative delivery records |
| --- | --- |
| [14-first-writer-milestone.md](../design/14-first-writer-milestone.md) | [AN-71](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6a70b94c-2c1f-483f-9c7c-93cd1a55cd05/), [AN-72](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/887162ef-fc5e-49e5-a53a-4db81b5b1d13/), [AN-73](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/af1fd8d1-d834-47cb-8058-43311469688c/), [AN-74](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2c4884af-2513-4c0b-908d-e2df1cb39686/), [AN-75](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/05338859-4138-411a-a36e-222ebdc8c420/), [AN-76](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cce1926f-51cb-4476-a658-a8d3553d1126/) |
| [README.md](../design/README.md) | [AN-12](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/ff2be107-80a4-4271-b234-f2cac434c510/), [AN-27](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/8f765bc9-70b9-4436-a40b-06db4409e832/), [AN-56](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e35a45e1-df2c-46d1-aad8-25b678d735b3/), [AN-16](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/950ff1ab-7337-4f5b-a49d-a4731c4fddf0/) |
| [01-agents.md](../design/01-agents.md) | [AN-24](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/b0df579f-b4f5-499b-b10b-3e2e1534d9ec/), [AN-25](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cc831c6a-7861-4d31-b699-b2100a9db1cd/), [AN-8](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/9e9435d9-cf72-4644-a85d-f7bf375941c1/), [AN-37](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/362e1e32-9a64-489e-958c-834c70fa9e7f/), [AN-41](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/231fb9b3-f101-481c-8fce-1f3f90cb8165/) |
| [02-independent-work.md](../design/02-independent-work.md) | [AN-11](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a40b50fd-864b-4ecc-95bb-09284ba84383/), [AN-26](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6f58d687-56a6-473a-ad5f-a1d1d8b99a44/), [AN-33](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/dd441efc-ed43-4a34-a4e3-904b0be1ebd0/), [AN-34](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/ce8e376a-3f05-4788-8080-9715353d5994/), [AN-35](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/22692c3e-b55f-4f3e-bea1-def47ccf1ef4/), [AN-51](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2f168877-3fd7-4fe3-a94b-152e423656e2/) |
| [03-projects-and-delegation.md](../design/03-projects-and-delegation.md) | [AN-9](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5d27c83c-8e08-4d4a-a006-bc462ab78fc1/), [AN-38](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a32beb4e-1c80-4fcf-8a8f-dff24754eafa/), [AN-42](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/7b7ec1eb-0f5c-4415-98af-5d1d9a2bdcea/), [AN-52](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/be386efb-4cb7-40e9-8283-8cfdcfe09f57/) |
| [04-workspaces-and-skills.md](../design/04-workspaces-and-skills.md) | [AN-19](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/737877ea-91c6-4cc2-b1ab-31508dc47238/), [AN-24](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/b0df579f-b4f5-499b-b10b-3e2e1534d9ec/), [AN-25](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cc831c6a-7861-4d31-b699-b2100a9db1cd/), [AN-26](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6f58d687-56a6-473a-ad5f-a1d1d8b99a44/), [AN-55](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/648ac50a-57dd-4697-b241-7f9d68a6f399/) |
| [05-human-interaction.md](../design/05-human-interaction.md) | [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/), [AN-29](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e7bd0945-6404-4126-a8a7-90111e94fed6/), [AN-30](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6d9c59dd-f04a-4546-8e92-7bb8986c70e2/), [AN-31](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e5eeaaba-18a4-49ce-aba3-8d7a2cd11ae4/), [AN-39](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0899b5fc-de2b-4f74-bfaf-890e02c6da54/), [AN-40](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a68016fe-d1f3-4340-a422-38b296732b55/), [AN-41](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/231fb9b3-f101-481c-8fce-1f3f90cb8165/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/) |
| [06-product-scenarios.md](../design/06-product-scenarios.md) | [AN-12](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/ff2be107-80a4-4271-b234-f2cac434c510/), [AN-13](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/ab640be8-cc39-40a0-861e-1f3148b69eac/), [AN-14](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/d9f9be07-935e-4e6a-8292-f1b8f9c70054/), [AN-15](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/9ac1a96c-8ce0-45ef-bf31-bf543a5db917/), [AN-16](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/950ff1ab-7337-4f5b-a49d-a4731c4fddf0/) |
| [07-open-decisions.md](../design/07-open-decisions.md) | [AN-59](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/f56afd5a-43f4-4274-baa1-f0ddc69dfcb4/), [AN-60](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/36b0d47f-450f-4042-ad49-2e29ffed7673/), [AN-61](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/dd57c601-772f-46de-96ed-532b445aba5b/), [AN-62](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/c48e5cde-ef6c-41be-95f0-7b3010b43cd9/), [AN-63](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3007c03d-50b4-4703-b9f2-343a6a44f04e/), [AN-64](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a81acad8-c2ff-4a7c-ab0b-a2f6868d1111/), [AN-65](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/aa20b66c-ee66-4566-8ba8-11cee2d8df60/), [AN-66](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0759460a-9d5c-4e20-a7f5-9e1e68894962/), [AN-67](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/097f6bd8-3ff1-4cb1-8c15-be29ab1f695e/) |
| [08-first-builder.md](../design/08-first-builder.md) | [AN-57](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/d1d913c7-0cc1-4965-9daf-5a419d43b978/), [AN-58](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cb2d3218-8ad6-4826-9ce5-9c69e7da693d/) |
| [09-observability.md](../design/09-observability.md) | [AN-32](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/17ccdecf-e02f-44a1-82a9-949fe6d64f46/), [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/), [AN-46](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0964fcf9-2c76-460b-a6b6-b60b10ebedb9/), [AN-42](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/7b7ec1eb-0f5c-4415-98af-5d1d9a2bdcea/), [AN-51](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2f168877-3fd7-4fe3-a94b-152e423656e2/) |
| [10-user-experience.md](../design/10-user-experience.md) | [AN-43](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/f376a9bc-23db-4c34-94ee-e36510fdf494/), [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/), [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/), [AN-6](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/26b8a2bc-fa02-45ae-86ae-373c132609cb/), [AN-49](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6ad8a1b8-6881-442c-856c-179ef203f5b9/) |
| [11-ux-scenarios.md](../design/11-ux-scenarios.md) | [AN-12](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/ff2be107-80a4-4271-b234-f2cac434c510/), [AN-49](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6ad8a1b8-6881-442c-856c-179ef203f5b9/) |
| [12-control-center-screens.md](../design/12-control-center-screens.md) | [AN-43](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/f376a9bc-23db-4c34-94ee-e36510fdf494/), [AN-11](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a40b50fd-864b-4ecc-95bb-09284ba84383/), [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/), [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/), [AN-47](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/96f2aac1-52b8-465c-8bd9-a4666dc64e55/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/), [AN-6](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/26b8a2bc-fa02-45ae-86ae-373c132609cb/), [AN-48](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/88fe7dfb-8d7c-4aa3-8b51-e877c68c4cf7/), [AN-46](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0964fcf9-2c76-460b-a6b6-b60b10ebedb9/), [AN-30](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6d9c59dd-f04a-4546-8e92-7bb8986c70e2/), [AN-49](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6ad8a1b8-6881-442c-856c-179ef203f5b9/) |
| [13-project-management.md](../design/13-project-management.md) | [AN-1](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2bbf3501-b3e1-44c3-83c7-e7a93f9d8e28/), [AN-2](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/61030f19-09ac-4500-bbac-e9b45fb490fc/), [AN-3](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e821a77c-2060-4022-94c0-19cc966154c7/), [AN-19](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/737877ea-91c6-4cc2-b1ab-31508dc47238/), [AN-20](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/4baf9a5e-3df7-439d-8241-5733a83debac/), [AN-21](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3f765e57-ccca-4f1c-b095-a69d2ee8440c/), [AN-22](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2aaa9d8e-0311-4bc3-9c77-d0b85eadfad8/), [AN-23](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5bacc4af-edae-4ce4-a872-641c0d6d6bff/), [AN-26](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6f58d687-56a6-473a-ad5f-a1d1d8b99a44/), [AN-35](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/22692c3e-b55f-4f3e-bea1-def47ccf1ef4/), [AN-36](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cbf7c3bc-3ecf-465c-82cd-79dead9ce3ea/), [AN-54](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56720c94-6a3a-48bc-8a42-4c382e90836b/) |

## Acceptance scenario traceability

References are assigned test targets, not a claim that those tests pass.
Playwright covers user flows alongside feature delivery; unit/integration checks
exercise authority, persistence, real processes and failures. Model-driven planning
evidence is recorded separately from deterministic model fixtures.

| Product scenario | Delivery records |
| --- | --- |
| 1 | [AN-21](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3f765e57-ccca-4f1c-b095-a69d2ee8440c/), [AN-26](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6f58d687-56a6-473a-ad5f-a1d1d8b99a44/), [AN-35](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/22692c3e-b55f-4f3e-bea1-def47ccf1ef4/) |
| 2 | [AN-35](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/22692c3e-b55f-4f3e-bea1-def47ccf1ef4/) |
| 3 | [AN-33](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/dd441efc-ed43-4a34-a4e3-904b0be1ebd0/), [AN-35](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/22692c3e-b55f-4f3e-bea1-def47ccf1ef4/), [AN-38](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a32beb4e-1c80-4fcf-8a8f-dff24754eafa/), [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/), [AN-55](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/648ac50a-57dd-4697-b241-7f9d68a6f399/) |
| 4 | [AN-29](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e7bd0945-6404-4126-a8a7-90111e94fed6/), [AN-35](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/22692c3e-b55f-4f3e-bea1-def47ccf1ef4/), [AN-39](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0899b5fc-de2b-4f74-bfaf-890e02c6da54/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/) |
| 5 | [AN-37](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/362e1e32-9a64-489e-958c-834c70fa9e7f/), [AN-38](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a32beb4e-1c80-4fcf-8a8f-dff24754eafa/), [AN-55](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/648ac50a-57dd-4697-b241-7f9d68a6f399/) |
| 6 | [AN-19](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/737877ea-91c6-4cc2-b1ab-31508dc47238/), [AN-24](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/b0df579f-b4f5-499b-b10b-3e2e1534d9ec/), [AN-25](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cc831c6a-7861-4d31-b699-b2100a9db1cd/), [AN-37](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/362e1e32-9a64-489e-958c-834c70fa9e7f/), [AN-41](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/231fb9b3-f101-481c-8fce-1f3f90cb8165/), [AN-47](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/96f2aac1-52b8-465c-8bd9-a4666dc64e55/) |
| 7 | [AN-19](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/737877ea-91c6-4cc2-b1ab-31508dc47238/), [AN-20](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/4baf9a5e-3df7-439d-8241-5733a83debac/), [AN-21](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3f765e57-ccca-4f1c-b095-a69d2ee8440c/), [AN-25](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cc831c6a-7861-4d31-b699-b2100a9db1cd/), [AN-26](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6f58d687-56a6-473a-ad5f-a1d1d8b99a44/), [AN-35](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/22692c3e-b55f-4f3e-bea1-def47ccf1ef4/) |
| 8 | [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/), [AN-30](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6d9c59dd-f04a-4546-8e92-7bb8986c70e2/), [AN-31](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e5eeaaba-18a4-49ce-aba3-8d7a2cd11ae4/), [AN-40](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a68016fe-d1f3-4340-a422-38b296732b55/), [AN-41](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/231fb9b3-f101-481c-8fce-1f3f90cb8165/) |
| 9 | [AN-18](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5d1f5591-1af5-497b-aa3a-633ae6cb591c/), [AN-22](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2aaa9d8e-0311-4bc3-9c77-d0b85eadfad8/), [AN-25](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cc831c6a-7861-4d31-b699-b2100a9db1cd/), [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/), [AN-31](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e5eeaaba-18a4-49ce-aba3-8d7a2cd11ae4/), [AN-34](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/ce8e376a-3f05-4788-8080-9715353d5994/), [AN-36](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cbf7c3bc-3ecf-465c-82cd-79dead9ce3ea/), [AN-53](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56387dba-c9fd-44e7-82cd-0e91800f7ef9/), [AN-54](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56720c94-6a3a-48bc-8a42-4c382e90836b/) |
| 10 | [AN-21](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3f765e57-ccca-4f1c-b095-a69d2ee8440c/), [AN-37](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/362e1e32-9a64-489e-958c-834c70fa9e7f/), [AN-38](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a32beb4e-1c80-4fcf-8a8f-dff24754eafa/), [AN-43](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/f376a9bc-23db-4c34-94ee-e36510fdf494/) |
| 11 | [AN-27](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/8f765bc9-70b9-4436-a40b-06db4409e832/), [AN-34](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/ce8e376a-3f05-4788-8080-9715353d5994/), [AN-47](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/96f2aac1-52b8-465c-8bd9-a4666dc64e55/), [AN-54](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56720c94-6a3a-48bc-8a42-4c382e90836b/), [AN-55](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/648ac50a-57dd-4697-b241-7f9d68a6f399/), [AN-56](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e35a45e1-df2c-46d1-aad8-25b678d735b3/) |
| 12 | [AN-42](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/7b7ec1eb-0f5c-4415-98af-5d1d9a2bdcea/) |
| 13 | [AN-18](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5d1f5591-1af5-497b-aa3a-633ae6cb591c/), [AN-19](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/737877ea-91c6-4cc2-b1ab-31508dc47238/), [AN-20](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/4baf9a5e-3df7-439d-8241-5733a83debac/), [AN-23](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5bacc4af-edae-4ce4-a872-641c0d6d6bff/), [AN-24](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/b0df579f-b4f5-499b-b10b-3e2e1534d9ec/), [AN-30](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6d9c59dd-f04a-4546-8e92-7bb8986c70e2/), [AN-32](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/17ccdecf-e02f-44a1-82a9-949fe6d64f46/), [AN-36](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cbf7c3bc-3ecf-465c-82cd-79dead9ce3ea/), [AN-42](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/7b7ec1eb-0f5c-4415-98af-5d1d9a2bdcea/), [AN-46](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0964fcf9-2c76-460b-a6b6-b60b10ebedb9/), [AN-47](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/96f2aac1-52b8-465c-8bd9-a4666dc64e55/), [AN-53](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56387dba-c9fd-44e7-82cd-0e91800f7ef9/), [AN-54](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56720c94-6a3a-48bc-8a42-4c382e90836b/), [AN-56](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e35a45e1-df2c-46d1-aad8-25b678d735b3/) |
| 14 | [AN-19](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/737877ea-91c6-4cc2-b1ab-31508dc47238/), [AN-20](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/4baf9a5e-3df7-439d-8241-5733a83debac/), [AN-23](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5bacc4af-edae-4ce4-a872-641c0d6d6bff/), [AN-24](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/b0df579f-b4f5-499b-b10b-3e2e1534d9ec/), [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/), [AN-29](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e7bd0945-6404-4126-a8a7-90111e94fed6/), [AN-41](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/231fb9b3-f101-481c-8fce-1f3f90cb8165/), [AN-42](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/7b7ec1eb-0f5c-4415-98af-5d1d9a2bdcea/) |
| 15 | [AN-37](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/362e1e32-9a64-489e-958c-834c70fa9e7f/), [AN-38](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a32beb4e-1c80-4fcf-8a8f-dff24754eafa/) |
| 16 | [AN-57](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/d1d913c7-0cc1-4965-9daf-5a419d43b978/), [AN-58](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cb2d3218-8ad6-4826-9ce5-9c69e7da693d/) |
| 17 | [AN-40](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a68016fe-d1f3-4340-a422-38b296732b55/), [AN-41](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/231fb9b3-f101-481c-8fce-1f3f90cb8165/), [AN-54](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56720c94-6a3a-48bc-8a42-4c382e90836b/), [AN-55](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/648ac50a-57dd-4697-b241-7f9d68a6f399/) |
| 18 | [AN-43](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/f376a9bc-23db-4c34-94ee-e36510fdf494/), [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/), [AN-47](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/96f2aac1-52b8-465c-8bd9-a4666dc64e55/) |
| 19 | [AN-23](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5bacc4af-edae-4ce4-a872-641c0d6d6bff/), [AN-32](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/17ccdecf-e02f-44a1-82a9-949fe6d64f46/), [AN-39](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0899b5fc-de2b-4f74-bfaf-890e02c6da54/), [AN-42](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/7b7ec1eb-0f5c-4415-98af-5d1d9a2bdcea/), [AN-46](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0964fcf9-2c76-460b-a6b6-b60b10ebedb9/) |
| 20 | [AN-30](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6d9c59dd-f04a-4546-8e92-7bb8986c70e2/), [AN-32](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/17ccdecf-e02f-44a1-82a9-949fe6d64f46/), [AN-33](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/dd441efc-ed43-4a34-a4e3-904b0be1ebd0/), [AN-34](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/ce8e376a-3f05-4788-8080-9715353d5994/), [AN-36](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cbf7c3bc-3ecf-465c-82cd-79dead9ce3ea/), [AN-40](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a68016fe-d1f3-4340-a422-38b296732b55/), [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/), [AN-46](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0964fcf9-2c76-460b-a6b6-b60b10ebedb9/), [AN-53](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56387dba-c9fd-44e7-82cd-0e91800f7ef9/) |
| 21 | [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/), [AN-32](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/17ccdecf-e02f-44a1-82a9-949fe6d64f46/), [AN-39](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0899b5fc-de2b-4f74-bfaf-890e02c6da54/), [AN-42](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/7b7ec1eb-0f5c-4415-98af-5d1d9a2bdcea/), [AN-46](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0964fcf9-2c76-460b-a6b6-b60b10ebedb9/) |
| 22 | [AN-50](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2a5876cd-421d-4d86-9c4e-2a46c599578a/), [AN-51](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2f168877-3fd7-4fe3-a94b-152e423656e2/), [AN-52](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/be386efb-4cb7-40e9-8283-8cfdcfe09f57/) |
| 23 | [AN-38](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a32beb4e-1c80-4fcf-8a8f-dff24754eafa/), [AN-48](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/88fe7dfb-8d7c-4aa3-8b51-e877c68c4cf7/), [AN-50](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2a5876cd-421d-4d86-9c4e-2a46c599578a/), [AN-52](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/be386efb-4cb7-40e9-8283-8cfdcfe09f57/) |
| 24 | [AN-29](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e7bd0945-6404-4126-a8a7-90111e94fed6/), [AN-39](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0899b5fc-de2b-4f74-bfaf-890e02c6da54/), [AN-43](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/f376a9bc-23db-4c34-94ee-e36510fdf494/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/) |

| UX scenario | Delivery records |
| --- | --- |
| UX-01 | [AN-21](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3f765e57-ccca-4f1c-b095-a69d2ee8440c/), [AN-37](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/362e1e32-9a64-489e-958c-834c70fa9e7f/) |
| UX-02 | [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/), [AN-43](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/f376a9bc-23db-4c34-94ee-e36510fdf494/) |
| UX-03 | [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/) |
| UX-04 | [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/) |
| UX-05 | [AN-37](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/362e1e32-9a64-489e-958c-834c70fa9e7f/), [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/) |
| UX-06 | [AN-39](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0899b5fc-de2b-4f74-bfaf-890e02c6da54/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/) |
| UX-07 | [AN-29](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e7bd0945-6404-4126-a8a7-90111e94fed6/), [AN-39](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0899b5fc-de2b-4f74-bfaf-890e02c6da54/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/) |
| UX-08 | [AN-29](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e7bd0945-6404-4126-a8a7-90111e94fed6/), [AN-31](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e5eeaaba-18a4-49ce-aba3-8d7a2cd11ae4/), [AN-39](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0899b5fc-de2b-4f74-bfaf-890e02c6da54/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/) |
| UX-09 | [AN-29](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e7bd0945-6404-4126-a8a7-90111e94fed6/), [AN-41](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/231fb9b3-f101-481c-8fce-1f3f90cb8165/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/), [AN-53](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56387dba-c9fd-44e7-82cd-0e91800f7ef9/) |
| UX-10 | [AN-30](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6d9c59dd-f04a-4546-8e92-7bb8986c70e2/), [AN-31](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e5eeaaba-18a4-49ce-aba3-8d7a2cd11ae4/), [AN-40](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a68016fe-d1f3-4340-a422-38b296732b55/), [AN-53](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56387dba-c9fd-44e7-82cd-0e91800f7ef9/) |
| UX-11 | [AN-25](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cc831c6a-7861-4d31-b699-b2100a9db1cd/), [AN-40](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a68016fe-d1f3-4340-a422-38b296732b55/), [AN-41](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/231fb9b3-f101-481c-8fce-1f3f90cb8165/), [AN-47](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/96f2aac1-52b8-465c-8bd9-a4666dc64e55/) |
| UX-12 | [AN-30](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6d9c59dd-f04a-4546-8e92-7bb8986c70e2/), [AN-33](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/dd441efc-ed43-4a34-a4e3-904b0be1ebd0/), [AN-36](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cbf7c3bc-3ecf-465c-82cd-79dead9ce3ea/), [AN-40](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a68016fe-d1f3-4340-a422-38b296732b55/), [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/), [AN-46](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0964fcf9-2c76-460b-a6b6-b60b10ebedb9/), [AN-53](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56387dba-c9fd-44e7-82cd-0e91800f7ef9/) |
| UX-13 | [AN-28](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/5b3d90e8-9b5c-4474-b32b-ac1153d5dcc0/), [AN-34](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/ce8e376a-3f05-4788-8080-9715353d5994/), [AN-46](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0964fcf9-2c76-460b-a6b6-b60b10ebedb9/), [AN-53](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56387dba-c9fd-44e7-82cd-0e91800f7ef9/), [AN-56](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/e35a45e1-df2c-46d1-aad8-25b678d735b3/) |
| UX-14 | [AN-35](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/22692c3e-b55f-4f3e-bea1-def47ccf1ef4/), [AN-44](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3c86132f-d09d-46ea-98a2-175a04fbeed3/) |
| UX-15 | [AN-38](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/a32beb4e-1c80-4fcf-8a8f-dff24754eafa/), [AN-48](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/88fe7dfb-8d7c-4aa3-8b51-e877c68c4cf7/), [AN-50](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2a5876cd-421d-4d86-9c4e-2a46c599578a/), [AN-52](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/be386efb-4cb7-40e9-8283-8cfdcfe09f57/) |
| UX-16 | [AN-50](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2a5876cd-421d-4d86-9c4e-2a46c599578a/), [AN-51](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/2f168877-3fd7-4fe3-a94b-152e423656e2/), [AN-52](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/be386efb-4cb7-40e9-8283-8cfdcfe09f57/) |
| UX-17 | [AN-42](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/7b7ec1eb-0f5c-4415-98af-5d1d9a2bdcea/), [AN-46](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/0964fcf9-2c76-460b-a6b6-b60b10ebedb9/) |
| UX-18 | [AN-43](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/f376a9bc-23db-4c34-94ee-e36510fdf494/), [AN-45](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/29c7b2a2-5075-42c2-bfeb-8dff1f140fca/) |
| UX-19 | [AN-49](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6ad8a1b8-6881-442c-856c-179ef203f5b9/) |
| UX-20 | [AN-21](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/3f765e57-ccca-4f1c-b095-a69d2ee8440c/), [AN-27](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/8f765bc9-70b9-4436-a40b-06db4409e832/), [AN-36](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/cbf7c3bc-3ecf-465c-82cd-79dead9ce3ea/), [AN-47](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/96f2aac1-52b8-465c-8bd9-a4666dc64e55/), [AN-48](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/88fe7dfb-8d7c-4aa3-8b51-e877c68c4cf7/), [AN-49](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/6ad8a1b8-6881-442c-856c-179ef203f5b9/), [AN-53](http://localhost:19230/agent-native/projects/0f39f541-5ef4-4a7f-8cdd-6a9a57ee0897/issues/56387dba-c9fd-44e7-82cd-0e91800f7ef9/) |

## Historical execution-audit handoff

AN-17's [Hermes source audit](hermes-execution-audit.md) pins the inspected baseline,
complete fork delta and license records, and distinguishes integrated operations
from native paths still requiring enforcement. It closes discovery, not M0's live
integration gate. At that audit handoff, AN-24 was next in sequence 3;
accepted AN-61/62 decisions supply its policy. The audit assigns admission,
tool/context assembly, stopping, events and real-run proof to existing AN-7/26/30/
32/18/57 records. AN-23 remains independently ready; AN-70 runtime configuration
remains open. That audit update introduced no new items or dates. Current writer
implementation starts at AN-72 as described above; AN-24 retains its partial evidence.

## Purpose-based lifespan follow-through

The latest owner clarification is reflected in the existing scenarios rather than
adding parallel scenario IDs. AN-64 records the accepted policy; AN-68 separates
unresolved retention/export/deletion/transfer details from core lifecycle behavior.
AN-69 is an M2 implementation item under AN-11 and a dependency of root gate AN-12.
It covers evidence-based continued need, growth versus recurring operation,
legitimate waiting, uncertain relevance and controlled self-retirement. AN-9 supplies
applicable result acceptance; AN-24 and AN-30 supply authority and actual stopping.
M3 applies the same rules to recursive children and parent accountability.

| Updated scope | Plane work |
| --- | --- |
| Purpose evaluation, retirement evidence and rejected stale assessments (product 2, 5, 15, 17, 23; UX-11/15) | AN-69, AN-9, AN-11, AN-12, AN-37, AN-40 |
| Cancellation pauses the performing agent/subtree and preserves independent assignments (product 8; UX-10) | AN-30, AN-40, AN-47 |
| Planning and instructions distinguish growth, operation, waiting and completion (product 1, 2, 7, 15; UX-14) | AN-26, AN-35, AN-69 |
| Purpose/outcomes/obligations replace the mandatory lifetime selector; expose evaluation and reason (UX-01/11/15) | AN-37, AN-47, AN-69 |

At the time of that lifespan update, these changes refined the roadmap without
adding work to the selected near-term cycles or claiming implementation evidence.
The later First Builder priority update reorganizes those cycles. Live item links and states
are available through the project board; this table is a coverage index.

## Decision and evidence boundaries

The original nine chapter-07 choices have decision items. AN-60–62 were subsequently
approved by the owner; see the [decision record](../design/07-open-decisions.md#resolved-autonomy-and-permissions).
AN-63 was then approved. The owner's latest revision resolves AN-64 with
purpose-based lifespan and cancellation pause; it supersedes the earlier
completion-by-role default. See [the current lifecycle decision](../design/07-open-decisions.md#resolved-purpose-based-lifespan-cancellation-and-replacement).
AN-68 separately tracks retained-work operations. Six decisions remain open:
AN-59, AN-65, AN-66, AN-67, AN-68 and AN-70. AN-70 now covers first-writer
and subsequent Builder runtime configuration separately from broad capacity/progress
defaults. AN-66 and AN-70 move forward for the writer; AN-65 governs later project/descendant controls. They gate only behavior needing that choice;
record export/deletion and new transfer behavior do not block ordinary retirement
with retained records. Creating an item does not approve its proposal.
Parent notification after direct human direction is part of the accepted
handoff decision. Required immediate stopping is already settled and is part of
the first root, not deferred to team replacement.

Manual-only agents, execution replay/branching and multiple owner chat channels
remain outside the initial release unless explicitly selected. No migration of the
abandoned prototype, OpenCode coupling, new provider SDK or independent task store
was added to the roadmap.

Existing evidence remains linked: identity/creation/provisioning/sandbox commits,
Astra screenshot-reading proof, accepted Plane setup/API characterization, and
partial AN-3 storage recovery. None makes the unfinished M0/M1 or autonomous-root
gates complete. The M2 root acceptance also requires the live engine boundary proof.

The owner explicitly requested removal of the `agent-native` demo project. Its
identity and seven Plane onboarding samples were verified, then the project was
deleted through the owner API and returned 404 on read-back. The Agent Native
Framework project is the retained planning home.

## Verification of the original planning import

Read-back verified all 67 unique items, including the 51 additions, original accepted
states, source references and parent links. Every item belongs to exactly its
intended module; the three cycle selections match their briefs. Native dependency
links were verified and the graph remains acyclic including parent completion.
Owner-session Playwright Chromium checks passed for modules, future cycles, the
current scoped-read item and policy-decision work. Documentation links and all
44 scenario rows were checked. These checks validate planning records and their
presentation, not completion of the scheduled product features.

## Scoped-read acceptance update

[AN-19 validation](plane-scoped-reads.md) records the trusted-host read boundary,
122 passing focused tests and the isolated live Plane proof. AN-19 is accepted;
AN-20 scoped writes is the next ready slice in sequence 2, followed by AN-22 retry
recovery. AN-3 remains blocked on that evidence and was explicitly carried from
sequence 1 into sequence 2. Native cycle membership and item states were read back;
sequence 1 retains three accepted items, and all cycles remain undated. This update
does not establish managed run authentication, agent activation or M1 completion.

## First Builder priority update

The owner moved the managed Builder with persistent chat to the first major
milestone. The existing M7 module now appears first and aggregates 39 records while
preserving their original capability memberships. AN-16 is the acceptance gate;
AN-57 connects the protected Builder run and AN-58 proves real TDD development,
owner steering and independent continuation. The first handoff reuses one existing
Plane project and one configured model; general onboarding and model switching
remain AN-21/AN-27 after it.

AN-70 records the still-open first Builder runtime-limit decision. Broader capacity
and progress thresholds remain AN-67. Root timing AN-66 remains on the early path;
AN-65 gates the later descendant/project-pause extension, with root resume in AN-31.
These changes set priority and scope; they do not approve unresolved defaults.

Readback verified 70 unique work items, 39 updated existing items with their states
preserved, 14 revised dependency sets, six exact undated cycle memberships and
preserved original module memberships. The graph including aggregate completion
remains acyclic; the first handoff has no prerequisite in deferred teams, complete
UI, multi-model switching or broad operation hardening. At that planning update AN-20 was the next
implementation slice in sequence 2; the acceptance update below supersedes it. The completed first cycle and accepted evidence
remain intact. Documentation checks preserve all 24 product and 20 UX mappings.


## Scoped-write acceptance update

[AN-20 validation](plane-scoped-writes.md) records 340 passing focused checks and
the isolated live Plane proof for ten scoped planning operations. AN-20 is now
accepted and AN-22 is the next ready item in sequence 2. AN-3 remains Blocked until
uncertain-write/retry recovery is verified; the passing storage restore evidence
is preserved. This acceptance covers the trusted-host adapter, schemas and
receipts. Managed-run authentication, execution, source reconciliation and the
first Builder handoff remain separate work. Cycles remain ordered and undated.


## Recovery acceptance and sequence-3 carry review

[AN-22 evidence](plane-write-recovery.md) records 452 passing regressions and the
isolated live ten-operation recovery proof with zero resends and verified cleanup.
AN-22 and the bounded existing-Builder AN-3 recovery scope are accepted; prior
storage evidence remains in [the AN-3 report](plane-recovery-validation.md).
General new-project/workspace creation recovery is explicitly retained in AN-21.

AN-4 carries unfinished from sequence 2 to sequence 3: host adapters do not prove
run-derived authority or skill/tool transport. It now explicitly requires AN-7
and AN-26, retaining AN-2 and child acceptance. AN-5 instead requires the accepted
host boundary AN-20, preserving AN-22/23 and all source-freshness requirements.
AN-7 still requires AN-5. This removes the aggregate/runtime dependency deadlock
without dropping the freshness gate. AN-17 is Todo and next; AN-70 remains open.

Readback confirmed AN-3/22 Done, AN-17 Todo, other states unchanged, sequence 2
containing AN-3/20/22, sequence 3 with carried AN-4, and all six cycles undated.
These planning outcomes do not establish a managed run or autonomous handoff.
