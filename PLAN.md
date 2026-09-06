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

The full specification is organized into M0–M7 milestone modules and a product
decision module in Plane. Existing AN-1–AN-16 retain their history; refined work
items cover the remaining specification. Three ordered, undated cycles select
small increments. Advance by accepted outcomes and dependencies; do not estimate
cycle durations or assign calendar windows.
Plane is the authority for item state; this overview is not a second task store.
The latest owner lifecycle decision replaces fixed agent lifetime categories with
[purpose evaluation](design/01-agents.md#lifetime-and-work-assignment); cancellation
pauses the performing agent/subtree. The roadmap must implement these rules in
the first autonomous root and then extend them to teams.

Completed identity, authenticated creation UI, private provisioning and restricted
Hermes environment increments are recorded in Git and Builder state. They do not
yet establish autonomous managed agents.
