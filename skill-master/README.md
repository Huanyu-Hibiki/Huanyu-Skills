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

## 📦 安装（写给完全没接触过 AI 工具的你）

整个安装分 3 步：**① 装好 AI 编程助手 → ② 放好本 Skill 文件夹 → ③ 安装脚本增强能力（可选）**。跟着做就行，每步都有说明。

### 第 0 步：先弄清楚两个概念

| 名词 | 是什么 | 例子 |
|---|---|---|
| **AI Agent（编程助手）** | 能帮你操作电脑、读写文件的 AI 助手软件，本 Skill 的"大脑" | Claude Code、OpenCode、Codex CLI、Cursor |
| **Skill（技能）** | 教会 Agent 做某类工作的说明书文件夹，放到指定位置 Agent 就会自动使用 | 本项目 `skill-master` |

> 你至少需要安装并登录其中一个 Agent，才能使用本 Skill。Agent 一般按模型用量向官方付费，与本 Skill 无关（本 Skill 免费、开源）。

### 第 1 步：把本 Skill 放到 Agent 能读到的位置

**方式一：从 GitHub 获取（需要安装 [Git](https://git-scm.com/downloads)）**

```bash
git clone https://github.com/Huanyu-Hibiki/Huanyu-Skills.git
```

**方式二：直接下载文件夹（购买/获赠/网盘）**，跳过 Git。

然后把它复制到你 Agent 的 skills 目录（任选其一位即可）：

| Agent | skills 目录（`<用户名>` 换成你的） |
|---|---|
| Claude Code | `C:\Users\<用户名>\.claude\skills\`（macOS/Linux：`~/.claude/skills/`） |
| OpenCode | 项目或全局 `.opencode/skills/` |
| Cursor / Codex | 项目内任意目录，用 `AGENTS.md` 指向它 |

复制后最终路径应类似：

```text
C:\Users\<用户名>\.claude\skills\skill-master\
├── SKILL.md          ← Agent 读的入口说明书
├── scripts\          ← 安全扫描 / 盘点 / 报告脚本
├── skills\           ← 5 个子 skill 的 SKILL.md
└── ...
```

**或者用一键安装脚本（自动创建链接，更新无需重复安装）：**

```powershell
cd C:\Users\<用户名>\.claude\skills\Huanyu-Skills\skill-master
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

| 参数 | 作用 |
|---|---|
| `-Target <路径>` | 指定其他 Agent 的 skills 目录 |
| `-Name <名称>` | 安装后的目录名（默认 `skill-master`） |
| `-Remove` | 移除已安装的链接 |
| `-WhatIf` | 预览模式，不实际执行 |

### 第 2 步：安装脚本增强能力（可选）

盘点、编写、优化等核心能力**开箱即用**，不需要任何额外安装。

安全扫描与分析的**脚本增强能力**需要 Python 3.12+。打开终端（Windows 用 **PowerShell**：开始菜单搜 "PowerShell" 回车），进入 Skill 目录：

```powershell
# Windows 示例（路径换成你的实际位置）
cd C:\Users\<用户名>\.claude\skills\skill-master
```

运行一键安装：

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

1. 检查/安装 **uv**（Python 包管理器，自动管理 Python 3.12，无需你装 Python）；
2. 创建独立虚拟环境 `.venv` 并安装依赖（首次约 1-2 分钟）；
3. 运行健康检查，确认安装成功。

#### 手动安装（不想用脚本的话）

```powershell
# 1. 安装 uv：Windows 在 PowerShell 执行
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
#    macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 创建环境并装依赖（在 Skill 根目录）
uv venv .venv --python 3.12
uv sync
```

### 安装自检

```powershell
uv run python -c "import json; print('Python OK')"
uv run python scripts\scanner.py --help
uv run python scripts\inventory.py --help
```

三条都有正常输出 = 安装成功。

### 常见问题（FAQ）

| 问题 | 解决 |
|---|---|
| `uv` 提示找不到命令 | 安装后**关闭并重开 PowerShell/终端**再试 |
| 依赖下载超时 | 用国内镜像重跑：`install.ps1 -Mirror`（macOS：`install.sh -mirror`） |
| 没有 Python 3.12 | 不需要手动装：uv 会自动管理 Python 版本 |
| 脚本报权限错误 | Windows 用 `powershell -ExecutionPolicy Bypass` 前缀运行 |
| Agent 没识别到 skill | 确认路径下有 `SKILL.md` 文件，重启 Agent 会话 |

---

## 🚀 第一次使用

在你的 Agent 里直接说：

```text
盘点我装了哪些 skill
```

Agent 会自动调用 `sm-manager`，扫描你所有 Agent 的 skills 目录，输出清单 + 健康报告。

## 💬 日常用法

```text
盘点我装了哪些 skill                        → sm-manager（清单 + 健康看板）
检查这个 skill 安全吗：<路径>                → sm-security（安全扫描）
分析这个开源 skill：<路径>                    → sm-analyzer（结构分析）
帮我写一个 <主题> 的 skill                   → sm-writer（访谈 + 落盘）
优化这个 skill：<路径>                       → sm-optimizer（四维诊断）
```

## ✅ 适合 / ❌ 不适合

**✅ 适合**：skill 越装越多、需要体检和去重的人；装第三方 skill 前想先扫一遍后门的安全党；想研究优秀开源 skill 的写法、或从零做自己 skill 的创作者。

**❌ 不适合**：对象不是 skill 目录的一般编程 / 文档 / 运维任务——路由器会按负例表拒绝，按普通任务处理。

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
