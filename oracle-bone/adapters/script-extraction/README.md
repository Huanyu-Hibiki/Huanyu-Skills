# script-extraction — 视频/音频转脚本

/oracle-learn-from（Way b）/ /oracle-apprentice 的转录管线。

## 依赖

- **ffmpeg / ffprobe**（全局 PATH，抽音频 + 时长探测；whisper 路径必需）
- **uv**（建 venv 用，可选——已有系统 Python 也能 `python -m venv`）
- 转录模型：faster-whisper 格式（CTranslate2），见下方「模型下载」——**whisper 路径必需，字幕轨路径不需要**

## 安装（一次性）

```bash
cd adapters/script-extraction
uv venv .venv                                        # 或指定版本：uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe --pre -r requirements.txt   # Windows
# uv pip install --python .venv/bin/python --pre -r requirements.txt          # macOS/Linux
```

requirements 含 `--pre`：**yt-dlp 装 nightly 版**（平台反爬更新最快），faster-whisper 稳定版。

## 模型下载（whisper 路径必需，字幕轨路径不需要）

### 放在哪里

统一放在**本目录**的 `models/` 下，命名必须是 `faster-whisper-<档位>/`——`transcribe.py` 自动发现，无需 `--model-dir`：

```
adapters/script-extraction/
└── models/
    └── faster-whisper-medium/      ← 下载后长这样（gitignored）
        ├── model.bin               ← 主权重（medium 约 1.5GB）
        ├── config.json
        ├── tokenizer.json
        └── vocabulary.txt / vocabulary.json
```

校验标准：目录里有 `model.bin` 即合法。不下载时 transcribe.py 会尝试在线下载到 `~/.cache/huggingface/hub/`（国内网络常失败，所以推荐预下载）。

| 档位 | 大小 | 适用 |
|---|---|---|
| tiny / base | ~75MB / ~145MB | 快速试验，错字多 |
| small | ~490MB | 短口播可用 |
| **medium（默认）** | ~1.5GB | 中文口播推荐，CPU int8 约 1:1 实时 |
| large-v3 | ~3.1GB | 精度最高，CPU 慢（建议 GPU） |
| large-v3-turbo | ~1.6GB | large 级精度 + 接近 medium 速度 |

### 来源 A：魔搭社区 ModelScope（国内推荐，免翻墙、快）

```bash
# 1. 往本 .venv 里装 modelscope CLI（只是下载器，不参与转录）
uv pip install --python .venv/Scripts/python.exe modelscope

# 2. 下载 medium 档到 models/（--local_dir 路径必须严格按此命名）
.venv/Scripts/modelscope.exe download --model pengzhendong/faster-whisper-medium --local_dir models/faster-whisper-medium

# 其他档位同规则换名：
#   pengzhendong/faster-whisper-small   → models/faster-whisper-small
#   pengzhendong/faster-whisper-large-v3 → models/faster-whisper-large-v3
```

### 来源 B：HuggingFace（或 hf-mirror 镜像）

```bash
# 1. 装 huggingface_hub CLI
uv pip install --python .venv/Scripts/python.exe -U huggingface_hub

# 2a. 直连（网络通时）：
.venv/Scripts/hf.exe download Systran/faster-whisper-medium --local-dir models/faster-whisper-medium

# 2b. 国内走镜像（先设环境变量再执行同一条命令）：
#    PowerShell:  $env:HF_ENDPOINT = "https://hf-mirror.com"
#    bash:        export HF_ENDPOINT=https://hf-mirror.com
.venv/Scripts/hf.exe download Systran/faster-whisper-medium --local-dir models/faster-whisper-medium
```

> macOS/Linux 把 `.venv/Scripts/xxx.exe` 换成 `.venv/bin/xxx`。
> 旧版 huggingface_hub 的命令名是 `huggingface-cli download`，参数相同。

## 日常运行

```bash
PY=.venv/Scripts/python.exe            # macOS/Linux: PY=.venv/bin/python

# URL（字幕轨优先——有字幕不耗 whisper，无字幕自动走 whisper）
$PY transcribe.py "https://www.bilibili.com/video/BVxxxx" --out study/某博主-apprentice/某标题/

# 本地文件（跳过 yt-dlp，直接 ffmpeg + whisper）
$PY transcribe.py "D:\downloads\demo.mp4" --out study/某博主-apprentice/某标题/

# 指定档位 / 指定模型目录 / 强制 whisper / B站字幕需登录 cookie
$PY transcribe.py <url> --model large-v3-turbo
$PY transcribe.py <url> --model-dir /path/to/faster-whisper-medium
$PY transcribe.py <url> --force-whisper
$PY transcribe.py <url> --cookies cookies.txt
```

输出：`<out>/transcript.md`（来源 + 时长 + 转录方式标注 + 段落版全文）。

## 管线

```
URL ──yt-dlp──> 字幕轨？──有──> VTT/SRT 清洗 ──────────────> transcript.md
 │                          └─无─> source.mp4 ──ffmpeg──> audio.wav
 └─本地文件 ─────────────────────────────────┘                 │
                                                    faster-whisper（模型三级解析：
                                                    --model-dir > models/ > 在线下载）
```

## 已知坑

- **B 站字幕需登录 cookie**（无 cookie 时字幕轨拿不到，全靠本地 whisper）：浏览器导出 cookies.txt 后传 `--cookies`
- **长视频转录耗时约 1:1 实时**（CPU int8 medium 档）——一律后台跑，不占前台
- **转录产物立刻落盘**（`--out` 直接指向 `study/<博主>-apprentice/<标题>/`）——临时目录会被清
- **转录准确度低于粘贴文本**（错字/漏字/标点不准）——能用"文案提取小程序/字幕导出"就别用 whisper
- **模型在线下载在国内大概率失败**——按「模型下载」节预下载到 `models/`，一劳永逸
- 代理环境注意：国内平台下载常需绕过系统代理（NO_PROXY）

## 输出契约

transcript.md 含：来源 URL/文件名 + 时长 + 转录全文（段落版）+ 转录方式标注（字幕轨 zh-Hans (manual/auto-ASR) / whisper-<model>(local/hw 配置)）。
