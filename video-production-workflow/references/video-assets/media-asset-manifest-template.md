# Media Asset Manifest Template

Save to:

```text
D:\work\OPC\videos\{第X期：视频标题}\assets\licenses\media_asset_manifest.json
```

```json
{
  "project_folder": "D:\\work\\OPC\\videos\\{第X期：视频标题}",
  "updated_at": "2026-05-05",
  "assets": [
    {
      "asset_id": "asset_001",
      "related_motion_id": "Motion 01",
      "related_segment": "S04",
      "type": "background_music",
      "title": "Cinematic Cyber Intro",
      "creator": "creator_name",
      "source_site": "Pixabay",
      "source_page_url": "https://example.com/source-page",
      "download_url": "https://example.com/download",
      "license_name": "Pixabay Content License",
      "commercial_use_allowed": true,
      "attribution_required": false,
      "editorial_only": false,
      "downloaded_at": "2026-05-05",
      "original_file": "assets/raw/audio/asset_001_original.mp3",
      "processed_file": "assets/audio/music/asset_001_cyber_intro.wav",
      "processing_notes": "Converted to 48kHz stereo WAV using ffmpeg.",
      "attribution_text": ""
    }
  ]
}
```

If attribution is required, set `attribution_required` to `true` and write the exact attribution text required by the license.
