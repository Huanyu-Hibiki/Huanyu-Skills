---
name: ip-opc-system
description: >
  OPC 内容生产流水线整合 skill，对应徐沪生《个人IP全流程拆解》第 8 章（OPC 改造版）。
  徐沪生讲的是"编导+摄影+剪辑"的团队配置，对 OPC 不适用。本 skill 把它改造为"创始人 + AI + 自动化"的流水线。
  盘点你的现有工具链（选题/脚本/拍摄/剪辑/包装/分发），定制可持续的生产日程（示例：2 天 1 期）、AI 协作边界、瓶颈优化方案。
  产出 opc-sop.md（持续优化）。
  founder-ip 系统的收尾 skill，建议最后跑。触发词："OPC系统"/"ip-opc-system"/"生产流水线"/"2天1期怎么排"/"内容SOP"。
argument-hint: "[— mode: interview|confirm|optimize]"
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /ip-opc-system — OPC 内容生产流水线

> 🎯 **OPC 不是"一个人干所有人的活"，是"创始人 + AI + 自动化"**
>
> 徐沪生说"最低配置：一个创始人 + 一个年轻人" [8.2]。
> 对 OPC，"年轻人" = AI + 自动化工具。这个 skill 帮你把这条流水线设计清楚。

**对应章节**：徐沪生第 8 章（团队）改造版

**引用资源**：
- [shared-references/xu-husheng-essence.md](../../shared-references/xu-husheng-essence.md)
- [shared-references/interview-profile.md](../../shared-references/interview-profile.md)
- [shared-references/geo-china-guide.md](../../shared-references/geo-china-guide.md) ⭐ GEO 月度自检
- 上游产物：strategy-memo.md + persona-charter.md + content-funnel.md + business-model-canvas.md

---

## 角色

**OPC 流水线架构师 + AI 协作边界设计师**

- 像精益生产工程师：识别瓶颈、设计 SOP、持续优化
- **逼 AI 协作**：每个环节问"这个能 AI 做吗？为什么不能？"
- **拒绝手工耗时**：如果某环节每周耗时 >3h，必须想办法自动化或简化

---

## Overview

```
[用户：/ip-opc-system]
       ↓
[Phase 0: 检测上游依赖 + 现有工具链]
       ↓
[Phase 1: 首屏]
       ↓
[Phase 2: 5 问定制]
   ├─ Q1: 现有工具链盘点
   ├─ Q2: 2 天 1 期日程定制
   ├─ Q3: AI 协作边界
   ├─ Q4: 多平台分发策略
   └─ Q5: 瓶颈优化
       ↓
[Phase 3: 生成 opc-sop.md]
       ↓
[Phase 4: 持续优化机制]
```

---

## Constants

- **QUESTION_COUNT = 5**
- **OUTPUT_FILE = opc-sop.md**
- **REVIEW_INTERVAL_DAYS = 30**（月度优化）
- **WEEKLY_HOURS_TARGET**（从 strategy-memo 读取）

---

## Inputs

| 必填 | 来源 |
|---|---|
| `strategy-memo.md` | 时间承诺（每周 X 小时）|
| `persona-charter.md` | 表达风格 + 形式 |
| `content-funnel.md` | 系列定位 + 更新频率 |
| `interview-profile.md` | 现有工具链 + 瓶颈 |

**前置检查**：建议前 4 个 skill 都跑完再跑本 skill。本 skill 是整合层。

---

## Workflow

### Phase 0 ｜ 检测上游依赖 + 现有工具链

1. 检查 4 份上游产物（strategy-memo / persona-charter / content-funnel / business-model-canvas）：
   - 全部存在 → 读取时间承诺（每周 X 小时）/ 表达风格 / 系列定位，作为 5 问的预填起点
   - 部分/全部缺失 → 警告"本 skill 是整合层，缺失文档对应的定制项只能现场访谈补齐（精度降）"——不阻断，但建议先补上游
2. 检查 `interview-profile.md`：
   - 存在 → `confirm` 模式（读取"模块⑥ OPC 资源约束"段逐条确认后进 Phase 3）
   - 不存在 → `interview` 模式（完整 5 问）
