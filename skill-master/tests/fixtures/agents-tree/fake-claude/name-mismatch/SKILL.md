---
name: original-name
description: Fixture where the frontmatter name deliberately differs from the directory name to exercise the naming-consistency health check.
---

# original-name

Static test fixture (no executable logic).

- Frontmatter `name` is `original-name`.
- Directory name is `name-mismatch`.
- Expected inventory result: health issue "name mismatch" (frontmatter name
  does not match the containing directory).
