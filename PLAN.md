# Current implementation work

The owner explicitly selected this Hermes fork and authorized its implementation
in the conversation. Product requirements remain in [design/](design/README.md).
Detailed milestone criteria remain in [implementation/](implementation/delivery-plan.md);
this list tracks completed increments rather than claiming whole milestones done.

- [x] Verify subscription inference and desktop screenshot reading through Hermes.
- [x] Fix one-shot computer approval waits; preserve default-deny behavior.
- [x] Persist inactive roots, purpose revisions and creation/revision events.
- [x] Add authenticated dashboard creation/listing with real-backend Playwright tests.
- [x] Add private profile/workspace provisioning and explicit data mount plans.
- [x] Verify purpose immutability and mutable storage with a real local container.
- [x] Integrate the mount plan with a restricted Hermes tool environment; prevent
  inherited credentials, mounts, environment, network or container reuse from
  broadening the managed agent's access.
- [x] Specify Plane planning and the default backlog/sprint skill for agents and Builder.
- [ ] Validate a pinned Plane Community release and its API/access boundaries; follow
  [the Plane integration sequence](implementation/plane-project-management.md).
- [ ] Provision the planning service and connect the Builder project/skill; reconcile
  bootstrap work once, without maintaining duplicate task boards.
- [ ] Bind that environment to durable run admission and the Hermes model loop,
  linking Plane work items according to the agreed source-of-truth boundary.
- [ ] Record provisioning/activation state and expose it through the owner UI.
- [ ] Add protected revision refresh and revalidation at admission.
- [ ] Connect initial planning, task persistence, pause/cancellation and cadence.

Managed agents remain not started. The real container test verifies its specific
mounts and execution flags; it does not certify Hermes' unmodified Docker backend.