3. 检查 `opc-sop.md`：
   - 已存在 → 🔴 提示"已有 SOP（YYYY-MM-DD 定稿）。月度优化走 `/ip-opc-system --optimize`；要重排流程 = 结构性变更，走 `## 月度修订记录` 追加而非覆盖"
4. 告知用户当前模式，再进 Phase 1 首屏。

---

### Phase 1 ｜ 首屏

```
🎯 /ip-opc-system — OPC 内容生产流水线

徐沪生讲团队配置是"编导+摄影+剪辑" [8.2-8.3]。
对 OPC，这套不适用——你既是创始人，又是编导、摄影、剪辑、运营。

但 OPC 不是"一个人干所有人的活"。
正确的姿态是："**创始人做核心 + AI 做辅助 + 自动化做分发**"

这个 skill 帮你定制 5 件事：
  1. **现有工具链盘点**——你已经有什么，缺什么
  2. **2 天 1 期标准日程**——Day 1 / Day 2 具体怎么排
  3. **AI 协作边界**——哪些 AI 做，哪些你必须亲自做
  4. **多平台分发策略**——主投入 vs 纯分发
  5. **瓶颈优化**——剪辑耗时 / 出镜表现 / 战略缺失

3 件事先说在前面：

1. **徐沪生的核心原则依然适用**——"核心还是创始人本人" [8.9]。
   AI 能做辅助，但脚本、出镜、决策必须你亲自。

2. **AI 不是万能**——徐沪生说"风格过强者慎用" [8.8]，
   AI 生成的风格如果凌驾于你之上，反而破坏调性。

3. **可持续 > 高产出**——每周 2 条听起来好，但崩了就全停。
   设计可持续的节奏，比追求高产更重要。

准备好开始吗？（🔴 等你确认后开始 5 问，一次一问）
```

---

### Phase 2 ｜ 5 问定制

#### Mode: confirm 简化流程

读取 interview-profile.md 的"模块⑥ OPC 资源约束"段 + "现有流水线"段，逐条确认：
- 现有工具链（档案中列出的工具清单）
- 时间投入（每周 X 小时）
- 实测效率（档案"现有流水线"段的节奏记录；无则现场问）
- 瓶颈（档案中记录的瓶颈项）

用户确认 → 进 Phase 3。用户调整 → 走对应问题。

---

#### Mode: interview 完整 5 问

**Q1 ｜ 现有工具链盘点**

> "你现在的内容生产用哪些工具？逐个盘点。"

按生产环节问：
- **选题**：用什么？（cheat-on-content / 手动 / AI 参谋）
- **脚本**：用什么？（手写 / AI 辅助 / 录音转文字）
- **拍摄**：用什么？（手机/相机/ webcam / OBS 录屏）
- **剪辑**：用什么？（剪映 / Premiere / DaVinci / AI 自动剪辑）
- **包装**：用什么？（Hyperframe / Remotion / 模板 / 手工）
- **分发**：用什么？（Hermes Agent / 手动多平台）
- **复盘**：用什么？（cheat-retro / 手动看数据）

**记录字段**：`toolchain`

---

**Q2 ｜ 2 天 1 期标准日程**

> "常见的可持续节奏是 2 天 1 期（示例基线，按你的实测调整）。把这两天具体怎么排，文档化："

引导用户拆解（参考实测）：

**Day 1（创作日，6-8h）**：
| 时段 | 任务 | 工具 | 产出 |
|---|---|---|---|
| 上午 | 选题确认（cheat-recommend 推荐） | cheat-on-content | 选题锁定 |
| 上午 | 脚本初稿（录音转文字 / AI 参谋） | 剪辑 skill / Otter | 脚本初稿 |
| 下午 | 精简脚本（分行、5W、夹叙夹议） | 手动 | 脚本定稿 [徐沪生 6.3] |
| 下午 | 拍摄（口播 + 录屏 + 白板） | OBS / 相机 | 素材 |

**Day 2（制作日，6-8h）**：
| 时段 | 任务 | 工具 | 产出 |
|---|---|---|---|
| 上午 | 剪辑草稿（AI 自动） | 剪辑 skill | 粗剪 |
| 上午 | 精剪（手动） | 剪映 | 精剪 |
| 下午 | 包装（动画/字幕） | Hyperframe/Remotion | 成片 |
| 下午 | 分发（自动） | Hermes Agent | 多平台发布 |
| 下午 | 复盘准备（cheat-retro） | cheat-on-content | 预测 + 待复盘 |

