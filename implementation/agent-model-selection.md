# Persistent agent model selection

Owner priority: AN-27 in cycle 03, before AN-80. This implements
[model selection](../design/15-model-selection.md) using Hermes's existing picker,
configured connections, provider resolver and native worker loops.

## Storage and boundaries

Additive control tables hold the new-agent default, per-agent assignments,
immutable creation input, owner change events and per-attempt selections.
Provider/model and an independent revision are separate from the soul revision.
The initial default is copied from an explicitly configured Hermes profile pair;
an unconfigured profile stays visibly unconfigured. Before changing defaults,
pin legacy identities to their previous native setting.

The owner API supplies default read/edit, configured model options and per-agent
edit. Authentication uses the existing dashboard owner session. Creation accepts
an optional pair; replay checks its original input even after later edits.
Concurrent saves use expected configuration revisions.

Work snapshots the pair when queued work is admitted; chat snapshots it with an
accepted owner-message receipt. Workers resolve credentials for that selection
through native Hermes connections, with strict explicit provider routing and no
implicit fallback. Run/session identity and retained conversation stay intact.
Managed execution records its normalized model/provider after native construction;
the final request boundary rejects middleware substitutions before the SDK call,
including model overrides inside `extra_body`.

Work configuration validates a usable pair before allocating the initial attempt.
A missing model returns a useful 422 response and leaves work unconfigured. The
creation screen also prevents submitting with an unknown default; an explicit
configured override remains usable when the default cannot be loaded.

## Interface

The Agents page shows a default-model section and an optional creation override.
Agent details show the saved choice, edit controls, the work attempt selection
and recent chat selection. The native standalone model picker is reused; these
controls do not invoke Hermes's global main-model assignment endpoint. Existing
Hermes model/provider configuration remains the credential setup surface.

## Verification

Use the three named cases in `web/e2e/model-selection.spec.ts` and focused settings,
provider-resolution and admission tests. The existing external HTTP model fixture
supports two configured provider routes/model IDs, including held requests for
change-during-work/chat cases. No model API key, subscription inference or new
browser download is needed for these checks. Keep optional live model-quality
checks separate and explicitly configured; no live evaluation is required here.

Exact red/green evidence and current completion status live in
[Builder state](../first-builder/STATE.md) and Plane AN-27.
