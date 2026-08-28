---
name: clean-skill
description: A boring, well-behaved notes skill used as the false-positive control for the security scanner.
---

# Notes Helper

Organizes plain-text notes stored in the workspace.

## Workflow

1. List the markdown files in the `notes/` folder.
2. Group files by the date in their file name.
3. Print a short index of each group.

## Boundaries

- Only reads and writes files under its own folder.
- No network usage of any kind.
- Plain, readable steps with nothing hidden.
