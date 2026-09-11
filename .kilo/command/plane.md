---
description: Show Plane planning status (summary/current/last-worked/milestones)
agent: first-builder
---

Run the read-only First Builder Plane status tool with the bash tool and print
its output verbatim, with no added commentary:

    .venv/bin/python first-builder/tools/plane_status.py $ARGUMENTS

If `$ARGUMENTS` is empty, run `summary` instead. Plane is the only planning
source.
