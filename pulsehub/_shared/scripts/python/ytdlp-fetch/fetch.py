"""ytdlp-fetch — yt-dlp wrapper that returns normalized JSON metadata.

Usage:
    python fetch.py --url "https://www.bilibili.com/video/BVxxx"
    python fetch.py --url "..." --output metadata.json
    python fetch.py --input urls.txt --output metadata.json
    echo "<url>" | python fetch.py --stdin

Output (JSON array, one object per URL):
    [
      {
        "url": "...",
        "title": "...",
        "description": "...",
        "uploader": "...",
        "upload_date": "YYYYMMDD",
        "duration": 600,
        "thumbnail": "...",
        "tags": ["..."],
        "extractor": "bilibili",
        "raw": { ... }
      }
    ]

Failed URLs produce an entry with `error` set:
    { "url": "...", "error": "...", "raw": null }
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

# yt-dlp is imported lazily so the script can print --help without yt-dlp installed.
# Users run `pip install yt-dlp` separately.


def fetch_metadata(url: str, *, no_warnings: bool = True) -> dict[str, Any]:
    """Fetch metadata for a single URL via yt-dlp.

    Returns a normalized dict. On failure, returns {url, error}.
    """
    try:
        from yt_dlp import YoutubeDL
    except ImportError as e:
        return {
            "url": url,
            "error": f"yt-dlp not installed: {e}. Run: pip install yt-dlp",
            "raw": None,
        }

    # yt-dlp options: skip download, just extract info.
    # quiet=True suppresses progress output; no_warnings keeps stderr clean.
    opts: dict[str, Any] = {
        "skip_download": True,
        "quiet": no_warnings,
        "no_warnings": no_warnings,
        "extract_flat": False,
        # Don't write any files to disk
        "writeinfojson": False,
        "writethumbnail": False,
        "writedescription": False,
        # Don't print banners / headers
        "noprogress": True,
        "consoletitle": False,
    }

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:  # noqa: BLE001 — yt-dlp raises various exception types
        return {
            "url": url,
            "error": f"{type(e).__name__}: {e}",
            "raw": None,
        }

    if info is None:
        return {
            "url": url,
            "error": "yt-dlp returned no info",
            "raw": None,
        }

    # Normalize: pull the common fields across extractors.
    # yt-dlp returns a dict; fields vary by platform. We pick the stable subset.
    return {
        "url": url,
        "title": info.get("title"),
        "description": info.get("description"),
        "uploader": info.get("uploader") or info.get("channel") or info.get("uploader_id"),
        "upload_date": info.get("upload_date"),  # YYYYMMDD string
        "duration": info.get("duration"),  # seconds, int
        "thumbnail": info.get("thumbnail"),
        "tags": info.get("tags") or [],
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "comment_count": info.get("comment_count"),
        "extractor": info.get("extractor_key") or info.get("extractor"),
        "extractor_key": info.get("extractor_key"),
        "webpage_url": info.get("webpage_url"),
        "original_url": info.get("original_url"),
        "raw": info,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="yt-dlp wrapper that fetches video metadata as normalized JSON",
    )
    parser.add_argument("--url", help="Video URL")
    parser.add_argument("--input", help="File containing one URL per line")
    parser.add_argument("--output", help="Output file (default: stdout)")
    parser.add_argument("--stdin", action="store_true", help="Read URLs from stdin")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show yt-dlp warnings (default: suppressed)",
    )
    args = parser.parse_args()

    urls: list[str] = []
    if args.stdin:
        urls = [line.strip() for line in sys.stdin if line.strip()]
    elif args.input:
        with open(args.input, encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip()]
    elif args.url:
        urls = [args.url]
    else:
        parser.error("Provide --url, --input, or --stdin")

    results: list[dict[str, Any]] = []
    success_count = 0
    fail_count = 0

    for url in urls:
        result = fetch_metadata(url, no_warnings=not args.verbose)
        results.append(result)
        if "error" in result:
            fail_count += 1
            print(f"[warn] {url}: {result['error']}", file=sys.stderr)
        else:
            success_count += 1
            title = result.get("title") or "(no title)"
            print(f"[ok] {url}: {title}", file=sys.stderr)

    output = json.dumps(results, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(
            f"\nDone: {success_count} succeeded, {fail_count} failed.",
            file=sys.stderr,
        )
        print(f"Wrote {len(results)} entries to {args.output}", file=sys.stderr)
    else:
        print(output)

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
