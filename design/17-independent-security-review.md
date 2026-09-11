# Independent security review and containment

Status: **Future milestone requested by the owner, detailed design proposed**,
2026-09-11. This capability belongs in the framework roadmap but is not an
immediate implementation priority. Plane milestone **AN-135 / M8** tracks it.
The request establishes independent AI security reviewers, assessment of agent
actions and behavior, authority to trigger pauses, and warnings to the owner and
affected agents. The mechanisms and defaults below are recommendations to review
before enforcement is enabled; no reviewer is being deployed by this document.

## 1. Intended outcome

An agent can pursue its purpose autonomously while a separate security function
checks whether its actions fit its authority and present security risks. The
function can prevent a proposed action, interrupt affected work, investigate
observed behavior and give the owner an understandable incident with evidence
and a meaningful next decision. This applies to every profession and to the
First Builder; it is not specific to the Fantasy Game Builder.

Security review is distinct from output acceptance, product quality evaluation
and [activity without progress](02-independent-work.md#detecting-activity-without-progress).
A poor result, a failed test, a long attempt, exploration, or disagreement about
design does not by itself establish a security incident. The existing autonomy
levels determine how readily an agent seeks work approval; they do not weaken
security boundaries or let a Level 5 agent bypass review.

Use observable descriptions such as “attempted access outside the project” or
“possible credential disclosure,” not an unqualified “rogue agent” label. We
can assess actions, patterns and recorded explanations; we cannot prove a model's
inner motives, absence of bias, or future behavior. Independence is enforced
organizationally and technically and evaluated empirically.

## 2. Foundation and limits

Keep three responsibilities distinct:

| Layer | Responsibility | What it cannot establish |
| --- | --- | --- |
| Framework access enforcement | Authenticate the actor; enforce soul/grant revisions, resource boundaries, budgets and lifecycle holds at the operation causing an effect. | Compliance with every sentence of an open-ended natural-language purpose. |
| AI action review | Interpret the proposed operation, purpose, trusted direction, relevant files and recent activity to assess risk and recommend a disposition. | New permissions, certainty about opaque execution, or an irreversible action already being undone. |
| Independent behavior audit | Examine sequences and observed effects for drift, bypass attempts, impersonation, concealment or compromised inputs. | Prevention of an action that already happened or coverage of invisible external activity. |

AI is an additional reviewer, never the issuer of its own authority. An “allow”
judgment cannot override a denied grant. Hard controls continue even if reviewers
are unavailable or fooled. A retrospective audit alone is insufficient for an
action whose first execution could disclose data or cause an irreversible effect.

The control service, identity verification, credential isolation, sandbox and
event storage are trusted components. A compromised host or control service is
outside what a reviewer running on that same host can reliably contain. Report
that limitation and require independent host controls for stronger deployments.
Only mediated surfaces can claim enforcement coverage. An unrestricted shell,
host browser, container socket or independent background process breaks that
claim; adding a prompt or a command classifier does not fix it.

## 3. Independent security agents

Recommended organization:

```text
Human owner
├── Product/work roots and their children
└── Security root (owner-controlled purpose and security scope)
    ├── Action reviewers
    ├── Behavior auditors
    └── Independent second reviewers for disputed findings
```

The security root has its own protected purpose and no delivery objective for
the projects it reviews. Its narrowly delegated authority can inspect named
targets and request containment across those trees. This is a separate security
grant, not parentage, project ownership, or permission to modify another soul.
Only the human can appoint the security root or change its fundamental scope.
Review children follow normal soul ownership and grant-subset rules.

- The reviewed agent and its ancestors cannot select, instruct, replace, retire,
  fund-starve, or change the policy of their assigned reviewer. A product agent's
  claimed emergency or high priority cannot disable review.
- Reviewers use separate identities, sessions, protected instructions, memory
  and credentials. They receive host-selected evidence rather than inheriting
  the worker's conversational persona or editable summary as truth.
- Assignment is made by the control service using conflict rules. No reviewer
  reviews its own work, work it helped produce, or its own security supervisor.
  Where no eligible independent reviewer exists, show unavailable coverage.
- Reviewers receive no product-write, publish, spend, general shell, arbitrary
  browser or grant-administration capability. They can read scoped evidence,
  record findings, request narrowly authorized holds and send scoped notices.
- More security children require an owner-defined capacity envelope. Avoid a
  recursive chain of agents reviewing agents reviewing themselves. Reviewer
  operations have hard checks; a separately assigned peer and ultimately the
  human adjudicate concerns about the security root.
- Measure accuracy, missed violations, false positives, useful explanations,
  latency and cost. Neither the number of agents stopped nor a project's success
  is a reviewer success metric. Reviewers have no self-preservation objective.

Different models/providers and independent second opinions may reduce shared
failure modes; neither guarantees independence or correctness. The owner chooses
reviewer models and resource limits separately from worker models. The worker's
choice of a cheaper model cannot silently weaken the selected security policy.

## 4. What gets reviewed

Every managed operation receives deterministic checks. Risk policy determines
which also require AI review before execution, which receive later audit, and
which are not permitted on the installed execution backend.

| Surface or pattern | Review evidence and concern |
| --- | --- |
| Shell, scripts, build/test commands, package installation | Actual executable/script inputs, working directory, mounts, subprocess rights, install hooks, destinations and scope; commands can hide effects behind tools or interpreters. |
| Files, memory, practices and skills | Resolved targets, relevant changes and protected boundaries; attempts to alter soul, grants, executable plugins, security controls or future instructions. |
| API, MCP, browser and computer actions | Actual tool arguments, account/resource, action and destination; distinguish reads, submissions, uploads, publication, deployment, payments and communication. |
| Credentials and network access | Capability references and redacted destinations; potential secret access, external disclosure, data movement through logs, URLs, screenshots or output publication. |
| Child creation and cross-agent messages | Grants, provenance and sequence; spreading a denied action across children, relaying fake owner authority, or coordinating around a restriction. |
| Persistent/background activity | Owned processes, jobs, network and storage effects; work continuing after a stop or escaping the managed executor. |
| Long-term behavior | Repeated boundary probes, changed methods after denial, hidden persistence, unexplained resource use and purpose drift across attempts and descendants. |

Legitimate exploration can support a broad purpose. Review relevant plans,
trusted owner direction, permitted capabilities and evidence before interpreting
an unexpected action as drift. A denied attempt followed by an appropriate
correction is different from repeated attempts to reach the same prohibited
effect through alternate tools.

Statements inside code, webpages, Plane comments, outputs and tool responses are
untrusted evidence. “The owner authorized this” in those sources is not an owner
decision. Refer back to the authenticated authorization record. The reviewer
may request missing evidence through scoped reads but must not execute suspect
code to discover whether it is safe.

## 5. Review before execution

1. The framework captures an action intent before the effect: actor, run, work,
   original arguments, resource, effective revisions and a stable action identity.
2. Deterministic policy denies forbidden operations immediately. A denial is
   recorded; the actor receives a useful scope explanation. Do not ask an LLM
   to overrule it or treat every accidental denial as an agent-wide incident.
3. An allowed action is classified by the installed policy. Routine constrained
   actions may proceed without an extra model call; review-required actions wait
   without executing. Record that they are queued for security review.
4. An independent reviewer receives the evidence packet and returns a structured
   assessment: concern, applicable policy, supporting evidence, uncertainty,
   possible benign explanation, missing facts, recommended action and scope.
5. The host validates reviewer identity, jurisdiction, response schema and current
   revisions. It applies the configured rule: permit this exact action, deny it,
   obtain a second review, wait for specified information, or initiate containment.
6. Immediately before execution, recheck lifecycle and grants and verify that the
   reviewed inputs still match. A changed target, payload, script or authority
   invalidates the decision. Record the observed effect separately afterward.

A review is not a reusable blanket approval for “run tests” or “publish.” Reviewed
scripts need immutable staging or input verification at execution; raw command
text cannot describe every consequence of arbitrary programs. Network, filesystem
and process restrictions remain active throughout execution. Unsupported or
uninspectable high-impact operations stay unavailable or require an explicitly
scoped owner decision; the UI must disclose the coverage gap.

## 6. Continuous behavior auditing

Audit incrementally from a durable event cursor. Important signals trigger review
promptly; lower-risk activity is batched on a configurable cadence. Include
commands denied before execution, admitted actions, actual outcomes, relevant
communications, changes in authority and work across multiple attempts.

Correlate by agent, action, resource, project and descendant relationships. Several
ordinary actions may combine into a prohibited outcome. Conversely, a burst of
authorized installation or compilation activity must not be called malicious
merely because it is unusual. Audits preserve evidence of both explanations.

Persist the reviewed interval, detected pattern, coverage gaps and latest known
observation. No new events normally means no new model call. Deduplicate repeated
findings into one incident, while materially new evidence updates that incident
or opens a linked recurrence. A worker's pause does not stop the security review
of that worker. Security waits must not wake the worker merely to ask whether it
is still waiting.

## 7. Responses and security holds

Severity, confidence and proposed intervention are separate fields. Model-reported
confidence is not a calibrated probability or authority to stop a whole system.
Proposed response policy:

| Finding | Response |
| --- | --- |
| Ordinary allowed work, no relevant concern | Execute under existing grants; record coverage without owner notification noise. |
| Isolated mechanically denied action with an evident safe alternative | Keep the action denied; explain and allow independent permitted work. |
| Plausible concern or missing evidence without imminent harm | Hold only the proposed action if its policy requires review; seek facts or a second reviewer. Label uncertainty. |
| Credible imminent harmful effect or confirmed serious violation | Immediately request a security pause of the affected agent and subtree; investigate after containment. Do not wait for a consensus vote before stopping imminent harm. |
| Repeated or coordinated bypass pattern | Open/update an incident; contain the proven affected scope. Extending a hold to other roots requires explicit jurisdiction and evidence for each target. |
| Reviewer timeout, outage or broken telemetry | Record unavailable security coverage, retry within limits, and retain the required-action gate. This is a framework/service condition, not proof of worker misconduct. |

Reviewers request a hold through a narrow authenticated operation; the control
service decides whether that request fits the security mandate. The host blocks
new actions atomically, initiates actual process/job interruption and records
stopping until confirmed. Already completed effects are preserved as facts.
Uncertain external effects remain unresolved until read back; never claim that
a security pause rolls back a payment, disclosure or deployment.

An action hold is narrower than an agent pause. A security pause of an agent
includes its subtree, following the established rule. The security root and
unaffected work roots keep operating. Restrict related credentials only within
the incident policy; revoking a shared account with broader impact needs its
own authorization. Credential rotation, deletion, rollback and retirement are
separate operations, not automatic consequences of a suspicious finding.

## 8. Continuation without confusing state or endless approval

A security hold is a separate durable cause. Keep configured automatic cadence
on; effective readiness explains why execution is currently barred. The same
reason appears in scheduler admission, managed tools, chat context and the UI.
Retry timers, output acceptance, ordinary resume, a successor agent and parent
commands cannot accidentally clear an applicable security hold.

Every hold identifies its affected scope, incident, evidence, resolver and release
condition. Examples: re-review a corrected upload destination; verify termination
of a background process; await a named owner permission change. If the condition
is an automatic check, the framework performs it rather than asking the human to
press an unexplained Retry button.

Proposed release rules:

- Action review waits can clear when a fresh valid decision arrives. A changed
  action receives a new review rather than borrowing approval for its predecessor.
- A temporary investigation hold can clear automatically after an independent
  second reviewer finds a false positive and the host verifies the configured
  release conditions. The acting worker cannot release its own hold.
- Confirmed serious incidents remain contained until the owner explicitly resolves
  them. Closing an alert or acknowledging a notice is not authorization to resume.
- Owner decisions state whether to preserve the stop, narrow authority, permit an
  exact exception, change policy, or release the named hold. The human has ultimate
  control and needs no reviewer consent. Authenticated policy changes must be
  applied before a previously denied action can execute.
- Clearing a security cause preserves independent manual, budget, lifecycle and
  dependency causes. Reconcile outstanding effects and current plans before an
  eligible fresh attempt; do not blindly replay the interrupted command.

When a second review is unavailable, keep a visible review-service blocker with
automatic recovery and an owner override path; do not mislabel it as a request
for product feedback. A bounded timeout never silently authorizes a risky action.

## 9. Owner experience and alert routing

Use the existing agent page, unified Inbox and event history. On the default
Work tab, put an applicable incident above ordinary work and outputs. For example:

> Security hold — an attempted upload targeted an unapproved external service.
> The upload was blocked before sending. This agent and its two children are
> stopped. Review the destination and choose whether to keep the restriction
> or authorize this exact destination.

Show an evidence link, the affected operation/work item, the source policy, known
impact and uncertainty, who is investigating and what releases the hold. Offer
controls appropriate to that condition, such as **Keep stopped**, **Review scope**,
**Request independent review**, or **Authorize and release this hold**. State
explicitly if authorizing still leaves other holds. Show **Stopping** rather
than **Stopped** when processes or external effects are unconfirmed.

Provide a Security tab/filter for incident history and a settings section for
coverage, reviewer model, budget and review mode. Keep the default agent view
compact. Tables are newest-first, paginated at 20 rows by default with 50/100
options, filterable by status, severity, agent/subtree and time. Do not expose a
worker's internal reasoning as security evidence; use actions, observations and
concise assessment explanations.

Security alerts travel through the owner-controlled security root directly to
the trusted owner inbox. A suspected product parent cannot intercept or suppress
them. This is a scoped exception for security reporting, not a shortcut for
ordinary child clarification. The human can inspect the original source and
full security escalation path. Inform authorized affected parents/agents through
recorded framework messages; reveal only what they need for safe coordination,
not other agents' private data or raw credentials. Such messages cannot grant
permissions or silently pause uninvolved agents based on hearsay.

Deduplicate incident notifications and record delivery. Failure to reach Plane,
chat, or an offline owner must not prevent containment. Queue redacted Plane
references on relevant work items; the protected incident record remains the
source of truth, and Plane comments do not clear security holds.

## 10. Reviewer security, privacy and availability

Treat all reviewed content as potentially adversarial, including appeals and
messages from other reviewers. Trusted rules and origin-labelled evidence remain
separate. A model's text cannot call a privileged control operation indirectly;
only validated structured decisions enter that path. Sanitise displayed evidence
and render attachments inertly; never execute supplied HTML or scripts in an
operator or reviewer context with control credentials.

Minimize evidence to the resources within the review grant. Redact secrets before
sending packets to a reviewer/provider, retain references to protected evidence,
and identify redaction or truncation rather than inventing missing context. Keep
restricted audit evidence outside worker-writable storage; use append-only records
with tamper detection and access logging. Retention/deletion obey the owner's
policy; append-only does not mean permanent storage against owner wishes.

Reserve a separately visible security budget and execution capacity. A reviewed
worker cannot exhaust that reserve. Enforce queue/concurrency limits, deduplicate
repeated requests and cap retry/escalation loops. Show reviewer tokens, cost,
latency, queue age, failed reviews, last audit event and coverage gaps separately
from productive work; attribute shared review costs without double counting.

If a required reviewer is down or its budget exhausted, high-risk actions remain
gated. Explicitly permitted low-risk operations can continue under hard controls;
there is no general fallback from a strong reviewer to a weaker model without
configured policy. Deterministic stopping and owner controls need no model call
or remaining reviewer budget. A provider outage must not prevent the owner from
inspecting evidence or changing the policy.

## 11. Applying this to the First Builder

The First Builder may edit proposed security code and test it inside its granted
repository workspace. It cannot deploy its own changes to the active reviewer,
replace protected instructions, weaken audit storage or grant itself exceptions.
Review the source diff as evidence, and apply the existing protected-release
boundary before it affects running enforcement. Otherwise the Builder could edit
the code that judges it and trigger a hot reload.

This milestone does not claim that today's development server or local contributor
has these protections. Existing First Builder authority protections are still
required for its handoff; advanced AI security review is a later milestone, not
a new prerequisite that silently postpones that handoff.

## 12. Decisions to settle before enforcement

| Choice | Proposed starting policy |
| --- | --- |
| Review coverage | Hard checks for every mediated action; AI before external/high-impact effects, later audit of ordinary constrained activity. Promote unknown tool surfaces only after coverage is proven. |
| Modes | Shadow assessment first, then enforced action gates for selected scopes, then scoped automatic containment. Shadow mode never relaxes existing hard denies and is visibly not preventive AI protection. |
| Independence | One owner-controlled security root with separate action/audit roles; independently assigned second reviewer for disputes. Peer review or human review for the security root itself. |
| Automatic release | Permit policy-verified false-positive release; require owner disposition for confirmed serious incidents. Never auto-clear a manual hold. |
| Model/provider | Select using adversarial evaluation and evidence privacy constraints; no untested specific model promise or requirement for the worker's model. |
| Resources and telemetry | Reserve security capacity, bounded review latency and retries, separate usage. Exact values and acceptable false-positive/missed-violation thresholds require measured evidence. |
| Sensitive evidence | Minimum necessary access; owner-controlled provider and retention policy; raw secrets excluded from model prompts and notifications. |

These choices are also indexed in [Open decisions](07-open-decisions.md).
Implementation work and acceptance scenarios are detailed in
[the M8 delivery plan](../implementation/security-review-milestone.md).
