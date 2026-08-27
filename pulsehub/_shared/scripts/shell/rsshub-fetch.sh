#!/usr/bin/env bash
# rsshub-fetch — fetch an RSSHub route and return normalized JSON.
#
# Usage:
#   bash scripts/shell/rsshub-fetch.sh "/xiaohongshu/user/{uid}"
#   bash scripts/shell/rsshub-fetch.sh "/bilibili/user/dynamic/{uid}" --output json
#   bash scripts/shell/rsshub-fetch.sh "/bilibili/user/dynamic/{uid}" --raw
#
# Environment:
#   RSSHUB_BASE_URL  Base URL of RSSHub instance (default: http://localhost:1200)
#   CURL_TIMEOUT     Request timeout in seconds (default: 15)
#
# Output:
#   --output json (default): normalized JSON with title/url/publishedAt fields
#   --raw:                     raw RSS XML as returned by RSSHub
#
# Exit codes:
#   0  Success (or partial — some entries failed normalization)
#   1  Bad usage (no route provided)
#   2  RSSHub unreachable (connection refused / timeout)
#   3  RSSHub returned HTTP error
#   4  Response parse error (not valid RSS/JSON)

set -euo pipefail

RSSHUB_BASE_URL="${RSSHUB_BASE_URL:-http://localhost:1200}"
CURL_TIMEOUT="${CURL_TIMEOUT:-15}"

OUTPUT_FORMAT="json"
RAW_OUTPUT=0
ROUTE=""

# ─── arg parsing ────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output)
      OUTPUT_FORMAT="$2"
      shift 2
      ;;
    --raw)
      RAW_OUTPUT=1
      shift
      ;;
    --base-url)
      RSSHUB_BASE_URL="$2"
      shift 2
      ;;
    --timeout)
      CURL_TIMEOUT="$2"
      shift 2
      ;;
    --help|-h)
      cat <<EOF
Usage: rsshub-fetch <route> [--output json|text] [--raw] [--base-url URL] [--timeout SEC]

Examples:
  rsshub-fetch "/xiaohongshu/user/abc123"
  rsshub-fetch "/bilibili/user/dynamic/DEF456" --output json
  rsshub-fetch "/zhihu/hotlist" --raw
  RSSHUB_BASE_URL=https://rsshub.app rsshub-fetch "/bilibili/user/dynamic/123"

Environment:
  RSSHUB_BASE_URL  Base URL (default: http://localhost:1200)
  CURL_TIMEOUT     Timeout seconds (default: 15)
EOF
      exit 0
      ;;
    *)
      ROUTE="$1"
      shift
      ;;
  esac
done

if [[ -z "$ROUTE" ]]; then
  echo "Error: route is required (e.g., /bilibili/user/dynamic/123)" >&2
  exit 1
fi

