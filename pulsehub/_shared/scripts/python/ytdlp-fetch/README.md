# ytdlp-fetch

yt-dlp wrapper that returns normalized JSON metadata for PulseHub.

## Usage

```bash
# Single URL
python fetch.py --url "https://www.bilibili.com/video/BV1xx411c7mD"

# Multiple URLs from file
python fetch.py --input urls.txt --output metadata.json

# Stdin pipe
echo "https://www.douyin.com/video/xxx" | python fetch.py --stdin
```

## Output Format

```json
[
  {
    "url": "https://www.bilibili.com/video/BV1xx411c7mD",
    "title": "...",
    "description": "...",
    "uploader": "...",
    "upload_date": "20260727",
    "duration": 600,
    "thumbnail": "https://...",
    "tags": ["..."],
    "extractor": "bilibili",
    "raw": { }
  }
]
```

## Why a Wrapper?

- **Normalizes output** across platforms (Bilibili, Douyin, YouTube, etc. all return slightly different shapes)
- **Handles errors** per-URL without failing the whole batch
- **Stable JSON contract** that `pulse-enrich` can rely on

## Status

🟡 Skeleton. Implementation pending M1.
