---
name: broken-frontmatter
description: Fixture whose frontmatter block is never terminated, so no metadata can be parsed.

# broken-frontmatter

The frontmatter above has an opening delimiter line but no closing
delimiter line. A parser therefore cannot extract `name` or `description`
from this file.

Expected inventory result: `frontmatter_ok: false` with a broken /
unterminated frontmatter health issue.
