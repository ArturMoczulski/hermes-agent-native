# The First Builder and self-bootstrap

The framework is intended to build and develop itself through a persistent
**First Builder** agent. The First Builder is its architect and builder,
responsible for evolving the framework under the human owner's direction.
Running this agent inside the framework is an intended product outcome, not an
optional example.

## An explicit workspace exception

The First Builder's working area is the root of this repository. Its project
work and workspace state use that repository so it can inspect, change, verify,
and develop the framework itself. It has explicitly granted privileged access
needed for this responsibility instead of the ordinary isolated project workspace.

This is a named exception for framework development, not a reason to grant every
agent the same access. Repository access does not by itself mean unrestricted
access to the human's entire machine. The exact execution environment and
additional capabilities are implementation decisions.

The First Builder remains subject to human ownership, trusted communication,
soul protection from self-editing, and applicable permission requirements. It
must not use its ability to edit framework code to grant itself new authority.
The human can change its purpose and permissions as with any other agent.

## Bootstrap and eventual operation

The First Builder begins development through an external coding environment.
It already performs the Builder role at that stage; its actual tools, permissions
and execution lifetime come from that environment. The repository holds its
purpose, working instructions, memory and development state so the role can
continue across sessions.

Once the framework can support the role, the First Builder runs as one of its
persistent agents. It starts and maintains a development plan, acts on its
cadence, can delegate focused work, reports progress, and escalates unresolved
questions through its parent chain, or directly to the human when parentless. Its work and context persist across periods of activity.

Success is observable when the First Builder can perform a bounded framework
improvement from its repository workspace, verify the result, retain progress,
and accept human steering while running on the framework itself. The human does
not have to invoke each development step manually.

The maintained framework repository is also the First Builder's workspace.
Its [soul](../first-builder/SOUL.md) and [working instructions](../first-builder/INSTRUCTIONS.md)
define the current role. Detailed development conventions, including the owner's
test-driven workflow, belong in those implementation instructions.