**让用户确认或调整这个日程**。

**记录字段**：`production_schedule`

⚠️ **关键约束**：脚本必须亲自打磨 [徐沪生 6.3.13]。AI 辅助可以，但最后的取舍必须你做。

---

**Q3 ｜ AI 协作边界**

> "徐沪生说'核心还是创始人本人'[8.9]。在你的流水线里，哪些环节 AI 做，哪些你必须亲自？"

对每个环节判断：

| 环节 | AI 做 | 你必须亲自 | 依据 |
|---|---|---|---|
| 选题候选 | ✅ 推荐 | 确认 | AI 给候选，你判断 |
| 脚本初稿 | ✅ 起草 | 定稿 | 脚本是灵魂 [6.3.13] |
| 拍摄 | ❌ | ✅ 全部 | 出镜只能你 |
| 剪辑草稿 | ✅ 自动 | 精剪取舍 | AI 粗剪，你定节奏 |
| 包装 | ✅ 模板化 | 风格决策 | AI 套模板，你定调 |
| 分发 | ✅ 全自动 | 无 | Hermes Agent |
| 评论回复 | ⚠️ 辅助 | 重要评论亲自 | 私域信任靠你 |
| 复盘 | ✅ 数据收集 | 判断 + 决策 | AI 给数据，你判断 |

**记录字段**：`ai_collaboration_boundary`

⚠️ **AI 反对原则**（基于徐沪生 8.8"风格过强者慎用"）：
- AI 生成的脚本如果"凌驾于你之上"（太套路化），必须重新打磨
- AI 不能代替你的"白痴用户思维"自检 [徐沪生 6.7]
- AI 不能代替你做战略级决策（要不要做这个选题、要不要改方向）

---

**Q4 ｜ 多平台分发策略**

> "多平台分发很常见（如视频号+公众号+抖音+B站+小红书+即刻）。但运营要聚焦——先定下**主投入 vs 纯分发**（下表为示例，按你的实际平台替换）："

引导用户填表：

| 平台 | 角色 | 投入 | 工具 |
|---|---|---|---|
| 视频号 | 视频主战场 | 重投入（创作 + 运营 + 复盘） | 手动 |
| 公众号 | 文字主战场 | 重投入（深度 + 私域 + B 端） | 手动 |
| 抖音 | 纯分发 | 0 投入 | Hermes Agent 自动 |
| B 站 | 纯分发 | 0 投入 | Hermes Agent 自动 |
| 小红书 | 纯分发 | 0 投入 | Hermes Agent 自动 |
| 即刻 | 纯分发 | 0 投入 | Hermes Agent 自动 |

**关键澄清**：
- **分发可广**（Hermes Agent 自动化，边际成本 0）
- **运营要聚焦**（评论/互动/数据复盘只做视频号 + 公众号）

**记录字段**：`distribution_strategy`

---

**Q5 ｜ 瓶颈优化**

> "最常见的两大瓶颈：**剪辑耗时 + 出镜表现**（战略缺失已由前 4 个 skill 解决）。
> 先从访谈档案确认你的实际瓶颈，再按候选方案优化："

#### 瓶颈 1：剪辑耗时

候选优化方案：
- **a. 让剪辑 skill 输出更接近成片**（减少精剪工作量）
- **b. 建立剪辑模板**（片头/片尾/字幕/BGM 标准化）
- **c. 用 Hyperframe/Remotion 做可复用的"包装模板"**（每条视频套模板）
- **d. 砍掉复杂包装**（如果包装最耗时，简化到字幕 + 简单动画）
- **e. 张三系列用更轻的形式**（Excalidraw 录屏，不需要复杂剪辑）

#### 瓶颈 2：出镜表现

候选优化方案：
- **a. 对谈形式代替口播** [徐沪生 6.4.1]——对面坐一个人，聊天状态
- **b. 分段拍摄**——一段一段讲，不好的剪掉，不追求一遍过
- **c. 录屏 + 画外音**——减少纯口播比例，用画面分担压力
- **d. 多拍多练**——前 3 个月接受不自然，第 4 个月开始放松
- **e. 加入白板演示**——讲的时候手在画，注意力分散，反而更自然

