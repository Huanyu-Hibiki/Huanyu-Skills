<div align="center">

# shendu-yuedu · 深度阅读系统

**把"读完就忘"变成"读完变成可调用的技能"——6 个 skill 组成的阅读闭环，越读越聪明**

拆解书籍 → 带着问题预读 → 结构化精读 → 实践转化 → 自进化 · 个人知识 Wiki 三层架构

[![Version](https://img.shields.io/badge/version-1.0.0-blue)](https://github.com/Huanyu-Hibiki/Huanyu-Skills/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Skills](https://img.shields.io/badge/skills-6%20·%20阅读闭环-059669)](#-目录)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20OpenCode%20·%20Codex%20·%20Cursor-supported-8b5cf6)](#-安装)

</div>

---

> 📦 本系统是 [Huanyu-Skills 合集](../)的一员——6 套 Agent skill 系统，可独立使用，也可互相配合。

输入一本书 / 一门课 / 一篇长文，输出结构化的个人 Wiki（分层目录 / 问题清单 / 知识卡片 / 实践转化出的可执行技能）。AI 只做结构化提炼，**绝不代写你的原始笔记**——它不替代阅读，只放大每一分钟阅读的杠杆。

## 🧭 工作流

```
#1 初始化 → #2 拆解书籍 → #3 预读 → #4 结构化精读 → #5 实践转化（产出可执行 skill）
                                                          ↓
                                      #6 自进化（按真实使用情况迭代那些技能）
```

每个 skill 独立可用，完成后自动推荐下一步。

## 📖 阅读大脑 · 三层架构

所有 skill 通过 `<知识库根>/阅读笔记/` 共享上下文，组织方式参照 Karpathy LLM Wiki 模式 + Google Open Knowledge Format（OKF）：

| 层 | 目录 | 谁写 | 规则 |
|---|---|---|---|
| **Raw 原始层** | `阅读笔记/…/摘抄.md` 等你的真实笔记 | 人 | **不可变**：AI 只读，提取知识但绝不改写 |
| **Wiki 沉淀层** | 拆解目录 / 问题清单 / 知识卡片 / 实践转化 / Hub 报告 | AI | LLM 全权维护：更新、交叉引用、标矛盾，人只审 |
| **Schema 约定层** | README + `<知识库根>/SKILL.md`（vault 级宪法） | 人×AI | 告诉 LLM 目录职责与工作流约定 |

知识库位置很灵活：会话里显式指定 → 当前项目有知识库标志 → 全局配置 `~/.shendu-yuedu/config.json` → 默认当前项目路径。#1 初始化时引导确定，之后跨会话记住。产出文件带 YAML frontmatter（OKF 约定），用 Obsidian 就用双链，其他编辑器用标准相对链接。

## 📋 目录

| # | Skill | 触发短语 |
|---|---|---|
| 1 | `sy-init` 初始化 | "阅读初始化" / "开始读一本书" / "建阅读档案" |
| 2 | `sy-decompose` 拆解书籍 | "拆解这本书" / "精读目录" / "这书怎么读" |
| 3 | `sy-preread` 预读 | "预读" / "问题清单" / "带着问题读" |
| 4 | `sy-deepread` 结构化精读 | "整理笔记" / "知识卡片" / "结构化精读" |
| 5 | `sy-practice` 实践转化 | "实践转化" / "萃取技能" / "怎么用这本书" |
| 6 | `sy-evolve` 自进化 | "迭代技能" / "技能不好用" / "优化阅读技能" |

## 📦 安装

```bash
# 方式一：从 GitHub 获取
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
cp -r Huanyu-Skills/shendu-yuedu <你的 skills 目录>/shendu-yuedu

# 方式二：已拿到 skill 文件夹（购买 / 下载），直接复制进去
cp -r shendu-yuedu <你的 skills 目录>/shendu-yuedu
```

| Runtime | skills 目录 |
|---|---|
| Claude Code | `~/.claude/skills/` |
| OpenCode | `~/.opencode/skills/` |
| Codex / Cursor / 其他 | 各自的 skills 目录 |

## 🚀 快速开始

对 Agent 说：

```
阅读初始化
```

#1 会采访式引导：确定知识库位置 → 建目录骨架 → 登记在读书目。之后每读一本书：拆解 → 预读出问题清单 → 精读中整理知识卡片 → 读完萃取成可执行技能。所有输出都在你的知识库里，永远可检索。

**人 × AI 分工**：人负责真实阅读、记录想法、把技能用到真实场景、反馈好不好用；AI 负责拆解结构、设计问题、整理卡片、萃取与迭代技能。

## ✅ 适合 / ❌ 不适合

**✅ 适合**：读了很多书却"读完就忘"的人；想把书变成自己技能库的学习者；用 Obsidian / Typora / VS Code 管理笔记、想给笔记系统接上 AI 的人。

**❌ 不适合**：想让 AI 替你读书、代写笔记的捷径党——本系统的底线恰恰是 AI 不碰你的原始笔记。

## 📄 License

MIT

## 🙏 方法论来源

- 推理框架：Tree-of-Thoughts / Chain-of-Verification / Graph-of-Thoughts（#2-#5 各环节）
- 知识组织：Karpathy LLM Wiki 模式 + Google Open Knowledge Format
- 自进化：微软 SkillOpt（#6，把技能文档当可训练状态）

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

