# Durable whole-purpose evaluation — AN-75

Each managed work review can record one or more immutable whole-purpose judgments
through `purpose_evaluate`. This record is separate from an assignment result, the
bounded attempt outcome, and owner acceptance.

The record binds the agent, run, protected purpose revision and purpose text to:

- a judgment: `continue`, `wait`, `clarify`, or `retire_candidate`;
- concise evidence supporting that judgment;
- all known remaining obligations;
- material uncertainty; and
- a concrete next action.

A retirement candidate cannot list remaining obligations. This validation does not
retire the agent yet; subtree review, unresolved effects, applicable acceptance and
the actual lifecycle operation remain later enforcement. Later attempts receive the
latest evaluations in their planning context. The compact agent view shows the newest
judgment, obligations, uncertainty and next action.

Purpose evaluation is meaningful progress for cadence-loop detection. It cannot be
used as empty status churn: the record is explicit evidence and a lifecycle decision,
while semantic repetition across otherwise valid records remains future AN-51 work.
`clarify` must reference an applicable unanswered framework question. While that
question remains unanswered, cadence stays enabled but does not queue redundant work
attempts. A trusted owner answer makes the next cadence review immediately eligible;
it never resumes an owner-paused agent. `wait` leaves the ordinary configured cadence
in place so the agent can review the dependency or continuing service later.
