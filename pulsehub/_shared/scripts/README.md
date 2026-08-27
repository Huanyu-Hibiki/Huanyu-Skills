# PulseHub Scripts

Direct CLI wrappers around upstream tools. AI Agents call these from skills.

## Layout

```
scripts/
├── python/                     # Python wrappers
│   ├── ytdlp-fetch/            # yt-dlp metadata fetcher
│   └── whisper-transcribe/     # Whisper transcription
└── shell/                      # Shell wrappers
    └── rsshub-fetch.sh         # RSSHub route fetcher
```

## Why wrappers (instead of calling upstream directly)?

Wrappers add value when they:
- **Normalize output** to a stable JSON shape
- **Handle errors gracefully** (retry, fallback, clear messages)
- **Add caching** for expensive operations
- **Compose multiple calls** into one logical operation

Wrappers don't add value when they just forward arguments. PulseHub avoids that.

## Tool Inventory

### Python

| Tool | Path | Status | Purpose |
|------|------|--------|---------|
| `ytdlp-fetch` | `python/ytdlp-fetch/` | 🟡 Skeleton | Fetch video metadata as JSON |
| `whisper-transcribe` | `python/whisper-transcribe/` | 🟡 Skeleton | Transcribe audio to text |

### Shell

| Tool | Path | Status | Purpose |
|------|------|--------|---------|
| `rsshub-fetch` | `shell/rsshub-fetch.sh` | 🟡 Skeleton | Fetch RSSHub route |

## Setup

### Python tools

```bash
# Recommended: use uv (fast) or venv
cd scripts/python/ytdlp-fetch
uv sync         # or: python -m venv .venv && source .venv/bin/activate && pip install -e .

cd ../whisper-transcribe
uv sync
```

Requires:
- Python ≥ 3.11
- ffmpeg (for yt-dlp audio extraction)
- Whisper model files (auto-downloaded on first use)

### Shell tools

```bash
# Just make them executable
chmod +x scripts/shell/*.sh
```

Requires:
- curl
- jq
- A running RSSHub instance (self-hosted or public)

## Contributing a New Script

1. Pick `python/` or `shell/` based on tool's native language
2. Create `scripts/<lang>/<tool-name>/`
3. Add a `README.md` describing usage and output format
4. Add an entry to the inventory tables above
5. Add usage examples to relevant skills (`skills/*/SKILL.md`)

## Calling Convention

All scripts should:
- Accept `--help` and exit 0
- Exit non-zero on error
- Write progress to stderr, results to stdout
- Output JSON to stdout when `--output json` is passed (or by default for non-interactive use)
- Accept `--input` and `--output` for file-based I/O
- Be idempotent where possible
