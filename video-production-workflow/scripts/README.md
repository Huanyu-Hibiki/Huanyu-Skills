# 执行脚本目录

本目录是 `video-production-workflow` 的统一实现层。所有可执行脚本都放在这里，子 Skill 只通过本目录调用，不再依赖父目录或备份目录中的脚本路径。

## 目录映射

| 目录 | 来源能力 | 主要入口 |
|---|---|---|
| `video-caption-correct/` | 本地 Whisper/Fun-ASR 或可选火山引擎转录、字幕格式化、口癖识别、审核页、FCPXML 辅助 | `run_transcribe.sh`、`doctor.js`、`generate_review.js`、`lib/` |
| `video-rough-cut/` | Whisper/Fun-ASR 转录、字幕映射、EDL 渲染、调色、时间线预览 | `transcribe.py`、`render.py`、`align_to_manuscript.py` |
| `video-jianying-draft/` | 剪映原生 Draft 生成及其内置适配库 | `jianying.py`、`vendor/pyJianYingDraft/`、`vendor/template_jianying/` |
| `video-assets/` | 图片、Stock 视频、YouTube 下载、裁切、标准化和许可证登记 | `media_cli.py`、`normalize_asset.py`；配置见 Skill 根 `.env` |
| `b-roll-finder/` | B-roll 静帧微动、网页截图和候选 cutaway 处理 | `zoom_still.py`、`cdp_capture.py` |
| `b-roll-generate/` | Gemini 拼贴视频、HyperFrames 动画地图和对比检查 | `generate_video.py`、`animation-map.mjs`、`contrast-report.mjs` |
| `video-polish/` | 把已批准 B-roll 按 manifest 装配到精剪视频 | `compose_broll.py` |
| `video-plan/` | 模型驱动的分镜和交接文档生成入口说明 | `README.md` + `templates/` |
| `video-fine-cut/` | 剪映/Filmora 人工精剪入口说明 | `README.md`；装配由 `video-polish/compose_broll.py` 负责 |
| `video-init/` | 项目初始化 | `init_project.py` |
| `video-status/` | 只读状态看板 | `status.py` |
| `video-skill-optimize/` | 任务证据账本、有界候选、留出验证和人工采纳 | `optimize.py` |
| `video-migrate/` | 状态 schema 迁移 | `migrate.py` |

## 路径约定

脚本通过自身位置定位合集根目录，不要求安装到 `~/.claude/skills/`。Python 脚本必须从合集根目录通过 `uv run` 执行；项目文件始终由命令参数传入，默认不写入脚本目录。媒体下载 CLI 未指定 `--output` 时写入当前工作目录下的 `downloads/`，不会创建 Skill 内缓存目录。

```powershell
cd "<合集根>"
uv run python scripts/video-status/status.py "<项目>"
```

## 不纳入版本的内容

- `.env`、API key、Cookie；
- `downloads/`、`cache/`、`.setup_done`、`.engine_toggle`；
- `__pycache__/` 和生成的媒体文件；
- 用户项目中的 Raw、草稿、成片和许可证数据。