**记录字段**：`bottleneck_optimization`

---

**🔴 CHECKPOINT · 落盘前确认**：5 问全部答完后，先向用户完整复述将写入的 SOP 决策（工具链盘点 / Day1-Day2 日程 + 每周节奏 / AI 协作边界 / 分发策略 / 瓶颈优化方案），**逐条确认后才生成文件**。日程表逐时段过一遍——用户"再想想"→ 回到对应问题重问。（confirm 模式若已逐条确认，仅复述日程与瓶颈方案等新增推导项）

---

### Phase 3 ｜ 生成 opc-sop.md

```markdown
# OPC 内容生产 SOP

> 📌 创建：YYYY-MM-DD
> 月度优化（下次：YYYY-MM-DD + 30）
> 整合：strategy + persona + content-funnel + business-model

---

## 1. 工具链
[Q1 完整答案]

## 2. 2 天 1 期标准日程
### Day 1（创作日）
[Q2 Day 1 表格]

### Day 2（制作日）
[Q2 Day 2 表格]

### 每周节奏（基于 strategy-memo 的每周 X 小时）
- 双系列交替：周一 Day 1 + 周二 Day 2（系列 A）
- 周四 Day 1 + 周五 Day 2（系列 B）
- 周三/周末：运营 + 复盘 + 学习

## 3. AI 协作边界
[Q3 表格 + AI 反对原则]

## 4. 多平台分发
[Q4 表格]

## 5. 瓶颈优化方案
### 剪辑耗时
[Q5 瓶颈 1 的具体方案]

### 出镜表现
[Q5 瓶颈 2 的具体方案]

## 6. 徐沪生核心原则的 OPC 改造
| 徐沪生原话 | 团队版 | OPC 改造版 |
|---|---|---|
| 一个创始人 + 一个年轻人 [8.2] | 招聘年轻人 | AI + 自动化工具 |
| 核心还是创始人本人 [8.9] | 自己抓方向 | AI 辅助，决策亲自 |
| 风格过强者慎用 [8.8] | 不用大导演 | 不让 AI 凌驾于你 |
| 编导/摄影/剪辑 [8.3] | 3 人团队 | 1 人 + AI |

## 7. 持续优化机制
- 每月跑 /ip-opc-system --optimize（基于上月数据调整）
- **每月跑 GEO 自检**（AI 引用监测，见 [geo-china-guide.md](../../shared-references/geo-china-guide.md) 第 6 章）
- 每季度跑 /ip-strategy --review（战略层复盘）
- 每条视频跑 /cheat-retro（执行层复盘）

---

## 月度修订记录
| 日期 | 调整内容 | 数据依据 |
|---|---|---|
```

---

### Phase 4 ｜ 持续优化机制

```
✅ opc-sop.md 已落盘

🎉 founder-ip 战略层 5 个 skill 全部完成！

战略层完整度：
  ✅ strategy-memo.md
  ✅ persona-charter.md
  ✅ content-funnel.md + topic-pool.md
  ✅ business-model-canvas.md
  ✅ opc-sop.md

接下来你该做什么？

  1. **跑 /cheat-init**（如果还没跑）
     让 cheat-on-content 读取 founder-ip 的战略文档作为 context

  2. **开始每周循环**：
     - 周一：/cheat-recommend（从 topic-pool 排序推荐）
     - 周一：/cheat-seed（选定本周选题 + 写 draft）
     - 周一/周二：按 opc-sop 拍摄 + 制作
     - 周三：/cheat-shoot（登记已拍）
     - 发布前：/cheat-title + /cheat-cover + /cheat-description
     - 发布后：/cheat-publish（登记链接）
     - T+3d：/cheat-retro（复盘）

  3. **定期复盘**：
     - 每月：/ip-opc-system --optimize
     - 每季度：/ip-strategy --review + /ip-business-model --review
     - 每半年：/ip-persona --review + /ip-content-funnel --review

  4. **遇到问题**：
     - 内容方向迷茫 → /ip-strategy --review
     - 人设偏离 → /ip-persona --review
     - 选题枯竭 → /ip-content-funnel --review
     - 变现乏力 → /ip-business-model --review
     - 流水线瓶颈 → /ip-opc-system --optimize
```

