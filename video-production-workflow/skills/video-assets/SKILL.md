---
name: video-assets
description: 视频外部素材规划、搜索、下载和合规归档。获取图片、视频、音乐、音效并转码，记录具体来源和许可证。触发词：下载素材、找音乐、找音效、找图片、找视频、准备 B-roll 素材。
argument-hint: "[project-path] [asset-request-path]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep
---

# /video-assets

## 两类能力的边界

| Skill | 负责 | 不负责 |
|---|---|---|
| 搜索下载 | 按描述搜索、下载图片/视频、下载 YouTube 指定片段、简单裁剪 | 不替用户判断最终 B-roll、不会自动保证每个来源适合商用 |
| 合规归档 | 读取请求、核验具体许可证、转码、整理目录、维护 manifest | 不创作 Remotion 动画、不编辑主视频 |

实现脚本统一位于 `<合集根>/scripts/video-assets/`：

- `media_cli.py`：图片、Stock 视频、YouTube 搜索/下载/裁切；
- `normalize_asset.py`：音频、视频和图片标准化并追加许可证 manifest。

## 流程

🔴 **CHECKPOINT：下载任何第三方素材前，展示本轮下载清单（来源、预计数量、许可证判断）并等用户确认；许可证不明的高风险来源单独列出。**

1. 优先读取 `assets/requests/asset_request_list.md`；没有则询问素材类型、用途、时长、画幅、情绪、许可证和项目路径。
2. 按来源聚类需求，先做 metadata search，再下载确认项，避免逐条反复抓取。
3. 每项第三方素材记录来源网站、页面 URL、下载 URL、标题、作者、许可证、商用许可、署名要求、下载日期和风险。
4. 许可证不清楚时标记 blocked，不放进消费者目录。
5. 用 FFmpeg 标准化音乐、音效、Stock 视频和用户提供的需要处理的副本。
6. 更新 `assets/licenses/media_asset_manifest.json` 和 `assets/logs/ffmpeg_commands.md`。
7. 输出素材摘要和未解决风险，等待用户确认高风险或付费来源。

## CLI 示例

```bash
uv run --project "<合集根>" python "<合集根>/scripts/video-assets/media_cli.py" status
uv run --project "<合集根>" python "<合集根>/scripts/video-assets/media_cli.py" search "城市夜景" --type video
uv run --project "<合集根>" python "<合集根>/scripts/video-assets/media_cli.py" video "城市夜景" --duration 30 --output "<项目>/assets/incoming"
uv run --project "<合集根>" python "<合集根>/scripts/video-assets/media_cli.py" youtube "<URL>" --start 60 --end 90 --output "<项目>/assets/incoming"
uv run --project "<合集根>" python "<合集根>/scripts/video-assets/normalize_asset.py" "<项目>/assets/incoming/source.mp4" \
  --project "<项目>" --type stock-video --asset-id ASSET-001 \
  --source-site Pexels --source-url "<具体页面 URL>" \
  --license "Pexels License" --commercial-use
```

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 搜索无结果或结果全不相关 | 换中英双语关键词、放宽筛选条件重搜 | 列出替代来源路线（Stock→用户自录→Remotion 自制）让用户选 |
| 下载失败/超时 | 重试一次并换镜像或清晰度档位 | 记录到 `assets/logs/`，标记该请求 blocked，不阻塞其余条目 |
| 许可证页面无法打开或信息不全 | 该素材标记 `blocked`，不进消费者目录 | 🔴 换素材；不允许「平台一般免费」当许可证证明 |
| YouTube 片段已被删除或地区限制 | 告知用户并给出可替代的官方来源 | 不用其他渠道绕过访问限制 |
| 用户提供的素材格式异常（如 8DoF/HEVC） | `normalize_asset.py` 转码为标准规格 | 转码失败时保留原文件并在 manifest 标注风险 |

## 禁止

- 下载版权不明的电影、电视剧、付费内容、DRM 内容；
- 用 `yt-dlp` 绕过访问控制或网站条款；
- 把素材下载到 Skill 目录、工作区根目录或 Remotion 工程；
- 让 Remotion 直接读取 raw 下载；
- 将“平台一般免费”当作具体文件的许可证证明。

## 默认标准化

| 类型 | 交付标准 |
|---|---|
| 音乐 | WAV、48kHz、立体声、PCM 16-bit |
| 音效 | WAV、48kHz、立体声、PCM 16-bit，按需求裁剪 |
| Stock 视频 | MP4、H.264、`yuv420p`、30fps、1080p，B-roll 默认去音频 |
| 图片 | 原始高分辨率文件 + 用途和来源记录 |
