<div align="center">

# Huanyu-Skills · 呼风唤雨的焕羽的 Agent Skills 合集

**6 套经过实战打磨的 AI Agent skill 系统：创始人 IP 战略 → 内容校准循环 → 获客闭环 → 深度阅读 → skill 工程 → 视频制作**

*Production-grade AI agent skills for Claude Code / OpenCode / Codex / Cursor — open-sourced Build-in-Public from a one-person company (OPC).*

[![Skills](https://img.shields.io/badge/skills-6%20%E5%A5%97%E7%B3%BB%E7%BB%9F-059669)](#-合集一览)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20OpenCode%20·%20Codex%20·%20Cursor-supported-8b5cf6)](#-快速开始)
[![Release](https://img.shields.io/badge/release-v1.0.0-blue)](https://github.com/Huanyu-Hibiki/Huanyu-Skills/releases)
[![GitHub Stars](https://img.shields.io/github/stars/Huanyu-Hibiki/Huanyu-Skills?style=flat&color=ffd700)](https://github.com/Huanyu-Hibiki/Huanyu-Skills/stargazers)
[![License](https://img.shields.io/badge/license-%E6%8C%89%20skill%20%E5%90%84%E5%BC%82-lightgrey)](#-license)

</div>

---

给 AI Agent（Claude Code / OpenCode / Codex CLI / Cursor 等）用的实战 skill 合集。每个目录是一套独立系统，放进你的 skills 目录即可使用。它们不是玩具 demo——每一套都来自我经营一人公司（OPC）的真实工作流，Build in Public 全过程公开，配合我的视频教程食用效果最佳。

## 📦 合集一览

| Skill | 一句话 | 子 skill | 版本 | License |
|---|---|---|---|---|
| [founder-ip](founder-ip/) | 创始人 IP 战略层系统（Founder IP Strategy）：战略 / 人设 / 内容漏斗 / 商业模式 / OPC 五层一次想清楚 | 5 | 1.2.0 | AGPL-3.0 |
| [oracle-bone](oracle-bone/) | 内容预测校准循环（Content Calibration Loop）：打分 → 盲预测 → 发布 → 复盘 → 进化你自己的爆款公式 | 26 | 1.0.0 | MIT |
| [pulsehub](pulsehub/) | 获客系统（Lead Generation System）：16 个 skill 四层闭环 + 随使用积累的"项目大脑" | 16 | 1.0.0 | MIT |
| [shendu-yuedu](shendu-yuedu/) | 深度阅读系统（Deep Reading System）：把"读完就忘"变成可调用的个人知识 Wiki | 6 | 1.0.0 | MIT |
| [skill-master](skill-master/) | skill 全生命周期管家（Skill Lifecycle Manager）：盘点 / 安全扫描 / 分析 / 编写 / 优化 | 5 | 1.0.0 | MIT |
| [video-production-workflow](video-production-workflow/) | 视频制作管线（Video Production Pipeline）：终稿 → 分镜 → 粗剪 → 剪映 → B-roll → 成片 QA | 13 | 0.6.0 | MIT |

<details>
<summary><b>📖 English</b></summary>

**Huanyu-Skills** is a collection of 6 production-grade AI agent skill systems, extracted from a real one-person-company (OPC) workflow and open-sourced Build-in-Public. Works with any skills-compatible agent: Claude Code, OpenCode, Codex CLI, Cursor.

| Skill | What it does |
|---|---|
| [founder-ip](founder-ip/) | Founder IP strategy layer: strategy / persona / content funnel / business model / OPC pipeline |
| [oracle-bone](oracle-bone/) | Content calibration loop: score → blind-predict → publish → review → evolve your own hit formula |
| [pulsehub](pulsehub/) | Lead generation system: 16 skills in 4 layers + a "project brain" that grows with use |
| [shendu-yuedu](shendu-yuedu/) | Deep reading system: turn "read and forget" into a personal knowledge wiki of callable skills |
| [skill-master](skill-master/) | Skill lifecycle manager: inventory / security scan / analyze / write / optimize skills |
| [video-production-workflow](video-production-workflow/) | Video production pipeline: script → storyboard → rough cut → JianYing (CapCut) draft → B-roll → final QA |

```bash
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
cp -r Huanyu-Skills/oracle-bone ~/.claude/skills/oracle-bone   # or your agent's skills dir
```

</details>

## 🤝 它们怎么配合

```
founder-ip 定战略（为什么做、人设、漏斗、变现）
      ↓
oracle-bone 跑每周执行循环（选题 → 打分 → 盲预测 → 复盘 → 进化公式）
      ↓
pulsehub 把内容变成客户（画像 / 选题 / 文案 / 脚本 / 私域 / 评论线索）
      ↓
video-production-workflow 把稿子稳定做成片

shendu-yuedu 管输入：读书读完变技能，喂给上面所有环节
skill-master 管技能本身：这套系统的"系统"，装、扫、析、写、优
```

每套也完全独立可用，按需取用即可。

## 🚀 快速开始

```bash
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git

# 把想要的 skill 复制进你的 Agent skills 目录，例如：
cp -r Huanyu-Skills/oracle-bone ~/.claude/skills/oracle-bone    # Claude Code
# OpenCode: ~/.opencode/skills/  ·  Codex: ~/.codex/skills/
```

然后对 Agent 说人话即可（"初始化 oracle-bone" / "盘点我装了哪些 skill" / "帮我写个 skill"…），各 skill 的详细用法见各自目录的 README。

> 部分 skill 有可选依赖（如 video-production-workflow 需要 `uv sync` 初始化 Python 环境），见各自 README 的安装节。

## 👤 关于作者 · 呼风唤雨的焕羽

我是**呼风唤雨的焕羽**，**工程合规 AI 创业者**——工程管理专业出身，从央企经营部走出来，现在经营一人公司（OPC），用 AI Agent 重做工程本行（合同审查 / 招投标合规 / 资质管理），全过程 [Build in Public](https://github.com/Huanyu-Hibiki)。这个仓库不是 side project——每套系统都在我的一人公司里每天真实运转。

内容母题：**「AI 时代，我的工程青春谁做主」**——工程人如何在 AI 时代重新拿回职业主动权。这里每一套 skill 的完整手把手教程与实战演示，都在我的视频里：

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

## 📄 License

各 skill 协议不同（见各自目录的 LICENSE）：founder-ip 为 AGPL-3.0，oracle-bone / pulsehub / shendu-yuedu / skill-master / video-production-workflow 为 MIT。
