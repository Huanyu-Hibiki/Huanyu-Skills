# PulseHub Skills

PulseHub is a **complete customer acquisition skill system** — from project setup to lead conversion. 16 skills across 4 layers, with a shared "project brain" (`project-archive/`) that accumulates context over time.

## Architecture (4 Layers)

```
Layer 1: ENTRY          → pulse-router (decision routing)
Layer 2: DATA           → pulse-discover / resolve / enrich / deliver (existing tools)
Layer 3: BUSINESS       → pulse-init / insight / keywords / topics / copywrite / script / private / leads
Layer 4: QUALITY        → pulse-humanize / evolve / review
```

## Full Skill Catalog (16/16 ✅)

### Layer 1: Entry (路由)

| Skill | Purpose | Status |
|-------|---------|--------|
| [`pulse-router`](pulse-router/) | 诊断产品方向清晰度，路由到对应 skill | ✅ |

### Layer 2: Data (数据采集)

| Skill | Purpose | Status |
|-------|---------|--------|
| [`pulse-discover`](pulse-discover/) | 通过 RSSHub / Chrome MCP 发现帖子 | ✅ |
| [`pulse-resolve`](pulse-resolve/) | 标准化 URL（5 平台） | ✅ |
| [`pulse-enrich`](pulse-enrich/) | 信号检测 + 评分（关键词 + LLM prompt） | ✅ |
| [`pulse-deliver`](pulse-deliver/) | 生成 Markdown 报告 + 可点击 URL | ✅ |

### Layer 3: Business (获客闭环)

| Skill | Purpose | Status |
|-------|---------|--------|
| [`pulse-init`](pulse-init/) | 初始化项目 + 建立 project-archive | ✅ |
| [`pulse-insight`](pulse-insight/) | 付费用户洞察 + 痛点提炼 | ✅ |
| [`pulse-keywords`](pulse-keywords/) | 获客关键词矩阵 | ✅ |
| [`pulse-topics`](pulse-topics/) | 爆款选题（调 pulse-discover 发现热门） | ✅ |
| [`pulse-copywrite`](pulse-copywrite/) | 文案生成（读 个人风格.md） | ✅ |
| [`pulse-script`](pulse-script/) | 视频脚本（含口播稿+分镜） | ✅ |
| [`pulse-private`](pulse-private/) | 私域承接 SOP + 话术资产 | ✅ |
| [`pulse-leads`](pulse-leads/) ⭐ | 评论线索抓取（**核心集成点**） | ✅ |

### Layer 4: Quality (质检 + 进化)

| Skill | Purpose | Status |
|-------|---------|--------|
| [`pulse-humanize`](pulse-humanize/) | 去 AI 味（24 模式 + 个人风格对齐） | ✅ |
| [`pulse-evolve`](pulse-evolve/) | 自进化（SkillOpt 式闭环） | ✅ |
| [`pulse-review`](pulse-review/) | 极简复核（体系体检） | ✅ |

## Project Brain (`_archive/`)

The [`_archive/`](_archive/) directory contains **6 template files** that form the "project brain":

| File | Role |
|------|------|
| `项目档案.md` | Hub: 基本信息 + 累积产出索引 |
| `人群语料库.md` ⭐ | 真实用户原话 / 痛点 / 拒绝理由 |
| `爆款素材库.md` | 拆解的爆款结构 / 钩子公式 |
| `话术资产.md` | 私域话术（带效果标签） |
| `数据反馈.md` ⭐ | 真实运营数据（自进化的燃料） |
| `个人风格.md` | 用户文风指纹 |

`pulse-init` copies these to `~/.pulsehub/archive/<项目名>/` on first run. All subsequent skills read/write to that location.

### Two archive fields that drive cross-skill behavior

| 字段 | 确定时机 | 作用 |
|------|---------|------|
| **主平台** | `pulse-init` Round 3（ABCD 选项确定） | 内容主战场。copywrite / topics / script / humanize 一律读此字段，不各自问用户 |
| **定位协议** | `pulse-init` Round 4（可选登记路径） | 品牌手册 / IP 对齐 / 内容红线文件。登记了 → 所有 skill 先读并优先服从；未登记 → 按档案自身定位执行 |

See [`_archive/README.md`](_archive/README.md) for the full design. Entry routing for agents: [`AGENTS.md`](AGENTS.md).

## How AI Agents Use These Skills

1. **opencode / Claude Code** reads `AGENTS.md` + `SKILL.md` frontmatter at startup
2. User says something (e.g., "我想找客户")
3. Agent matches intent to a skill's `description`
4. Skill's `Workflow` tells the agent what to do step-by-step
5. Skill reads from / writes to `~/.pulsehub/archive/<项目名>/`

## Compatibility

Skills work with any agent that reads `SKILL.md` files:

- **opencode** — reads `AGENTS.md` at startup ⭐ Best fit
- **Claude Code** — copy `pulse-*/` dirs to `~/.claude/skills/`
- **Cursor** — via `@workspace` indexing
- **OpenClaw** — copy to workspace
- **Custom Hermes** — see `docs/agents/hermes.md`

## Installing Skills

目录结构：16 个 `pulse-*/` skill 目录直接位于仓库根（无 `skills/` 中间层），共享资源在 `_shared/`、`_core/`、`_archive/`。

```bash
# For opencode: just start opencode in the PulseHub directory
cd /path/to/PulseHub && opencode

# For Claude Code:
cp -r pulse-*/ ~/.claude/skills/

# For OpenClaw:
cp -r pulse-*/ ~/.openclaw/workspace/skills/
```

> 单个 skill 目录被复制到别的 runtime 时，`_shared/`、`_core/` 引用（脚本/recipes）不可达属预期——各 SKILL.md 已内置对应 Fallback（人工/浏览器替代路径）。

## Skill Dependencies

Most business skills (Layer 3) depend on data from Layer 2 and the project brain:

```
pulse-router → pulse-init → pulse-insight → pulse-keywords
                                    ↓
                              pulse-topics → pulse-copywrite → pulse-humanize
                                    ↓               ↓
                              pulse-script    pulse-private
                                    ↓               ↓
                              pulse-leads ← ← ← ← ←
                                    ↓
                              pulse-evolve (reads all, edits skills)
```

**Recommended order for first run**:
1. `pulse-router` — am I ready?
2. `pulse-init` — set up project brain
3. `pulse-insight` — understand users
4. `pulse-topics` — find what to post
5. `pulse-copywrite` — write the content
6. `pulse-leads` — find comment opportunities
7. `pulse-humanize` — check for AI tone
8. (later) `pulse-evolve` — improve the system

## Authoring a New Skill

1. Create `pulse-<name>/SKILL.md` (at repo root, alongside the other pulse-* dirs)
2. Frontmatter:
```yaml
---
name: pulse-<name>
description: English summary. 中文关键词。Use when <trigger>.
---
```
3. Required sections:
   - `## 何时触发`
   - `## 前置`（读哪些 archive 文件）
   - `## 工作流`（step-by-step）
   - `## 输出`（产出什么 + 写回哪个 archive 文件）
   - `## 人 × 数字员工分工`
4. Update this README's catalog
5. Create `AGENTS.md` if it doesn't exist (opencode reads it at startup), then update it
