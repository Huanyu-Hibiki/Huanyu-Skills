---
name: oracle-cover
description: 封面工作流统一入口，按模式生成本期封面提示词或分析参考封面并沉淀视觉配方。生成模式读取 cover-generation-protocol.md；分析模式读取 cover-analysis-protocol.md。旧 oracle-cover-analyze 触发词兼容路由到 analyze 模式。
argument-hint: <draft-path 或参考封面图> [--mode: generate|analyze]
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /oracle-cover — 封面工作流

这是唯一的封面 skill，支持两个互斥模式：

| 模式 | 输入 | 产出 |
|---|---|---|
| `generate` | 已确认标题、定稿文案、用户视觉档案 | `prompt/cover/` 下的封面提示词 |
| `analyze` | 用户提供的参考封面图 | 项目根 `cover-patterns.md`，供后续生成复用 |

## 模式选择

- 用户说“封面”“生成封面”“封面提示词”时进入 `generate`。
- 用户说“拆封面”“分析封面”“对标封面”“cover-analyze”或提供参考封面图时进入 `analyze`。
- 同时提供定稿与参考图时，先进入 `analyze`；分析确认后，用户明确要求再进入 `generate`。不能把拆解自动当成生图授权。
- 旧 `/oracle-cover-analyze` 是兼容名称，只映射到本 skill 的 `analyze` 模式，不保留第二套实现。

## 共同边界

两种模式都只借鉴或生成构图结构、视觉逻辑、功能隐喻与文字层级；不得复制参考作品的人物身份、品牌元素、Logo、水印或原文案。任何参考图中发现的事实与推断必须分开记录。

## 按需读取

- `generate`：读取 [cover-generation-protocol.md](../../references/cover-generation-protocol.md)。
- `analyze`：读取 [cover-analysis-protocol.md](../../references/cover-analysis-protocol.md)。
- 两种模式均按需读取 `user-profile.md`、目标作品定稿与 `cover-patterns.md`，不全量加载另一模式协议。

## 输出规则

先在对话中展示方案与证据，再按对应协议的 checkpoint 等待用户确认；未确认不得落盘。模式完成后直接结束当前任务，不自动启动标题、制作或 VPW 流程。

## 与 video-production-workflow 的边界

本 skill 只处理静态封面与封面参考分析。视频包装、动效逆向、B-roll、分镜、剪辑和成片 QA 统一交给 `video-production-workflow`；旧 `oracle-apprentice --visual` / “拆视频包装”请求由根 `/oracle-bone` 路由到 VPW。
