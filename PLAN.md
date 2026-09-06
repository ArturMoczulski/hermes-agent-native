# Current implementation work

The owner selected the Hermes fork and Plane for project planning. The live
[First Builder Plane project](first-builder/PLANE.md) now owns the actionable
backlog, priorities, dependencies and cycles. Read its API state before choosing
work; do not maintain a parallel checklist here.

- Product requirements: [design/](design/README.md).
- Engineering milestones: [delivery plan](implementation/delivery-plan.md).
- Specification-to-work traceability: [Plane coverage](implementation/plane-roadmap-coverage.md).
- Plane integration: [implementation plan](implementation/plane-project-management.md).
- Session evidence and handoff: [Builder state](first-builder/STATE.md).
- Local service operations: [Plane deployment](ops/plane/README.md).

The first major milestone is the managed First Builder: it works in this repository
on its own cadence and communicates with the owner through persistent chat. The
full specification remains organized into M0–M7 capability modules and a product
decision module in Plane. M7 is the early handoff gate, not a requirement to finish
M3–M6 first. Existing AN-1–AN-16 retain their history; refined work covers the
remaining specification. Ordered, undated cycles select small increments: scoped
planning and recovery, a controlled Builder run, persistent chat and owner control,
autonomous continuity, then a real TDD improvement demonstrating the handoff.
Advance by accepted outcomes and dependencies; do not estimate cycle durations or
assign calendar windows.
Plane is the authority for item state; this overview is not a second task store.
The latest owner lifecycle decision replaces fixed agent lifetime categories with
[purpose evaluation](design/01-agents.md#lifetime-and-work-assignment); cancellation
pauses the performing agent/subtree. The roadmap must implement these rules in
the first autonomous root and then extend them to teams.

Completed identity, authenticated creation UI, private provisioning, restricted
Hermes environments and the scoped Plane read boundary are recorded in Git and
Builder state. They do not
yet establish autonomous managed agents.

The current planning increment remains AN-20, followed by AN-22 and the carried
AN-3 recovery acceptance. Existing Plane resources are reused for the Builder;
general onboarding and the complete multi-agent product follow the first handoff.
Use the live AN-16 milestone and AN-57/AN-58 execution/proof records for acceptance;
plan changes do not establish a deployed Builder.
