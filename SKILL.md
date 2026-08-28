---
name: skill-master
description: skill-master 合集路由器：管理 skill 全生命周期——盘点已装 skill、安全扫描第三方 skill、分析开源 skill、从零编写新 skill、迭代优化已有 skill，分别由 sm-manager / sm-security / sm-analyzer / sm-writer / sm-optimizer 五个子 skill 承担，本文件只路由不执行。Use when 用户提到"盘点skill"、"扫描skill"、"分析这个skill"、"帮我写个skill"、"优化这个skill"等 skill 相关请求，或直接提到"skill-master"时使用；完整触发词以正文路由表为准。
---

# skill-master — skill 全生命周期合集（路由器）

一个 skill 从装进来、看懂它、写出来到养得好，五件事各由一个子
skill 负责，全部位于本仓库 `skills/` 下：

| 子 skill | 职责 |
|---|---|
| [sm-manager](skills/sm-manager/SKILL.md) | 盘点本机各 Agent 已装的 skill（只读） |
| [sm-security](skills/sm-security/SKILL.md) | 第三方 skill 安装前的安全扫描与复核 |
| [sm-analyzer](skills/sm-analyzer/SKILL.md) | 开源 skill 的结构、工作流分析与 HTML 报告 |
| [sm-writer](skills/sm-writer/SKILL.md) | 从零访谈需求、起草并落盘新 skill |
| [sm-optimizer](skills/sm-optimizer/SKILL.md) | 已有 skill 的四维诊断与迭代优化 |

本文件是**总协议 + 路由器**（参照 cheat-on-content 模式）：收到请求
只做一件事——按路由表分发到对应 `skills/sm-*/SKILL.md`，不重复子
skill 的工作流细节；转介规则见下文。

## 总协议（三原则，shared-references/skill-anatomy.md §6.2）

所有子 skill 与本路由层共同遵守：

1. **脚本做确定性事**：枚举、校验、渲染、统计——结果必须可复现的
   操作交给 `scripts/`，不现场重写
2. **LLM 做判断事**：解读数据、权衡方案、撰写分析、降误报——需要
   语义理解的操作留给 Agent
3. **危险操作必须确认**：写文件、删文件、改配置之前，先向用户展示
   将要做什么，确认后再动手；宁可多问，不可先斩后奏

## 路由表（触发词 → 子 skill）

触发词摘自各子 skill frontmatter 的 Use when 句，逐字一致：

| 用户说 | 路由到 | 前置条件 |
|---|---|---|
| "盘点skill" / "我装了哪些skill" / "skill清单" / "skill健康检查" / "skill重复" | sm-manager | 无（默认用仓库内 shared-references/agents.yaml 注册表，只读） |
| "检查这个skill安全吗" / "扫描skill" / "有没有后门" / "skill安全" / "skill恶意" | sm-security | 目标 skill 的本地路径；远程仓库 / URL 需先下载到本地 |
| "分析这个skill" / "拆解这个开源skill" / "它怎么工作的" / "skill原理" / "这个skill写得怎么样" | sm-analyzer | 被分析 skill 已在本地目录（用户已 clone / 下载），需给路径 |
| "帮我写个skill" / "新做一个skill" / "写个技能" / "做个skill" / "创建skill" | sm-writer | 无（从零新建；目标已存在则归 sm-optimizer） |
| "优化这个skill" / "skill触发不准" / "改skill" / "skill不触发" / "迭代skill" | sm-optimizer | 目标 skill 已存在（不存在的归 sm-writer 新写） |

## 防抢触发负例

以下请求**含相似关键词但操作对象不是 skill**，不路由到 skill-master，
按普通任务处理：

| 用户说 | 不路由，因为 |
|---|---|
| "优化这段 Python 代码" | 代码优化 ≠ skill 优化，对象是代码 |
| "写个文档" / "写篇周报" | 写文档 ≠ 写 skill，对象是文档 |
| "分析这个报错" | 报错分析 ≠ skill 分析，对象是报错 |
| "扫描端口" / "扫描这个网站" | 端口 / 站点扫描 ≠ skill 安全扫描，对象不是 skill 目录 |
| "盘点服务器" / "盘点库存" | 资产盘点 ≠ skill 盘点，对象不是 skill 目录 |

判别标准一句话：**操作对象是否是一个 skill 目录**（含 SKILL.md 的
技能目录）。是 → 按路由表分发；不是 → 本合集不接。

## 子 skill 间转介规则

转介由路由层执行，子 skill 不越界代办：

- **sm-writer → sm-optimizer**：写完落盘、验证触发后流程即结束，
  **不自动进优化**；用户明确要求时才路由到 sm-optimizer
- **sm-optimizer ↔ sm-security**：优化诊断中发现疑似安全问题，只
  记录类型与位置并转介 sm-security，不展开修复、不回显敏感值；
  安全扫描中发现 skill 触发 / 质量问题，建议走 sm-optimizer
- **sm-analyzer ↔ sm-security**：analyzer 呈现扫描总分与规则命中
  即止，逐条误报复核、安装结论等深度安全审查转介 sm-security；
  需要完整拆解 skill 结构与质量时，sm-security 建议走 sm-analyzer
- **sm-manager → sm-optimizer**：盘点发现健康问题（缺 SKILL.md、
  frontmatter 损坏、description 超长、name 不一致）只给修复建议、
  不代改；用户要动手修已有 skill 时路由到 sm-optimizer（manager
  只读）

## 跨 Agent 兼容

本路由不依赖 slash-command：没有命令机制的 Agent（如 Codex）按
自然语言触发同一套路由表，子 skill 一律以 `skills/sm-*/SKILL.md`
的仓库内相对路径定位。
