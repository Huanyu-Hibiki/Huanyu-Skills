# PPTDESIGN.md contract

`PPTDESIGN.md` is the reviewable hand-off between discovery and generation. It
must use YAML frontmatter for machine-readable values and Markdown for human
review.

Required sections:

- `## 叙事`: purpose, audience, usage context, core message, and evidence.
- `## 视觉 tokens`: aspect ratio, grid, colors, typography, spacing, shapes,
  chart rules, and footer rules.
- `## 来源`: supplied materials, external facts/assets with source and date,
  and licensing or uncertainty notes.
- `## 逐页大纲`: one entry per slide with title, single takeaway, content,
  layout, editable-object plan, asset slots, and speaker notes. If a slide
  requests a native table or chart, include rectangular `表格数据` rows or
  `图表数据` label/value pairs; the renderer rejects data-less requests.
- `## 待确认项`: explicit decisions still awaiting the user.

The document is not a confirmation by itself. The Agent must display it and wait
for the user to explicitly approve it before generating a PPTX. The frontmatter
starts as `status: awaiting-user-confirmation`; a change request reopens that
status and requires a new explicit approval before the renderer accepts it.
