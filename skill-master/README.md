<div align="center">

# skill-master · Skill 全生命周期管家

**一个 skill 从装进来、看懂它、写出来到养得好——五件事各有一个子 skill 负责**

盘点已装 skill · 第三方 skill 安全扫描 · 开源 skill 分析 · 从零编写新 skill · 迭代优化已有 skill

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](SKILL.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-5%20子%20skill-059669)](#-五个子-skill)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20OpenCode%20·%20Codex%20·%20Cursor-supported-8b5cf6)](#-安装)

</div>

---

> 📦 本系统是 [Huanyu-Skills 合集](../)的一员——6 套 Agent skill 系统，可独立使用，也可互相配合。

skill-master 是一个 **skill 合集路由器**（总协议 + 路由表）：收到请求只做一件事——按路由表分发到对应 `skills/sm-*/SKILL.md` 子 skill 执行。你在用 AI Agent 管理 skill 时需要的全套工具，都在这一个合集里。

## 🧭 五个子 skill

| 子 skill | 职责 | 触发词示例 | 产出 |
|---|---|---|---|
| `sm-manager` | 盘点本机各 Agent 已装的 skill（只读零修改） | "盘点skill" / "我装了哪些skill" | skill 清单 + 跨 Agent 重复对比 + 健康看板 |
| `sm-security` | 第三方 skill 安装前的安全扫描与复核 | "检查这个skill安全吗" / "有没有后门" | 0-100 扫描报告 + SAFE / CAUTION / DO NOT INSTALL 结论 |
| `sm-analyzer` | 开源 skill 的结构、工作流分析 | "分析这个skill" / "它怎么工作的" | HTML 分析报告（功能 / 架构 / 工作流 / 反模式） |
| `sm-writer` | 从零访谈需求、起草并落盘新 skill | "帮我写个skill" / "新做一个skill" | 新 skill 目录（访谈 → 草稿 → 确认后落盘） |
| `sm-optimizer` | 已有 skill 的四维诊断与迭代优化 | "优化这个skill" / "skill不触发" | 四维诊断 + 优化计划（确认后实施 + before/after 验证） |

**防误触发**：判别标准一句话——操作对象是否是一个 skill 目录（含 `SKILL.md` 的技能目录）。"优化这段 Python 代码"、"扫描端口"、"盘点库存"这类请求对象不是 skill，合集不接。

## 🛡️ 总协议（三原则）

1. **脚本做确定性事**：枚举、校验、渲染、统计——结果必须可复现的操作交给 `scripts/`。
2. **LLM 做判断事**：解读数据、权衡方案、撰写分析、降低误报——语义理解留给 Agent。
3. **危险操作必须确认**：写文件、删文件、改配置之前，先向用户展示将要做什么，确认后再动手；宁可多问，不可先斩后奏。

子 skill 之间有明确转介规则（如 manager 只读、发现健康问题只给建议不代改；安全扫描发现质量问题转介 optimizer），不越界代办。

## 📦 安装

```bash
# 方式一：从 GitHub 获取
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
cp -r Huanyu-Skills/skill-master <你的 skills 目录>/skill-master

# 方式二：已拿到 skill 文件夹（购买 / 下载），直接复制进去
cp -r skill-master <你的 skills 目录>/skill-master
```

| Runtime | skills 目录 |
|---|---|
| Claude Code | `~/.claude/skills/` |
| OpenCode | `~/.opencode/skills/` |
| Codex / Cursor / 其他 | 各自的 skills 目录 |

**可选**：盘点、编写、优化等核心能力开箱即用；安全扫描与分析的脚本增强能力需要 Python 3.11+，在合集目录执行 `uv sync`（或 Windows 双击 `install.ps1`）安装依赖。

## 🚀 快速开始

对 Agent 说一句话即可：

```
盘点我装了哪些 skill
检查这个 skill 安全吗：<路径>
分析这个开源 skill：<路径>
帮我写一个 <主题> 的 skill
优化这个 skill：<路径>
```

## ✅ 适合 / ❌ 不适合

**✅ 适合**：skill 越装越多、需要体检和去重的人；装第三方 skill 前想先扫一遍后门的安全党；想研究优秀开源 skill 的写法、或从零做自己 skill 的创作者。

**❌ 不适合**：对象不是 skill 目录的一般编程 / 文档 / 运维任务——路由器会按负例表拒绝，按普通任务处理。

## 📄 License

MIT

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

