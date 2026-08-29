<div align="center">

# pulsehub · 获客 skill 系统

**从项目初始化到线索转化的完整获客闭环：16 个 skill 分 4 层 + 一个随使用越养越肥的"项目大脑"**

画像 / 关键词 / 选题 / 文案 / 脚本 / 私域承接 / 评论线索 · 去 AI 味 · 自进化

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](SKILL.md)
[![Skills](https://img.shields.io/badge/skills-16%20·%204%20layers-059669)](#-架构四层)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20OpenCode%20·%20Codex%20·%20Cursor-supported-8b5cf6)](#-安装)



---

PulseHub 是一套**完整的获客 skill 系统**。输入你的产品/服务与获客目标，输出用户画像、获客关键词矩阵、爆款选题、文案、视频脚本、私域承接 SOP 与评论区线索机会。所有产出沉淀进共享的"项目大脑"（`~/.pulsehub/archive/<项目名>/`），越用越懂你的业务。

## 🧭 架构（四层）

```
Layer 1: 入口      → pulse-router（诊断方向清晰度，路由分发）
Layer 2: 数据      → pulse-discover / resolve / enrich / deliver（发现帖子、标准化、信号评分、报告）
Layer 3: 业务      → pulse-init / insight / keywords / topics / copywrite / script / private / leads
Layer 4: 质检进化  → pulse-humanize / evolve / review
```

## 📋 16 个 skill 一览

| 层 | Skill | 干什么 |
|---|---|---|
| 入口 | `pulse-router` | 诊断产品方向清晰度，路由到对应 skill |
| 数据 | `pulse-discover` | 通过 RSSHub / Chrome MCP 发现帖子 |
| 数据 | `pulse-resolve` | 标准化 URL（5 平台） |
| 数据 | `pulse-enrich` | 信号检测 + 评分（关键词 + LLM） |
| 数据 | `pulse-deliver` | 生成 Markdown 报告 + 可点击 URL |
| 业务 | `pulse-init` | 初始化项目 + 建立项目大脑 |
| 业务 | `pulse-insight` | 付费用户洞察 + 痛点提炼 |
| 业务 | `pulse-keywords` | 获客关键词矩阵 |
| 业务 | `pulse-topics` | 爆款选题（调 pulse-discover 发现热门） |
| 业务 | `pulse-copywrite` | 文案生成（读「个人风格.md」对齐你的文风） |
| 业务 | `pulse-script` | 视频脚本（口播稿 + 分镜） |
| 业务 | `pulse-private` | 私域承接 SOP + 话术资产 |
| 业务 | `pulse-leads` ⭐ | 评论线索抓取（核心集成点） |
| 质检 | `pulse-humanize` | 去 AI 味（24 模式 + 个人风格对齐） |
| 质检 | `pulse-evolve` | 自进化（按真实数据迭代 skill） |
| 质检 | `pulse-review` | 极简复核（体系体检） |

## 🧠 项目大脑（6 份档案）

`pulse-init` 会把 6 份模板复制到 `~/.pulsehub/archive/<项目名>/`，之后所有 skill 都读写这里：

| 档案 | 作用 |
|---|---|
| `项目档案.md` | Hub：基本信息 + 累积产出索引（含「主平台」「定位协议」两个跨 skill 字段） |
| `人群语料库.md` ⭐ | 真实用户原话 / 痛点 / 拒绝理由 |
| `爆款素材库.md` | 拆解的爆款结构 / 钩子公式 |
| `话术资产.md` | 私域话术（带效果标签） |
| `数据反馈.md` ⭐ | 真实运营数据（自进化的燃料） |
| `个人风格.md` | 你的文风指纹 |

登记了「定位协议」（品牌手册 / IP 对齐 / 内容红线）→ 所有 skill 先读并优先服从；没登记 → 按档案自身定位执行。

## 📦 安装

```bash
# 方式一：从 GitHub 获取
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
cp -r Huanyu-Skills/pulsehub ~/.claude/skills/pulsehub   # 或你的 skills 目录

# 方式二：已拿到 skill 文件夹（购买 / 下载），直接复制进去
cp -r pulsehub <你的 skills 目录>/pulsehub
```

**兼容性**：任何能读 `SKILL.md` 的 Agent 都能用——OpenCode（读 `AGENTS.md`，最佳适配）、Claude Code、Cursor（`@workspace` 索引）、OpenClaw 及自定义 Agent。单个 skill 被单独复制出去时，共享脚本不可达属预期，各 `SKILL.md` 已内置人工/浏览器替代路径。

## 🚀 快速开始

首次运行推荐顺序：

```
1. pulse-router     → 我准备好了吗？
2. pulse-init       → 建立项目大脑（采集主平台 / 定位协议）
3. pulse-insight    → 搞懂你的用户
4. pulse-topics     → 找到该发什么
5. pulse-copywrite  → 写出内容
6. pulse-leads      → 找到评论区线索机会
7. pulse-humanize   → 去 AI 味质检
8. （后期）pulse-evolve → 用真实数据反哺系统
```

对 Agent 直接说需求即可（"我想找客户" / "帮我写条文案" / "抓一下评论线索"），路由层自动分发。

## ✅ 适合 / ❌ 不适合

**✅ 适合**：有产品/服务、靠内容获客的独立开发者 / OPC / 小团队；想把获客从"凭感觉"变成有档案、有数据、可进化的循环的人。

**❌ 不适合**：没有产品只想涨粉的娱乐账号；需要全自动群控、批量私发等灰产玩法——本系统只做合规的内容获客与评论区线索。

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

