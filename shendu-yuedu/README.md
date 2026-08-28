# 深度阅读 Skill 合集

5 个功能 skill（#1-#5 阅读闭环）+ 1 个自进化（#6，迭代实践转化出的技能）= 6 个 skill。把"读完就忘"变成"读完变成可调用的技能"。每个 skill 独立可用，完成后推荐下一步。

## 工作流

```
#1 初始化 → #2 拆解书籍 → #3 预读 → #4 结构化精读 → #5 实践转化（书名\知识点 skills）
                                                              ↓
                                          #6 自进化（按真实使用情况迭代那些技能，SkillOpt）
```

## 阅读大脑（共享沉淀库）· LLM Wiki 三层架构

组织方式参照 [Karpathy LLM Wiki](https://gist.github.com/karpathy) 模式 + [Google Open Knowledge Format](https://github.com/google/okf)（OKF）约定。所有 skill 通过 `<知识库根>/阅读笔记/` 共享上下文。**越读越聪明**。

**`<知识库根>` 解析协议**（#1 采集，#2-#6 每次启动按此解析，权威定义见 `01-init/SKILL.md`）：
1. 本次会话用户显式指定
2. 当前 Agent 打开的项目路径下有知识库标志（`阅读笔记/log.md` 或 `阅读笔记/_system/用户阅读报告.md`）→ 用当前项目路径
3. 全局配置 `~/.shendu-yuedu/config.json` 的 kb_root（问用户是否沿用）
4. 都没有 → **默认当前 Agent 打开的项目路径**（读书笔记等一切输出文件都在这个路径下组织知识库），由 #1 Round 0 引导初始化

### 三层架构

| 层 | 目录 | 谁写 | 规则 |
|---|---|---|---|
| **Raw 原始层** | `阅读笔记/YYYY-MM/<书名>/<章节名>/摘抄.md` 等用户真实阅读笔记 | 人 | **不可变**：AI 只读，提取知识但绝不改写 |
| **Wiki 沉淀层** | 拆解目录 / 问题清单 / 知识卡片 / 实践转化 / Hub 报告 | AI | LLM 全权维护：更新、交叉引用、标矛盾，人只审 |
| **Schema 约定层** | 本 README（阅读域）+ `<知识库根>/SKILL.md`（vault 级，#1 bootstrap 生成） | 人×AI 共同演进 | 告诉 LLM 目录职责与工作流约定 |

```
<知识库根>/                              # 默认 = Agent 当前打开的项目路径，#1 初始化时可改
├── SKILL.md                            ← Schema 层：vault 级宪法（#1 首次引导生成）
├── 阅读笔记/
│   ├── _system/用户阅读报告.md      ← index.md：Hub 主入口（画像/在读书目索引/技能索引）
│   ├── log.md                       ← append-only 执行时间线（#1-#5 每次执行追加）
│   ├── YYYY-MM/<书名>/              ← 单本书档案
│   │   ├── 00-拆解目录.md           (#2 产出)
│   │   ├── 问题清单.md              (#3 产出)
│   │   ├── 知识卡片.md              (#4 产出，多轮追加)
│   │   ├── 实践转化.md              (#5 产出)
│   │   └── <章节名>/摘抄.md         ← Raw 层（用户手写）
│   └── runs/<skill>/<日期>/         ← #6 训练数据
├── skills/
│   ├── INDEX.md                      ← 跨书技能索引（⭐核心资产）
│   └── <书名>/<skill-slug>/SKILL.md ← #5 产出的可执行技能
└── wiki/                             ← 可选：跨书实体/主题页（OKF 概念文件）
```

### OKF 约定（wiki 层产出文件）

每个 #2-#5 产出的 markdown 文件头部带 YAML frontmatter（OKF 只强制 `type`，其余可选）：

```yaml
---
type: 知识卡片          # 拆解目录 / 问题清单 / 知识卡片 / 实践转化 / 阅读大脑索引
title: <书名>·知识卡片
description: 一句话摘要
tags: [深度阅读, <书名>]
timestamp: YYYY-MM-DD   # 最后更新
resource: 可选，书源链接/版本（微信读书/豆瓣/纸书版次）
---
```

- **链接规范由 #1 采集**：用户编辑器是 Obsidian → 用 `[[双链]]`；Typora/VS Code/其他 → 标准相对路径链接；无偏好 → 默认标准相对链接（最大兼容）。写入 Hub 报告「知识库工具链」，#2-#5 写跨文件引用时遵循。
- **log.md 条目格式**：`## [YYYY-MM-DD] init|decompose|preread|deepread|practice | 书名·一句话说明`——前缀统一，可 `grep "^## \[" log.md | tail -5` 回顾最近动作。
- **存量不迁移**：2026-08-27 前的旧文件无 frontmatter 属正常；新书、新产出文件按本约定执行。

## 人 × AI 分工原则
- **人**：真实阅读、记录笔记/划线/想法、把技能用到真实场景、反馈技能好不好用
- **AI**：拆解结构、设计问题、整理卡片、萃取技能、迭代技能
- AI 不替代阅读，只放大每一分钟阅读的杠杆。

## 目录

| # | Skill | 触发短语 |
|---|-------|----------|
| 1 | `sy-init` 初始化 | "阅读初始化"/"开始读一本书"/"建阅读档案" |
| 2 | `sy-decompose` 拆解书籍 | "拆解这本书"/"精读目录"/"这书怎么读" |
| 3 | `sy-preread` 预读 | "预读"/"问题清单"/"带着问题读" |
| 4 | `sy-deepread` 结构化精读 | "整理笔记"/"知识卡片"/"结构化精读" |
| 5 | `sy-practice` 实践转化 | "实践转化"/"萃取技能"/"怎么用这本书" |
| 6 | `sy-evolve` 自进化 | "迭代技能"/"技能不好用"/"优化阅读技能" |

## 方法论来源
- 推理框架：Tree-of-Thoughts / Chain-of-Verification / Graph-of-Thoughts / Algorithm-of-Thoughts（用于 #2-#5 各环节）
- 知识组织：Karpathy LLM Wiki 模式 + Google [Open Knowledge Format](https://github.com/google/okf)（markdown + YAML frontmatter + index/log，三层架构见上节）
- 自进化：微软 [SkillOpt](https://github.com/microsoft/SkillOpt)（#6，把技能文档当可训练状态）

## 运行产物权威路径

本合集的 skill 安装包只保存协议，不保存运行产物。所有深度阅读输出写入 `<知识库根>`（解析协议见上节；未指定时默认当前 Agent 打开的项目路径）：

- 基准目录：`<知识库根>/阅读笔记/`
- Hub/阅读报告：`<知识库根>/阅读笔记/_system/用户阅读报告.md`
- sy-practice 产出的可执行 skill：`<知识库根>/skills/<书名>/<skill-slug>/SKILL.md`
- 跨书技能索引同时写入：阅读报告「已萃取技能索引（跨书累积）」 + `<知识库根>/skills/INDEX.md` + wiki 索引
- 每本书：`<知识库根>/阅读笔记/YYYY-MM/书名/`
- 每章笔记：`<知识库根>/阅读笔记/YYYY-MM/书名/章节名/`
- 全局配置（跨会话记住知识库位置）：`~/.shendu-yuedu/config.json`

