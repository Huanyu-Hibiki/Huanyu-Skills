# whisper-transcribe

Whisper wrapper for audio transcription. Used by `pulse-enrich` to analyze spoken content in videos.

## Usage

```bash
# Basic transcription
python transcribe.py --input audio.mp3

# With language hint (faster + more accurate)
python transcribe.py --input audio.mp3 --language zh

# Larger model for better accuracy
python transcribe.py --input audio.mp3 --model small
```

## Model Selection

| Model | Size | Speed (CPU) | Accuracy (zh) | When to use |
|-------|------|-------------|---------------|-------------|
| `tiny` | 39M | Fastest | Poor | Quick filter, low-stakes |
| `base` | 74M | ~30s / min audio | OK | **Default** — good balance |
| `small` | 244M | ~90s / min | Good | When accuracy matters |
| `medium` | 769M | ~3min / min | Very good | GPU recommended |
| `large` | 1550M | Slow | Best | GPU required |

**Recommendation**: Start with `base`. Upgrade to `small` if you find transcripts are missing purchase-intent keywords.

## Output Format

```json
{
  "text": "今天给大家推荐一款无线耳机...",
  "language": "zh",
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "今天给大家推荐一款无线耳机"
    }
  ]
}
```

## Integration with yt-dlp

Typical workflow:

```bash
# Step 1: Download audio
yt-dlp -x --audio-format mp3 --audio-quality 5 \
  -o "/tmp/audio.mp3" \
  "https://www.douyin.com/video/xxx"

# Step 2: Transcribe
python transcribe.py --input /tmp/audio.mp3 --language zh
```

## Status

🟡 Skeleton. Implementation pending M3.

## Performance Notes

- First run downloads model weights (~150MB for `base`)
- CPU-only mode is fine for batch processing (not real-time)
- For frequent use, consider `faster-whisper` (CTranslate2 backend, 4x faster)
