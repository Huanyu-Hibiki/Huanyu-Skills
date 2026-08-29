<div align="center">

# founder-ip · 创始人 IP 战略系统

**为"非娱乐类创始人 IP"设计的战略层系统：战略 / 人设 / 内容漏斗 / 商业模式 / OPC 五层，一次想清楚**

5 个子 skill · 徐沪生方法论 + dontbesilent 实战库 + PLG 三源印证 · 产出战略文档喂给执行循环

[![Version](https://img.shields.io/badge/version-1.2.0-blue)](SKILL.md)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](LICENSE)
[![Agents](https://img.shields.io/badge/Claude%20Code%20·%20OpenCode%20·%20Codex%20·%20Cursor-supported-8b5cf6)](#-安装)



---

创始人 IP ≠ 网红 IP。娱乐网红那套（抄爆款、蹭热点、搞笑耍宝、每天 10 条盲盒）对创始人不仅无效，而且有毒。这套系统专门为**产品已上线、通过内容获客**的创始人 / OPC / 主理人设计，尤其是垂直专业领域（工程 / 法律 / 医疗 / 教育等）的非娱乐型 IP。

## 🧭 这是什么

一套**战略层 skill 系统**，帮创始人想清楚 5 件事：

| # | 子 skill | 解决什么 | 使用频率 |
|---|---|---|---|
| 1 | `ip-strategy` | 为什么做个人 IP：立项决心、防网红思维坑、时间承诺、成功标准 | 一次性 + 季度回顾 |
| 2 | `ip-persona` | 人设怎么定：内容型/专家型/真实型、起源故事、表达风格 | 一次性 + 半年回顾 |
| 3 | `ip-content-funnel` | 内容漏斗怎么设计：三轨比例（A 破圈 / C 认知 / B 转化）、系列定位、利他选题库、GEO 长尾覆盖 | 半年/年度更新 |
| 4 | `ip-business-model` | 商业模式怎么搭：咨询枢纽、流量/转化视频分离、变现路径 | 季度更新 |
| 5 | `ip-opc-system` | OPC 流水线怎么整合：生产日程（示例基线 2 天 1 期）、AI 协作边界、瓶颈优化 | 持续优化 |

**与执行层的分工**：founder-ip 产出的战略文档，作为每周执行循环（选题 / 打分 / 预测 / 拍摄 / 复盘，如 `oracle-bone`）的**上下文和约束**——战略层不重造执行层轮子。

## ✨ 核心特性

- **方法论三源 + 一印证**：徐沪生《个人IP全流程拆解》（主方法论）+ dontbesilent 实战知识库（商业变现）+ PLG 三大增长资产（实战印证）+ 你的访谈档案（最高优先级）。三方一致 = 强信号，所有建议可追溯到源，不凭空发明。
- **访谈式建档**：`interview-profile.md` 记录你的产品、用户、资源与偏好，所有子 skill 按你的具体情况给建议，不输出通用鸡汤。
- **战略文档分级保护**：战略备忘录 / 人设宪章严格不可改；商业画布 / 内容漏斗季度可调但须附数据依据，变更留痕（`strategy-immutability.md`）。
- **内置国内 GEO 指南**：面向 AI 搜索（Kimi / 豆包 / DeepSeek / 元宝 / 秘塔等）的优化动作与月度自检，让内容在 AI 时代也能被检索到。

## 📦 安装

任一 skills-compatible 运行时（Claude Code / OpenCode / Codex / Cursor 等）均可：

```bash
# 方式一：从 GitHub 获取
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
cp -r Huanyu-Skills/founder-ip <你的 skills 目录>/founder-ip

# 方式二：已拿到 skill 文件夹（购买 / 下载），直接复制进去
cp -r founder-ip <你的 skills 目录>/founder-ip
```

| Runtime | skills 目录 |
|---|---|
| Claude Code | `~/.claude/skills/` |
| OpenCode | `~/.opencode/skills/` |
| Codex | `~/.codex/skills/` |
| 通用（多 agent 共享） | `~/.agents/skills/` |

装好后初始化你的访谈档案（每个使用者一份，含个人数据）：

```bash
cd <你的 skills 目录>/founder-ip/shared-references/
cp interview-profile.example.md interview-profile.md
# 编辑 interview-profile.md 填入你的情况；或直接跑 /ip-strategy，系统会引导你完成访谈
```

> `shared-references/` 已自包含核心方法论精华，开箱即用；如拥有徐沪生原书 / dontbesilent 原库等第三方版权内容，可另行配置用于原文回查，不配置不影响运行。

## 🚀 快速开始

跑完 5 步，创始人 IP 的战略层就立起来了：

```
1. /ip-strategy       → 锁定战略 + 立项决心（最重要，所有后续的根基）
2. /ip-persona        → 基于战略定人设
3. /ip-business-model → 基于战略 + 人设定变现路径
4. /ip-content-funnel → 基于人设 + 商业模式定内容漏斗
5. /ip-opc-system     → 整合所有，接上你的每周执行循环
```

**定期复盘**：每月 `/ip-opc-system --optimize`；每季度战略 / 商业模式 / 内容漏斗 `--review`；每半年人设 `--review`。

## ✅ 适合 / ❌ 不适合

**✅ 适合**：产品已上线、想通过内容获客的创始人 / OPC / 主理人；垂直专业领域的非娱乐型 IP；想清楚"为什么做、怎么做、怎么变现"再动手的人。

**❌ 不适合**：娱乐网红路线；纯执行层需求（单条视频的选题 / 脚本 / 复盘请用 `oracle-bone` 等执行循环工具）；只想蹭热点涨粉、不考虑变现的玩法。

## 📄 License

AGPL-3.0

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

