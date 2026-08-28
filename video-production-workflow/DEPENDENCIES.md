# 依赖说明

本 Skill 只有一个 Python 环境：根目录下的 `.venv`。不要使用系统 Python、Anaconda 或其他项目的虚拟环境。

## 初始化环境

在本文件所在目录执行：

```powershell
uv venv .venv --python 3.11
uv sync
```

之后所有 Python 入口统一使用：

```powershell
uv run python "<合集根>/scripts/<阶段>/<脚本>.py" --help
```

从其他目录调用时使用 `--project`：

```powershell
uv run --project "<skill 安装目录>/01-制作管线/video-production-workflow" python "<skill 安装目录>/01-制作管线/video-production-workflow/scripts/video-status/status.py" "<项目>"
```

## 全局命令

- Python 3.11（由 `uv venv --python 3.11` 管理）
- Node.js 18+
- FFmpeg 和 FFprobe
- Bash：macOS/Linux 原生，Windows 可使用 Git Bash；Windows 的 Python/Node 入口可直接运行
- Google Cloud CLI (`gcloud`)：仅 Veo 首尾帧生成流程用于从 GCS 下载结果

## Python

- 根 `pyproject.toml`：本地 Whisper、Fun-ASR、Torch CUDA 12.6、Librosa、Pillow、Gemini 等依赖
- `openai-whisper` 是本地 Whisper 推理包，不是 OpenAI API；对话模型由当前 Agent 提供
- PyTorch 固定为 CUDA 12.6 wheel：`torch==2.7.1+cu126`、`torchaudio==2.7.1+cu126`
- `video-assets/media_cli.py`：`requests`
- `b-roll-finder/zoom_still.py`：`Pillow`
- `b-roll-finder/cdp_capture.py`：`websockets`
- `video-jianying-draft/jianying.py`：随目录提供的 `vendor/pyJianYingDraft` 和 `imageio`
- `b-roll-generate/generate_video.py`、`upload_file.py`：`google-genai`，仅实际调用 Gemini 时需要
- `b-roll-generate/generate_veo_first_last.py`：实际生成还需要 Vertex AI ADC/服务账号凭证和 `gcloud storage cp`

## Node.js

- `video-caption-correct/` 的 `.js` 脚本只使用 Node.js 内置模块
- HyperFrames 检查脚本会按 `package-loader.mjs` 的规则解析或引导安装对应 npm 包

## 环境变量

所有环境变量统一写入 Skill 根目录 `.env`。`.env.example` 已列出完整变量名；空值表示该能力暂不启用。

| 变量 | 能力 | 必需条件 |
|---|---|---|
| `TRANSCRIPTION_ENGINE` | 转录后端 | 可选，默认 `local`（Whisper + Fun-ASR）；云端可设为 `flash`、`v3-standard` 或 `auto` |
| `VOLCENGINE_API_KEY` | 火山引擎字幕转录 | 仅显式使用火山引擎转录时需要；本地 Whisper/Fun-ASR 不需要 |
| `GEMINI_API_KEY` | Gemini Omni Flash 拼贴 B-roll | 实际生成或上传 Gemini 素材时必需 |
| `GOOGLE_CLOUD_PROJECT` | Vertex AI / Veo | 使用 `generate_veo_first_last.py` 实际生成时必需 |
| `GOOGLE_CLOUD_LOCATION` | Vertex AI / Veo 区域 | 可选，默认 `us-central1` |
| `PEXELS_API_KEY` | Pexels 图片/视频搜索 | 使用 Pexels 时必需 |
| `UNSPLASH_ACCESS_KEY` | Unsplash 图片搜索 | 使用 Unsplash 时必需 |
| `PIXABAY_API_KEY` | Pixabay 图片/视频搜索 | 使用 Pixabay 时必需 |
| `YTDLP_COOKIES` | YouTube 登录 Cookies | YouTube 需要登录或反爬时可选 |
| `CAPCUT_MCP_DIR` | 覆盖剪映适配库 | 使用自定义适配库时可选 |
| `FUNASR_NANO_DIR` | 覆盖 Fun-ASR Nano 模型代码目录 | 非内置模型布局时可选 |
| `CHROME_PATH` / `CDP_SCALE` | Chrome CDP 网页截图 | CDP 截图时按需设置 |

Python、Shell 和 Node 的实现入口都会从该根 `.env` 读取；已导出的系统变量优先于 `.env` 中的空值。
对话模型不在 `.env` 中配置，直接使用当前 Agent 的模型；只有专用视频/图像生成 API 才在调用参数中指定其服务要求的模型。

## API 和本地应用

- 全部变量：Skill 根目录 `.env.example`
- 剪映专业版：只在 `video-jianying-draft` 输出并打开 Draft 时需要
- Chrome：只在 `b-roll-finder/cdp_capture.py` 截取网页证据时需要；可通过 `CHROME_PATH` 指定可执行文件

## 验证命令

```powershell
uv run python -m compileall -q -f scripts
uv run python scripts/video-init/init_project.py --help
uv run python scripts/video-polish/compose_broll.py --help
uv run python -c "import torch; assert torch.version.cuda and torch.cuda.is_available(); print(torch.__version__, torch.version.cuda)"
```
