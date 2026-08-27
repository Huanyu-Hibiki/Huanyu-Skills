# pulse-resolve

> URL normalizer for Chinese social platforms.

Resolves short links, extracts platform-native work IDs, and preserves critical tokens (like RedNote's `xsec_token`).

## Origin

This tool **ports URL parsing logic from [AiToEarn](https://github.com/yikart/AiToEarn)** (`apps/aitoearn-server/src/core/channels/platforms/<platform>/<platform>-work.provider.ts`). All credit for the parsing algorithms belongs to the AiToEarn team. PulseHub only removes the NestJS dependency and unifies the three platform parsers into one CLI.

| Platform | AiToEarn source file | Status |
|----------|----------------------|--------|
| Bilibili | `bilibili-work.provider.ts` | ✅ Ported (12 tests) |
| Douyin | `douyin-work.provider.ts` | ✅ Ported (14 tests) |
| RedNote | `rednote-work.provider.ts` | ✅ Ported (14 tests) |
| WeChat Official | — (no AiToEarn base) | ✅ Implemented (7 tests) |
| Zhihu | — (no AiToEarn base) | ✅ Implemented (9 tests) |
| WeChat Channels | — | 🔴 Blocked (requires scan-login, no public URL) |

**Total: 56 tests passing across 5 platforms.**

## Usage

```bash
# Resolve a single URL
pnpm --filter pulse-resolve dev -- "https://xhslink.com/a/abc123"

# Resolve multiple URLs from a file
pnpm --filter pulse-resolve dev -- --input urls.txt --output resolved.json

# Pipe mode
echo "https://v.douyin.com/abc123/" | pnpm --filter pulse-resolve dev -- --stdin
```

## Output Format

```json
{
  "platform": "rednote",
  "workId": "65f8e7ab000000000d00aabc",
  "url": "https://www.xiaohongshu.com/explore/65f8e7ab000000000d00aabc?xsec_token=ABxyz...",
  "originalLink": "https://xhslink.com/a/abc123",
  "token": { "xsec_token": "ABxyz..." },
  "resolvedAt": "2026-07-27T10:30:00.000Z"
}
```

See [ARCHITECTURE.md §5.1](../../ARCHITECTURE.md) for the full `ResolvedLink` contract.

## Why a Separate Tool?

- **Decoupled from AiToEarn's NestJS runtime** — runs as a standalone CLI
- **No database / Redis / OAuth dependencies** — pure HTTP + URL parsing
- **Tokenizable output** — `xsec_token` etc. are preserved, not stripped
- **Composable** — AI Agents can invoke via `child_process` or HTTP wrapper

## License

MIT. Original parsing logic is from AiToEarn (also MIT).
