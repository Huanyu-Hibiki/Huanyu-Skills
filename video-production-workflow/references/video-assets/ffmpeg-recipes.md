# ffmpeg Recipes

Run commands from the video project folder:

```text
D:\work\OPC\videos\{第X期：视频标题}\
```

Append every command to `assets\logs\ffmpeg_commands.md`.

## Music To WAV 48kHz Stereo

```bash
ffmpeg -y -i "assets/raw/audio/asset_001_original.mp3" -ar 48000 -ac 2 -c:a pcm_s16le "assets/audio/music/asset_001_music.wav"
```

## Sound Effect Trim To WAV

```bash
ffmpeg -y -ss 00:00:01 -to 00:00:04 -i "assets/raw/audio/asset_002_original.mp3" -ar 48000 -ac 2 -c:a pcm_s16le "assets/audio/sfx/asset_002_click.wav"
```

## Stock Video To H.264 1080p30 With Audio

```bash
ffmpeg -y -i "assets/raw/video/asset_003_original.mp4" -vf "scale=-2:1080,fps=30,format=yuv420p" -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k -ar 48000 -movflags +faststart "assets/video/stock/asset_003_broll.mp4"
```

## Stock Video To Silent H.264 1080p30

```bash
ffmpeg -y -i "assets/raw/video/asset_004_original.mp4" -vf "scale=-2:1080,fps=30,format=yuv420p" -c:v libx264 -crf 18 -preset medium -an -movflags +faststart "assets/video/stock/asset_004_broll_noaudio.mp4"
```

## Image Normalize To PNG

```bash
ffmpeg -y -i "assets/raw/image/asset_005_original.jpg" "assets/image/stock/asset_005_image.png"
```
