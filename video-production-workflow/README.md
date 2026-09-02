<div align="center">

# video-production-workflow · 视频制作管线

**把"写完稿之后怎么做成片"变成有阶段、有交接、有审核闸门的制作系统**

终稿 → 分镜 → 粗剪 → 字幕校对 → 剪映草稿 → 素材 → 精剪 → B-roll 分析与生成 → 装配成片 QA

[![Version](https://img.shields.io/badge/version-0.7.0-blue)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-13%20子%20skill-059669)](#-主要子-skill)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20OpenCode%20·%20Codex%20·%20Cursor-supported-8b5cf6)](#-第一次使用)

</div>

---

> 📦 本系统是 [Huanyu-Skills 合集](../)的一员——6 套 Agent skill 系统，可独立使用，也可互相配合。

常见的视频制作问题不是缺一个工具，而是**工具之间没有清晰的交接**：

- 分镜表没有告诉剪辑师哪些画面是 A-roll、哪些是 B-roll；
- 转录字幕、校对字幕和精剪 SRT 混在一起，时间码逐步失真；
- 剪映草稿、下载素材、Remotion 工程和最终成片散落在不同目录；
- B-roll 只是按关键词找素材，没有先判断这句话是否值得插画面；
- 动效工具直接参与整片剪辑，导致时间线、字幕和素材责任混乱。

这套合集把流程固定为一条**有交接契约的管线**：

```text
终稿
  → 分镜与素材路由
  → A-roll 转录粗剪
  → 字幕校对
  → 剪映 Draft
  → 外部素材获取
  → 剪映精剪并输出 SRT
  → B-roll 机会分析
  → B-roll 生成
  → B-roll 装配与成片 QA
```

## 🧩 主要子 skill

| 子 skill | 负责什么 | 不负责什么 |
|---|---|---|
| `video-rough-cut` | 转录（默认 faster-whisper）、按文稿和词级时间码剪辑、FFmpeg 合成、最终自检 | 不替用户决定每条 B-roll 的审美方案 |
| `video-caption-correct` | 校对 ASR、识别口误、生成删除建议 | 不替代剪映内部最终精剪 |
| `video-jianying-draft` | 生成剪映原生 Draft（Windows + macOS；草稿自包含、同名素材防错链、重叠音频自动分道、剪映运行检测） | 不负责内容策划和 B-roll 机会判断 |
| `b-roll-finder` | 判断哪里值得插 B-roll、定义视觉命题和素材路由 | 不替用户做最终审美选择 |
| `b-roll-generate` | 调度真实素材、拼贴路线、Remotion、HyperFrames | 不编辑整条主视频 |
| `video-polish` | 装配 B-roll、音效、音乐和字幕，输出成片 | 不静默删除用户已确认的素材 |
| `video-skill-optimize` | 从任务和对话记录证据，生成并验证有界 Skill 候选 | 不自动采纳，不用训练案例冒充留出验证 |

每个阶段交接有契约（`shared-references/handoff-contracts.md`）、目录有规范（`shared-references/video-folder-schema.md`），完整规范见 [SKILL.md](SKILL.md)。

---

## 📦 安装（写给完全没接触过 AI 工具的你）

整个安装分 4 步：**① 装好 AI 编程助手 → ② 放好本 Skill 文件夹 → ③ 一键安装依赖和模型 → ④ 配置密钥（可选）**。跟着做就行，每步都有说明。

### 第 0 步：先弄清楚两个概念

| 名词 | 是什么 | 例子 |
|---|---|---|
| **AI Agent（编程助手）** | 能帮你操作电脑、读写文件的 AI 助手软件，本 Skill 的"大脑" | Claude Code、OpenCode、Codex CLI、Cursor |
| **Skill（技能）** | 教会 Agent 做某类工作的说明书文件夹，放到指定位置 Agent 就会自动使用 | 本项目 `video-production-workflow` |

> 你至少需要安装并登录其中一个 Agent，才能使用本 Skill。Agent 一般按模型用量向官方付费，与本 Skill 无关（本 Skill 免费、开源）。

### 第 1 步：把本 Skill 放到 Agent 能读到的位置

**方式一：从 GitHub 获取（需要安装 [Git](https://git-scm.com/downloads)）**

```bash
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
```

**方式二：直接下载文件夹（购买/获赠/网盘）**，跳过 Git。

然后把它复制到你 Agent 的 skills 目录（任选其一位即可，具体路径以你使用的 Agent 官方文档为准）：

| Agent | skills 目录（`<用户名>` 换成你的） |
|---|---|
| Claude Code | `C:\Users\<用户名>\.claude\skills\`（macOS/Linux：`~/.claude/skills/`） |
| OpenCode | 项目或全局 `.opencode/skills/` |
| Cursor / Codex | 项目内任意目录，用 `AGENTS.md` 指向它 |

复制后最终路径应类似：

```text
C:\Users\<用户名>\.claude\skills\video-production-workflow\
├── SKILL.md          ← Agent 读的入口说明书
├── scripts\          ← 所有可执行脚本
├── templates\        ← 各阶段交接文件模板
└── ...
```

### 第 2 步：一键安装依赖 + 下载 AI 模型

打开终端（Windows 用 **PowerShell**：开始菜单搜 "PowerShell" 回车；macOS 用"终端"），进入 Skill 目录：

```powershell
# Windows 示例（路径换成你的实际位置）
cd C:\Users\<用户名>\.claude\skills\video-production-workflow
```

运行一键安装脚本：

**Windows（PowerShell）：**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup\install.ps1
```

国内网络推荐加 `-Mirror`（清华镜像加速）：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup\install.ps1 -Mirror
```

**macOS / Linux（终端）：**

```bash
bash scripts/setup/install.sh        # 国内网络加 -mirror
```

脚本会自动完成：

1. 安装 **uv**（Python 包管理器，自动管理 Python 3.11，无需你装 Python）；
2. 创建独立虚拟环境 `.venv` 并安装全部 Python 依赖（含 PyTorch GPU 版，首次约 5-15 分钟）；
3. 检查 **FFmpeg**（视频处理）和 **Node.js**（Remotion 动效需要，18+），缺失时提示一键安装；
4. 询问是否下载 **AI 转录模型**（默认只下载 faster-whisper large-v3，约 3GB）。

> 💡 中途提示要下载什么就输入 `y` 回车。装完 FFmpeg/Node 后按提示**重开一次 PowerShell** 再继续。

#### 模型下载说明（国内/国外自动选源）

模型默认下载到 **Skill 目录下的 `models\`**（不进系统缓存，方便备份和迁移）。安装脚本会自动调用，也可以随时单独运行：

```powershell
# 自动判断网络：国外走 HuggingFace，国内走魔搭 ModelScope
uv run python scripts\setup\download_models.py --source auto

# 手动指定源（国内推荐 modelscope，国外推荐 huggingface）
uv run python scripts\setup\download_models.py --source modelscope
uv run python scripts\setup\download_models.py --source huggingface

# 可选：追加备选 whisper 引擎的模型 / legacy Fun-ASR
uv run python scripts\setup\download_models.py --include whisper
uv run python scripts\setup\download_models.py --include funasr

# 只查看已下载状态
uv run python scripts\setup\download_models.py --list
```

| 模型 | 是否默认 | 用途 |
|---|---|---|
| faster-whisper large-v3（约 3GB） | ✅ 默认下载 | 默认转录引擎，Windows 支持好（无显卡也能用 CPU int8） |
| openai-whisper large-v3（约 2.9GB） | 可选 `--include whisper` | 备选引擎：`transcribe.py --engine whisper` |
| Fun-ASR-Nano（约 2GB） | 可选 `--include funasr` | legacy，仅 `funasr_srt.py` 用，需 `uv sync --extra funasr` |

下载中断不要紧：重新运行同一命令会跳过已完成的部分继续。

#### 手动安装（不想用脚本的话）

```powershell
# 1. 安装 uv：Windows 在 PowerShell 执行
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
#    macOS/Linux: 
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 创建环境并装依赖（在 Skill 根目录）
uv venv .venv --python 3.11
uv sync
```

FFmpeg 手动安装：Windows 用 `winget install Gyan.FFmpeg`（或到 [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) 下载后把 bin 加入 PATH）；macOS 用 `brew install ffmpeg`。Node.js 到 [nodejs.org](https://nodejs.org/) 装 LTS 版。

### 第 3 步：配置密钥（可选）

Skill 根目录有 `.env.example`，复制一份并重命名为 `.env`：

```powershell
Copy-Item .env.example .env
```

**本地转录（faster-whisper/whisper）不需要任何密钥。** 只有用到以下功能才需要填（打开 `.env` 把等号后面填上即可）：

| 想用的功能 | 需要填的变量 | 去哪申请 |
|---|---|---|
| Pexels 图片/视频搜索 | `PEXELS_API_KEY` | pexels.com（免费） |
| Unsplash 图片搜索 | `UNSPLASH_ACCESS_KEY` | unsplash.com（免费） |
| Pixabay 图片/视频 | `PIXABAY_API_KEY` | pixabay.com（免费） |
| Gemini AI 拼贴 B-roll | `GEMINI_API_KEY` | Google AI Studio |
| 火山引擎云端转录 | `VOLCENGINE_API_KEY` | 火山引擎控制台 |

> ⚠️ `.env` 里是你的私人密钥，**分发/转让本 Skill 前务必删除它**。

### 安装自检

```powershell
uv run python -c "import faster_whisper; print('faster-whisper OK')"
uv run python scripts\setup\download_models.py --list
uv run python scripts\video-status\status.py --help
```

三条都有正常输出 = 安装成功。🎉

### 常见问题（FAQ）

| 问题 | 解决 |
|---|---|
| `uv` 提示找不到命令 | 安装后**关闭并重开 PowerShell/终端**再试 |
| 依赖下载超时 | 用国内镜像重跑：`install.ps1 -Mirror`（macOS：`install.sh -mirror`） |
| `ffmpeg` 找不到 | winget/brew 安装后**重开终端**；或手动下载后确认 bin 目录在 PATH 里 |
| 模型下载很慢/失败 | 换源重试：`--source modelscope`（国内）或 `--source huggingface`；断点会续传 |
| 没有 NVIDIA 显卡 | 不影响：faster-whisper 自动用 CPU int8，只是转录慢一些 |
| Remotion 报 Node 版本错误 | 安装 Node.js 18+（`winget install OpenJS.NodeJS.LTS` 或 nodejs.org） |

---

## 🚀 第一次使用

在你的**视频项目目录**（比如 `D:\我的视频\第1期_xxx\`，建议新建一个专门文件夹）打开 Agent，直接说：

```text
初始化视频制作管线
```

或：

```text
/video-init D:\我的视频\EP001_视频标题
```

初始化会检查项目路径，创建标准目录、`.video-workflow-state.json`、`WORKFLOW.md` 和 `STATUS.md`，不会覆盖已有文件。

## 💬 日常用法

```text
规划这篇视频的分镜
粗剪 Raw 里的这些视频
根据原稿校对字幕
创建剪映草稿
按 asset_request_list 下载素材
分析精剪 SRT 哪些地方值得做 B-roll
为 B-roll-003 生成 Remotion 动效
把这些 B-roll 放到对应口播位置并输出预览
视频状态
记录这次协作的问题并优化视频 skill
```

## ✅ 适合 / ❌ 不适合

**✅ 适合**：已经写完稿、要把口播/讲解视频稳定做成片的创作者；用剪映做主剪辑、想让 AI 负责转录、字幕、B-roll 与装配的流程党；想要阶段可追溯、交接不丢信息的系列视频生产（如播客、课程、测评）。

**❌ 不适合**：从零想选题、写稿的内容策划（配合 founder-ip / oracle-bone 等上游 skill）；纯手机随手拍的轻量剪辑；期望一键全自动出片——审美决策仍由你拍板。

## 📄 License

MIT。商用、改造、闭源接入都行。

---

## 👤 关于作者 · 呼风唤雨的焕羽

我是**呼风唤雨的焕羽**，**工程合规 AI 创业者**——工程管理专业出身，从央企经营部走出来，现在经营一人公司（OPC），用 AI Agent 重做工程本行（合同审查 / 招投标合规 / 资质管理），全过程 [Build in Public](https://github.com/Huanyu-Hibiki)。本 skill 的完整手把手教程与实战演示，都在我的视频里：

| 平台 | 账号 |
|---|---|
| 小红书 | 呼风唤雨的焕羽 |
| B站 | 呼风唤雨的焕羽 |
| 视频号 | 呼风唤雨的焕羽 |
| 抖音 | 呼风唤雨的焕羽 |

<div align="center">

🔍 **四个平台全同名，搜索「呼风唤雨的焕羽」看视频教程**

<img src="assets/gzh-qrcode.png" width="520" alt="微信搜一搜：呼风唤雨的焕羽">

<sub>微信扫一扫 / 搜一搜「**呼风唤雨的焕羽**」关注公众号，第一时间获取 skill 更新与 AI 实战干货</sub>

</div>