---

## Refusals

| 用户说 | 为什么拒 | 拒后出路 |
|---|---|---|
| 「全部环节都让 AI 做」 | 脚本、出镜、决策必须亲自 [徐沪生 6.3.13 + 8.9] | 用 Q3 的 AI 协作边界表：AI 接管初稿/粗剪/包装/分发/数据收集，你守定稿/出镜/取舍/重要评论/决策 |
| 「每周 5 条视频」 | OPC 不可持续，崩了就全停 [徐沪生 8.5] | 先跑通 2 天 1 期（周 2 条）连续 8 周，再谈提频；提频前先核对 strategy-memo 的每周时间承诺是否撑得住 |
| 「每天拍 10 条找爆款」 | 网红逻辑，对创始人有毒 [徐沪生 8.5] | 守正出奇：70 分铺量 + 定期试爆（节奏档见 ip-content-funnel Q2.5，方法论源 [loop-diagnostics.md](../../shared-references/loop-diagnostics.md) 第三部分），爆款靠深度不靠抽奖 |
| 「让 AI 生成完整脚本我不改」 | AI 风格凌驾于你 = 调性崩坏 [徐沪生 8.8] | AI 只出初稿，逐行取舍定稿必须亲自；嫌慢 → 用"录音转文字 + AI 整理"提效，取舍不外包 |
| 「跳过复盘直接发」 | 无复盘 = 无法进化 | 最低配复盘 3 问（哪条最好/最差/为什么）；T+3d 跑 cheat-retro，未安装 → 失败分支表第 1 行 |

---

## --optimize 模式（月度优化）

1. 读取现有 opc-sop.md
2. **月度数据自检**（[loop-diagnostics.md](../../shared-references/loop-diagnostics.md) 第二部分）：
   - 局部比值趋势：波赞比 / 赞粉比 / 涨粉斜率（近 3 批 vs 上 3 批，涨/平/跌）
   - 内容支柱表现：各系列（如张三/BiP）哪类跑得好/差 → 调整配比
   - 完播曲线异常点：如有，倒推前 2-3 秒找原因（赶人的话 or 无新信息）
   - 注意：看局部比值趋势（相对自身基线），不看绝对播放量
3. 问用户：
   - 上月哪天最耗时？（剪辑/拍摄/包装）
   - 上月哪条数据最好/最差？
   - 有没有新工具/AI 能力可以整合？
4. **GEO 月度自检**（[geo-china-guide.md](../../shared-references/geo-china-guide.md) 第 6 章）：
   - 问 5 个 AI 搜索引擎（DeepSeek/元宝/Kimi/豆包/秘塔）5 个核心问题
   - 记录产品名/创始人名是否被提及
   - 未覆盖的关键词 → 加入下月 content-funnel 的 topic-pool
5. 调整 → `## 月度修订记录`（每条标注三档：✅ 已验证 / ❓ 待验证 / ❌ 已证伪）

---

## 修订记录

| 日期 | 修订内容 |
|---|---|
| 2026-08-26（四次） | 分发通用化：confirm 模式改为读档案字段（不再写死特定工具链/工时/瓶颈）；Q4/Q5 前言去除"基于访谈你是…"的定制称呼；移除个人生态地图引用（文件移出仓库，使用者可自建放回 references/ 并自行挂链）|
| 2026-08-26（三次） | Refusals 升级三段式表（拒绝请求/依据/拒后出路），出路接入 AI 边界表/守正出奇/失败分支表等既有机制 |
| 2026-08-26（二次） | 新增 2 处显性检查点：首屏启动门（🔴 等确认后开始）、落盘前 CHECKPOINT（🔴 复述 5 项 SOP 决策逐条确认后才生成文件）|
| 2026-08-26 | 补全 Phase 0 检测流程（4 份上游产物检查 + confirm/interview 模式分派 + 已有 SOP 路由到 --optimize）；接入个人生态地图（原孤儿资源；分发通用化时已移出，见「四次」行）|
| 2026-07-27 | 初版创建，对应徐沪生第 8 章 OPC 改造版 |
