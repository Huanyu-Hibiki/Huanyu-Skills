---
name: ppt-design
description: Create editable PowerPoint decks through a confirmed PPTDESIGN.md. Use when the user wants a new PPT, presentation, or deck from a topic or source materials.
metadata:
  short-description: Interview or ingest materials, confirm a slide design, then generate an editable PPTX
---

# PPT Design

Create a PowerPoint deck through a reviewable design contract. The final `.pptx`
must use editable PowerPoint objects for text, tables, charts, and shapes. Photos
and illustrations may remain image assets; a full-slide screenshot is not an
editable deck.

## Choose the input mode

### Topic interview

Use when the user gives a topic but no complete source package. Establish the
topic, then ask exactly one question per turn. Wait for the user's answer before
asking the next question. Do not bundle questions or infer an unanswered field.
Prioritize goal, audience, context, core message, evidence, scope, and visual
preferences. If the user answers with a blank or unusable response, repeat the
same question in a clearer form.

### Source materials

Use when the user supplies documents, notes, spreadsheets, links, images, or an
existing deck. Treat the supplied material as the primary source of truth. Make
a material inventory after reading the supplied artifacts with the appropriate
local tools. Record extracted summaries, facts, assets, and licensing notes;
identify missing facts or assets, and ask at most one question when the missing
information would change the story or design. A binary or unsupported artifact
may remain an explicit "待提取" gap, but it must not be silently treated as
verified fact.

If facts, data, examples, or visual assets are missing, instruct the Agent to
search authoritative first-party sources. Record each external source, date, and
use in `PPTDESIGN.md`; mark uncertain claims and licensing status explicitly.
The skill does not require a particular search connector.

## Design checkpoint

Both modes produce and display `PPTDESIGN.md` before any PPTX work. Follow the
contract in [references/pptdesign-contract.md](references/pptdesign-contract.md):
use a YAML token header plus readable narrative and a slide-by-slide outline.
Show the outline, visual direction, sources, and unresolved decisions. Wait for
an explicit user confirmation. A vague acknowledgement or a request for more
changes does not open the generation gate. If the user requests changes after
confirmation, reopen the contract, return it to `status: awaiting-user-confirmation`,
and require a second explicit confirmation before generation.

## Generate and verify

After confirmation, generate the deck from the contract using an object-level
PPTX implementation. Keep the design source, `.pptx`, and optional rendered
preview together in the output directory. Inspect every slide for missing
content, overflow, overlap, contrast, alignment, and image cropping. Verify that
the result opens as a PowerPoint file and that the required content is not a
single flattened image.

The bundled minimal renderer is `scripts/generate_pptx.py` and requires
`requirements.txt` (`python-pptx`). It accepts only a `PPTDESIGN.md` whose YAML
frontmatter says `status: confirmed` and `editable_output: true`:

```powershell
python scripts/generate_pptx.py <PPTDESIGN.md> <output.pptx>
```

The renderer is a native-object baseline, not a visual-quality shortcut. Extend
its slide layout mapping when a confirmed design specifies richer charts, tables,
images, or notes; keep those as PowerPoint objects or explicit image assets.
Each run also writes a same-folder `<name>.preview.html` for quick visual review.

For the rationale behind the design system, consult the supplied reference
projects under `template-project/` only when the current request needs those
details. The HTML and image-deck references inform planning and visual QA; they
are not the final editable-PPT renderer.
