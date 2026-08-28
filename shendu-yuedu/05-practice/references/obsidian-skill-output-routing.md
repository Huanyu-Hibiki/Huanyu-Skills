# Obsidian skill output routing for shendu-yuedu / sy-practice

Use this when converting reading knowledge cards into executable skills for 焕羽.

## Durable routing rule

`sy-practice` has two output classes:

1. **Reading-process evidence** stays in Obsidian reading notes:
   - Base: `C:/work/Huanyu Hub/Huanyu-Knowledge/personal/阅读笔记/`
   - Per book: `personal/阅读笔记/YYYY-MM/<书名>/`
   - Per chapter: `personal/阅读笔记/YYYY-MM/<书名>/<章节名>/`
   - Examples: `原始笔记.md`, `知识卡片.md`, `实践转化.md`, `复盘.md`

2. **Executable skills extracted from the book** go to the vault-level skills layer:
   - Root: `C:/work/Huanyu Hub/Huanyu-Knowledge/skills/`
   - One book: `skills/<书名>/INDEX.md`
   - One executable skill: `skills/<书名>/<skill-slug>/SKILL.md`
   - Cross-book index: `skills/INDEX.md`

## Required indexing steps

When `sy-practice` creates or edits a book-derived skill, update all three indexes:

1. `skills/INDEX.md` — cross-book executable skill index.
2. `personal/阅读笔记/_system/用户阅读报告.md` — section `已萃取技能索引（跨书累积）`, with skill name, source book/chapter/card, trigger, and path.
3. `wiki/index.md` — Skills navigation section, or create/update a `wiki/concepts/<书名>-技能索引.md` page when the book yields multiple reusable skills.

## Boundary

Do **not** put executable book-derived skills under:

- skill 安装包目录下的 `project-archive/` 等子目录
- `personal/阅读笔记/_system/技能库.md`
- `personal/阅读笔记/YYYY-MM/<书名>/技能合集.md` as the only source of truth

Those locations may contain notes or links, but the callable skill asset lives under `Huanyu-Knowledge/skills/`.

## Relationship to Huanyu-Knowledge/SKILL.md

`C:/work/Huanyu Hub/Huanyu-Knowledge/SKILL.md` is the vault-level schema / operating constitution. It defines directory responsibilities and how agents should handle `raw/`, `wiki/`, `company/`, `personal/`, and `skills/`. Follow it when writing into the vault.
