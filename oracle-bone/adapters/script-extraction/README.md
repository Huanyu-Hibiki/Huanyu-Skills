# script-extraction — 视频/音频转脚本

/oracle-learn-from（Way b）/ /oracle-apprentice 的转录管线。

## 依赖

- `yt-dlp`（下载，可选——本地文件不需要）
- `ffmpeg` / `ffprobe`（抽帧 + 音频抽取）
- `whisper` 系（本地 faster-whisper 推荐 medium 档；或平台自带字幕轨优先）

## 管线

```
视频 URL ──yt-dlp──> source.mp4 ──ffmpeg──> audio ──whisper──> transcript.md
本地文件 ────────────> source.mp4 ──┘
（有字幕轨时优先下载字幕，跳过 whisper——更快更准）
```

## 已知坑

- **B 站字幕需登录 cookie**（无 cookie 时字幕轨拿不到，全靠本地 whisper）
- **长视频转录耗时约 1:1 实时**（CPU int8 medium 档）——一律后台跑，不占前台
- **转录产物立刻落盘**（study/<博主>/ 或 samples/ 下）——临时目录会被清
- **转录准确度低于粘贴文本**（错字/漏字/标点不准）——能用"文案提取小程序/字幕导出"就别用 whisper
- 代理环境注意：国内平台下载常需绕过系统代理（NO_PROXY）

## 输出契约

transcript.md 含：来源 URL/文件名 + 时长 + 转录全文（段落版）+ 转录方式标注（字幕轨 / whisper-<model>）。