# Normalize route: ensure leading slash
[[ "$ROUTE" != /* ]] && ROUTE="/$ROUTE"

URL="${RSSHUB_BASE_URL}${ROUTE}"

# ─── fetch ──────────────────────────────────────────────────────────────────
# Use curl with retries; capture HTTP status separately from body.
HTTP_RESPONSE=$(curl --silent --show-error \
  --write-out "\n__HTTP_STATUS__:%{http_code}\n" \
  --max-time "$CURL_TIMEOUT" \
  --retry 2 \
  --retry-delay 1 \
  -H 'User-Agent: PulseHub/0.1 (https://github.com/zhuyaotutejia/PulseHub)' \
  -H 'Accept: application/rss+xml, application/xml, text/xml' \
  "$URL" 2>&1) || {
    # curl failed entirely (connection refused, DNS error, etc.)
    echo "Error: RSSHub unreachable at ${RSSHUB_BASE_URL} (route: ${ROUTE})" >&2
    echo "Hint: start RSSHub with 'npm start' in the RSSHub directory" >&2
    echo "Captured error: ${HTTP_RESPONSE}" >&2
    exit 2
  }

# Split body from status line
HTTP_BODY="${HTTP_RESPONSE%__HTTP_STATUS__:*}"
HTTP_STATUS="${HTTP_RESPONSE##*__HTTP_STATUS__:}"
HTTP_STATUS="${HTTP_STATUS//$'\n'/}"
HTTP_STATUS="${HTTP_STATUS//$'\r'/}"

if [[ "$HTTP_STATUS" != "200" ]]; then
  echo "Error: RSSHub returned HTTP ${HTTP_STATUS} for ${URL}" >&2
  # Surface first 500 chars of body for debugging
  echo "Body (first 500 chars):" >&2
  echo "${HTTP_BODY:0:500}" >&2
  exit 3
fi

# ─── output ─────────────────────────────────────────────────────────────────
if [[ "$RAW_OUTPUT" == "1" || "$OUTPUT_FORMAT" == "raw" ]]; then
  echo "$HTTP_BODY"
  exit 0
fi

# ─── normalize ──────────────────────────────────────────────────────────────
# RSSHub returns RSS XML by default. To get JSON, append .json to route.
# We try .json first; if it fails, fall back to XML parsing via jq+xpath.
JSON_URL="${URL}.json"

JSON_RESPONSE=$(curl --silent --show-error \
  --write-out "\n__HTTP_STATUS__:%{http_code}\n" \
  --max-time "$CURL_TIMEOUT" \
  -H 'User-Agent: PulseHub/0.1' \
  -H 'Accept: application/json' \
  "$JSON_URL" 2>&1) || {
    # JSON endpoint unavailable — RSSHub may have .json disabled.
    # Fall back to XML.
    :
  }

JSON_BODY="${JSON_RESPONSE%__HTTP_STATUS__:*}"
JSON_STATUS="${JSON_RESPONSE##*__HTTP_STATUS__:}"
JSON_STATUS="${JSON_STATUS//$'\n'/}"
JSON_STATUS="${JSON_STATUS//$'\r'/}"

if [[ "$JSON_STATUS" == "200" && -n "$JSON_BODY" ]]; then
  # Validate it's actually JSON
  if echo "$JSON_BODY" | jq --raw-output0 '.' >/dev/null 2>&1; then
    echo "$JSON_BODY" | jq --raw-output0 '.'
    exit 0
  fi
fi

# ─── XML fallback ───────────────────────────────────────────────────────────
# RSSHub returned XML. Normalize to our canonical shape using jq + xml2json.
# We rely on `jq` and `xml2json` being available. If not, output raw XML.
if ! command -v jq >/dev/null 2>&1; then
  echo "Warning: jq not installed, returning raw XML" >&2
  echo "$HTTP_BODY"
  exit 0
fi

# Use Python for XML→JSON conversion (more reliable than xml2json tool)
NORMALIZED=$(python3 -c '
import sys
import xml.etree.ElementTree as ET
import json

xml_text = sys.stdin.read()
try:
    root = ET.fromstring(xml_text)
except ET.ParseError as e:
    print(json.dumps({"error": f"XML parse failed: {e}"}))
    sys.exit(0)

channel = root.find("channel")
if channel is None:
    print(json.dumps({"error": "no channel element"}))
    sys.exit(0)

feed_title = channel.findtext("title", "")
feed_link = channel.findtext("link", "")
feed_description = channel.findtext("description", "")

items = []
for item in channel.findall("item"):
    entry = {
        "title": item.findtext("title", ""),
        "link": item.findtext("link", ""),
        "description": item.findtext("description", ""),
        "guid": item.findtext("guid", ""),
        "pubDate": item.findtext("pubDate", ""),
        "author": item.findtext("author", ""),
        "categories": [c.text or "" for c in item.findall("category")],
    }
    items.append(entry)

print(json.dumps({
    "feed": {"title": feed_title, "link": feed_link, "description": feed_description},
    "items": items,
    "count": len(items),
}, ensure_ascii=False, indent=2))
' <<<"$HTTP_BODY")

echo "$NORMALIZED"
exit 0
