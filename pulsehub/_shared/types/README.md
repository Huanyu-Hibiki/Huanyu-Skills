# @pulsehub/types

Shared TypeScript contracts for PulseHub. Imported by `apps/*`, `packages/*`, and any skill that needs typed data.

## Exports

- `Platform` — union of supported platforms
- `ResolvedLink` — output of `pulse-resolve`
- `Opportunity` — output of `pulse-enrich`
- `Report`, `ReportEntry` — output of `pulse-deliver`
- `DiscoveryIntent`, `DiscoveryMode` — input to `pulse-discover`

See [source](src/index.ts) for full type definitions and [ARCHITECTURE.md §5](../../ARCHITECTURE.md) for design rationale.

## Usage

```typescript
import type { ResolvedLink, Platform } from '@pulsehub/types'

const link: ResolvedLink = {
  platform: 'rednote',
  workId: '65f8e7ab000000000d00aabc',
  url: 'https://www.xiaohongshu.com/explore/65f8e7ab000000000d00aabc?xsec_token=ABxyz...',
  originalLink: 'https://xhslink.com/a/abc123',
  token: { xsec_token: 'ABxyz...' },
  resolvedAt: new Date().toISOString(),
}
```
