# Agent storage topology

This document maps the product areas in
[Workspaces and skills](../design/04-workspaces-and-skills.md) to the Hermes-based
implementation. Plane owns planning; this storage owns private agent material and
framework evidence.

## Target layout

The operator-controlled data root contains one stable directory per agent:

```text
agent-native/agents/<agent-id>/
  protected/          host-written soul, identity and configuration projections
  memory/             durable agent memory
  practices/          durable agent-developed working conventions
  projects/main/      default mutable project work
  outputs/            host-published immutable deliverable versions
  runtime/attempts/   bounded-attempt scratch and retained diagnostic records
```

The names are an implementation convention; database records remain canonical for
identity, authority, lifecycle, events, decisions, and output metadata. Protected
files and outputs are never directly writable by model-generated code. Memory,
practices, and project work receive separate capabilities so a writable mount cannot
be mistaken for permission to change the soul.

An explicit project binding can replace `projects/main/` as the active project root
for repository tools. It does not change where protected files, memory, practices,
outputs, or runtime records live. The active binding is visible in the owner UI and
recorded with a revision. Revocation returns future work to no project access or to
the private default according to the adopted binding policy; it never moves files
silently.

## Current implementation and gaps

Provisioning currently creates `profile/`, `profile/memories/`, `profile/skills/`,
and `workspace/`. Protected soul and identity projections are read-only, while
`workspace/` contains both `PRACTICES.md` and published outputs. An optional external
project-workspace grant changes the model's working directory. AN-102 separated the
host-owned output root at runtime after that grant exposed the mixed-root defect.

Remaining migration work belongs to AN-104:

1. The first slice introduces one authoritative resolver and safely creates the
   missing practices, default-project, output and attempt-runtime areas for new or
   existing homes without moving live data. Remaining callers must adopt it instead
   of assembling paths independently.
2. Give every ordinary agent a default private project root and treat an external
   grant as a versioned project binding.
3. Move or compatibly resolve existing `workspace/outputs` and practices without
   losing immutable checksums or retained history.
4. Define backup, cleanup, retirement, replacement, removal, and quota behavior per
   area. Scratch cleanup must be safe after crashes.
5. Expose the active project binding and relevant storage health in observability,
   without exposing host paths or private memory to unauthorized agents.

AN-105 follows the topology migration and supplies bounded memory/practice reads and
writes to managed cadence work. The current worker deliberately skips general memory
loading, so the existence of `MEMORY.md` is not yet proof of functional long-term
memory.
