<div align="center">

# video-production-workflow · 视频制作管线

**把"写完稿之后怎么做成片"变成有阶段、有交接、有审核闸门的制作系统**

终稿 → 分镜 → 粗剪 → 字幕校对 → 剪映草稿 → 素材 → 精剪 → B-roll 分析与生成 → 装配成片 QA

[![Version](https://img.shields.io/badge/version-0.6.0-blue)](CHANGELOG.md)
[![Skills](https://img.shields.io/badge/skills-13%20子%20skill-059669)](#-主要子-skill)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20OpenCode%20·%20Codex%20·%20Cursor-supported-8b5cf6)](#-第一次使用)



---

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
| `video-rough-cut` | 转录、按文稿和词级时间码剪辑、FFmpeg 合成、最终自检 | 不替用户决定每条 B-roll 的审美方案 |
| `video-caption-correct` | 校对 ASR、识别口误、生成删除建议 | 不替代剪映内部最终精剪 |
| `video-jianying-draft` | 生成剪映原生 Draft（Windows + macOS；草稿自包含、同名素材防错链、重叠音频自动分道、剪映运行检测） | 不负责内容策划和 B-roll 机会判断 |
| `b-roll-finder` | 判断哪里值得插 B-roll、定义视觉命题和素材路由 | 不替用户做最终审美选择 |
| `b-roll-generate` | 调度真实素材、拼贴路线、Remotion、HyperFrames | 不编辑整条主视频 |
| `video-polish` | 装配 B-roll、音效、音乐和字幕，输出成片 | 不静默删除用户已确认的素材 |
| `video-skill-optimize` | 从任务和对话记录证据，生成并验证有界 Skill 候选 | 不自动采纳，不用训练案例冒充留出验证 |

每个阶段交接有契约（`shared-references/handoff-contracts.md`）、目录有规范（`shared-references/video-folder-schema.md`），完整规范见 [SKILL.md](SKILL.md)。

## 📦 安装

```bash
# 方式一：从 GitHub 获取
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
cp -r Huanyu-Skills/video-production-workflow <你的 skills 目录>/video-production-workflow

# 方式二：已拿到 skill 文件夹（购买 / 下载），直接复制进去
cp -r video-production-workflow <你的 skills 目录>/video-production-workflow
```

本合集依赖唯一 Python 环境，先在合集根目录初始化：

```powershell
cd "<合集根目录>"
uv venv .venv --python 3.11
uv sync
```

本机 API 密钥放 `.env`（参考 `.env.example` 配置）；**分发本合集时务必先删除 `.env`**——里面是你的密钥。

## 🚀 第一次使用

在视频项目目录或制作管线目录中调用：

```text
初始化视频制作管线
```

或：

```text
/video-init <视频项目根>\EP00X_视频标题
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

---

## 👤 关于作者 · 呼风唤雨的焕羽

我是**呼风唤雨的焕羽**，AI 实战博主，专注分享用 AI Agent 搭建一人公司工作流的真实过程。本 skill 的完整手把手教程与实战演示，都在我的视频里：

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

