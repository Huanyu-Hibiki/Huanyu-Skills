# PulseHub Signal Library

Curated keyword libraries used by `pulse-enrich` to detect engagement opportunities in Chinese social content.

## What Signals Are

A **Signal** is a pattern in content (title, description, transcript, comments) that indicates the author or audience is in a specific state of mind. Signals determine whether a URL is worth engaging with — and how.

## How to Use

Each `.md` file in this directory is a signal library. `pulse-enrich` reads them to construct LLM prompts for content scoring.

```text
Signal: purchase-intent
  → score: high
  → suggested angle: mention product specs, qualify budget

Signal: complaint (about competitor)
  → score: high
  → suggested angle: empathize, offer alternative

Signal: question (informational)
  → score: medium
  → suggested angle: helpful answer, soft mention
```

## Catalog

| Signal | Value | Library |
|--------|-------|---------|
| [`purchase-intent`](purchase-intent.md) | 🔥 High | User is ready to buy / asking where to buy |
| [`question-intent`](question-intent.md) | 🟡 Medium | User is researching / asking for advice |
| [`complaint`](complaint.md) | ❌ Negative | User is unhappy (skip or use for intel) |
| `trend` | 🔵 Contextual | TODO — viral markers, no library yet |
| `competitor-mention` | 🟡 Intel | TODO — track competitor name occurrences |

## Format

Each library follows this template:

```markdown
# <Signal Name>

## Score Impact
high | medium | low | negative

## Variants by Category
- Generic: ...
- Electronics: ...
- Beauty: ...

## Match Rules
- Case-insensitive
- Match on whole-word boundaries (避免"想要"匹配"不想要")
- Combine with negation list (反义词排除)

## Suggested Comment Angle
When this signal fires, suggest engaging with...

## False Positives
Watch out for...
```

## Contributing

When adding a new signal:
1. Copy `purchase-intent.md` as template
2. Add to catalog table above
3. Test against at least 20 real posts (manually verify it fires correctly)
4. Document false positives you find

The signal library is the **most culturally specific** part of PulseHub — Chinese internet slang evolves fast. Expect to update these monthly.
