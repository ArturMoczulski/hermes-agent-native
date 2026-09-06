# Workspaces and skills

## A place for organized work

Agents need durable workspaces that contain or provide access to project plans,
tasks, artifacts, relevant context, and pending decisions. An agent returning to
work must be able to discover the current state without asking the human to
reconstruct it.

The framework provides Plane as its shared planning application, following
[Project management with Plane](13-project-management.md). Work must remain
readable by agents and humans, with source-labelled file representations available
for framework concepts. Agent filesystem workspaces remain private execution areas.

Different views of the same work must agree on its current state. An agent should
not find one task marked complete in its notes and still active in the shared
workspace without a way to determine which record is authoritative.

Workspaces have access boundaries. Assignment to a task does not automatically
grant access to every other agent's memory, projects, or private information.
Agents receive the context and capabilities needed for their authorized work.

This boundary applies beyond project workspaces. By default, an agent has no
access to the human's personal files, machine controls, credentials, or another
agent's private information. Access to resources and the ability to act on them
must be explicitly granted and enforced by the framework. No particular
isolation technology is prescribed.

## Loadable skills

A skill teaches an agent how to perform a kind of work. Agents can be equipped
with skills relevant to their purpose and assignments. Skills can describe
methods, workflows, useful resources, and how to use available tools.

For example, an artist could have skills for composition, critique, and project
management. Different agents can use different methods while sharing the same
fundamental agent model.

Skills are separate from the soul. They help determine how to work; they cannot
redefine why the agent exists, change fundamental rules, or grant new authority.
A skill that describes publishing does not itself authorize publication.

## Project-management skills

The framework supplies skills that help agents:

- Turn a broad purpose into investigable questions and useful projects.
- Break outcomes into tasks, identify dependencies, and prioritize work.
- Assign work with enough context and clear completion expectations.
- Inspect progress before starting more work and find independent branches.
- Track questions and communicate blockers to the responsible party.
- Review results, revise plans, and preserve useful lessons.

The bundled [Plane project-management skill](../skills/productivity/plane-project-management/SKILL.md)
is the default for most substantive work, including the First Builder. Agents use
backlogs and small sprint-like planning cycles, with lighter handling for trivial
actions and rolling Kanban for continuous operations. Skills are provisioned and
loaded explicitly for managed planning sessions; merely storing this file does
not establish runtime loading or Plane access.

## Default capabilities

The initial root template supports ordinary work without a human-maintained prompt
queue: its private workspace, Plane project management, approved public research,
private drafts and results, and child creation within configured capacity limits.
The owner can configure these defaults and inspect what an agent receives.
Creating a root from a broad purpose does not grant additional access.

Child permissions are selected from the parent's delegable authority under
[the permission rules](05-human-interaction.md#applying-ownership-to-permissions).
Publishing, spending, contacting people and deployment follow the same chapter's
standing-permission or explicit-approval policy. Ordinary root defaults provide
no blanket access to the owner's personal files, credentials or computer controls.
Skills explain methods; they cannot add capabilities to this template.

## Capabilities and resources

Tools enable actions; skills explain how to use capabilities effectively. Access
to a tool remains subject to the agent's permissions and fundamental rules.
If a necessary capability is missing, the agent identifies the missing capability
and asks the responsible party or chooses a permitted alternative.

The framework must expose when work cannot proceed because resources or capacity
are unavailable. One waiting project must not automatically prevent independent
projects from progressing. The exact resource limits and allocation policies
are [open product decisions](07-open-decisions.md).
