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

requirements 含 `--pre`：**yt-dlp 装 nightly 版**（平台反爬更新最快），faster-whisper 稳定版；`curl-cffi` 是 **TLS 指纹拟真**依赖（抖音/小红书反爬必需——模拟真浏览器的 TLS/JA3 指纹，缺失时自动降级并警告）。

## 五大平台支持（B站 / 小红书 / 抖音 / 视频号 / 知乎）

transcribe.py 按 URL 自动识别平台，套用对应拟人化档案（TLS 指纹 + 请求间隔 + 退避重试 3s→8s）：

| 平台 | 提取器 | 反爬要点 | 推荐用法 |
|---|---|---|---|
| **B站** | ✅ | 下载宽松；**字幕轨必须登录态** | `--cookies-from-browser chrome`（浏览器已登录B站） |
| **抖音** | ✅ | 最严：校验 TLS 指纹 + 登录态 + 频控 | 网页版登录后 `--cookies-from-browser chrome`；档案自动 `impersonate=chrome` + 请求间隔 1.5s |
| **小红书** | ✅ | 严：未登录常拿不到流地址 | 同抖音：登录浏览器 + `--cookies-from-browser chrome` |
| **知乎** | ✅（视频回答） | 温和；**纯文字回答无需转录**——直接复制文本学表达 | 直接跑；间隔 1s 自动加 |
| **视频号** | ❌ 无公开网页播放器 | 无法 URL 提取 | 手机导出/录屏 → 本地文件路径；或手动粘稿 |

> `--cookies-from-browser chrome`（或 edge/firefox）直接读本机浏览器登录态，**不用导出 cookies.txt**。注意：读取时目标浏览器最好先退出（Windows 下 cookie 库会被运行中的浏览器锁住）。
> 反爬思路移植自 data-scientist-community 的实战经验：真实登录态复用（人是登录着看的）+ 拟真指纹（流量像真浏览器）+ 拟人节奏（请求不连发）+ 退避重试（3s→8s，不硬怼）。**一次性拿稿用 yt-dlp 足够；要批量采集数据请走 `adapters/perf-data/auto-collect/`（Playwright 真浏览器管线）。**

### 抖音实操序列（反爬最严，按序尝试）

```bash
$PY transcribe.py "<分享短链 v.douyin.com/...>" --out study/<博主>-apprentice/<标题>/ --cookies-from-browser chrome
# 1️⃣ 浏览器先登录 douyin.com；2️⃣ 关闭浏览器（解锁 cookie 库）；3️⃣ 跑上面的命令
# 仍被拦（风控期）→ 换手动方案：网页播放视频 → 复制"文案/字幕"或录屏导出本地文件 → 本地路径跑 whisper
```

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

### 已有本地模型？（不用重新下载）

faster-whisper 默认只扫 `~/.cache/huggingface/hub/models--Systran--...` 自动下载格式——你手动下载的模型（如在 `~/.cache/huggingface/manual/Systran/faster-whisper-medium`，或任何含 `model.bin` 的目录）它**看不见**。两种接法：

```bash
# 法 1（推荐）：目录 junction 零拷贝接入自动发现（Windows）
mklink /J models\faster-whisper-medium "C:\Users\<你>\.cache\huggingface\manual\Systran\faster-whisper-medium"
#     macOS/Linux 等价：ln -s <已有模型目录> models/faster-whisper-medium

# 法 2：每次跑时显式指定
$PY transcribe.py <input> --model-dir "C:\Users\<你>\.cache\huggingface\manual\Systran\faster-whisper-medium"
```

> `models/` 已 gitignore；junction/symlink 不占额外空间。

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

# 指定档位 / 指定模型目录 / 强制 whisper / 复用浏览器登录态（B站字幕、抖音、小红书）
$PY transcribe.py <url> --model large-v3-turbo
$PY transcribe.py <url> --model-dir /path/to/faster-whisper-medium
$PY transcribe.py <url> --force-whisper
$PY transcribe.py <url> --cookies-from-browser chrome     # chrome/edge/firefox（先退出该浏览器）
$PY transcribe.py <url> --cookies cookies.txt             # 或传统 cookies 文件
$PY transcribe.py <url> --impersonate off                  # 关闭 TLS 拟真（默认按平台档案自动）
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

- **B 站字幕需登录 cookie**（无 cookie 时字幕轨拿不到，全靠本地 whisper）：`--cookies-from-browser chrome` 最省事
- **抖音/小红书被拦**：确认 ①浏览器已登录 ②读取 cookie 时浏览器已退出 ③装了 curl-cffi（否则无 TLS 拟真）——仍失败说明进风控期，走录屏/文案复制
- **`--cookies-from-browser` 读不到 cookie**：Windows 下 Chrome/Edge 运行中会锁 cookie 数据库，先完全退出浏览器再跑
- **长视频转录耗时约 1:1 实时**（CPU int8 medium 档）——一律后台跑，不占前台
- **转录产物立刻落盘**（`--out` 直接指向 `study/<博主>-apprentice/<标题>/`）——临时目录会被清
- **转录准确度低于粘贴文本**（错字/漏字/标点不准）——能用"文案提取小程序/字幕导出"就别用 whisper
- **模型在线下载在国内大概率失败**——按「模型下载」节预下载到 `models/`，一劳永逸
- 代理环境注意：国内平台下载常需绕过系统代理（NO_PROXY）

## 输出契约

transcript.md 含：来源 URL/文件名 + 时长 + 转录全文（段落版）+ 转录方式标注（字幕轨 zh-Hans (manual/auto-ASR) / whisper-<model>(local/hw 配置)）。
