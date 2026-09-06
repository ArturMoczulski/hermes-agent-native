# The First Builder and self-bootstrap

The framework is intended to build and develop itself through a persistent
**First Builder** agent. The First Builder is its architect and builder,
responsible for evolving the framework under the human owner's direction.
Running this agent inside the framework, with direct owner chat, is the first
major delivery milestone. The owner should be able to continue developing the
framework through that agent instead of supplying each step in an external coding
conversation. The full recursive organization and complete control center follow
this handoff; they are not prerequisites for proving it.

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

## First major milestone: an autonomous Builder with chat

The first handoff supports one First Builder working in this repository under the
human's control. It uses its purpose, working instructions, memory and Plane plan
to select authorized work, perform it in small test-driven increments, evaluate
results, and decide whether to continue, wait or ask. It separately reviews its
whole purpose and continuing obligations; a completed work item alone does not
end its responsibility for developing the framework.

The owner has a persistent chat with this agent: read its progress and questions,
reply, redirect work, and explicitly stop or pause it. The conversation makes
current work, waiting and uncertain execution state visible. Human identity and
authority remain trusted even when agent output contains quoted instructions.
Closing the browser does not stop the agent, erase messages or require another
prompt to keep it working. Restarting the framework preserves its context and
reconciles interrupted work before continuing.

Success requires a real bounded framework improvement, driven by a demonstrated
failing test, implemented and verified by the hosted Builder, with evidence and
accepted results recorded in Plane. During that work the owner can converse with
and steer it. After inactivity and a service restart, the Builder retains progress
and takes the next clear authorized step without the human invoking each step.
It asks when direction or permission is missing and respects explicit pauses.

This first handoff can run without child delegation. Recursive teams, the complete
organization monitor and global decision inbox, advanced progress detection, and
broader deployment hardening remain required later capabilities. Basic questions,
result and purpose evaluation, observability, interruption, access enforcement,
soul protection and recovery belong in the handoff itself. The Builder's ability
to edit framework source must not change its running authority or authorize its
own deployment.

The milestone describes required evidence, not current runtime capability. The
Builder continues through its external coding environment until this handoff has
actually been demonstrated.

The maintained framework repository is also the First Builder's workspace.
Its [soul](../first-builder/SOUL.md) and [working instructions](../first-builder/INSTRUCTIONS.md)
define the current role. Detailed development conventions, including the owner's
test-driven workflow, belong in those implementation instructions.
