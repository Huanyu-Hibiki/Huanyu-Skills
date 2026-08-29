---
name: oracle-init
description: oracle-bone 的首次 onboarding 与脚手架创建器。不只是建目录——通过采访为用户建立完整档案（用户档案 + 内容规划单一/双轨/三轨 + 各轨受众画像），后续所有 skill 按档案执行。触发词："初始化"/"init"/"首次使用"/"我是新用户"/"setup oracle-bone"。**必须在用户第一次会话执行；其他子 skill 在 .oracle-state.json 不存在时自动路由到此。**
argument-hint: "[— form: opinion-video|long-essay|short-text|podcast]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, WebFetch, Skill
---

# /oracle-init — 首次 onboarding（档案 + 规划 + 脚手架）

让用户从零到能跑第一条预测。没发过历史的 ≤ 10 分钟；已发过要 import 历史的 ≤ 15 分钟。

初始化不只是建脚手架——这 10 分钟产出的**三份档案**（user-profile / content-plan / audience-profiles）决定后续所有 skill 怎么工作。

## Overview

```
[用户首次说"初始化"]
  ↓
[Phase 0: 检测当前状态]
  ↓
[Phase 1: 基础配置（形态/时长/频率/平台/模式判定）]
  ↓
[Phase 2: 用户档案采访（8 问）→ user-profile.md]
  ↓
[Phase 3: 内容漏斗采访（5 问）→ content-plan.md + 轨道注册]
  ↓
[Phase 4: 用户画像推导（按轨道）→ audience-profiles.md]
  ↓
[Phase 5: 脚手架落盘（state + rubric + 目录 + hooks）]
  ↓
[Phase 5.5: 对标账号询问 → （选"现在找"则 dispatch /oracle-learn-from）]
  ↓
[Phase 6: 测试 hook + 给"下一步该说什么"清单]
```

## Constants

- **INSTALL_HOOKS = ask** — 默认询问；用户选 yes 直接装；no 不装
- **TREND_DEFAULT_SOURCES = ["manual-paste"]**
- 采访依据：`references/xu-zuohao-positioning-distill.md` §6（Phase 2/4 问卷）+ `references/content-funnel-theory.md`（Phase 3 理论）+ [shared-references/content-funnel-protocol.md](../../shared-references/content-funnel-protocol.md)（完整协议）

## Inputs

无。所有信息从对话采访里收集。

## 🔴 采访执行协议（所有 Phase 通用铁律）

1. **一次只问一个问题**：每条消息只含当前这一个问题（可附选项/示例），禁止把多个问题打包进同一条消息
2. **答完再问下一个**：用户回答当前问题之前不进入下一问；答非所问 → 换更简单的问法重问，不跳过、不代答
3. **追问有度**：每问最多 1-2 轮澄清追问；信息已够用就继续，不为凑轮次而追问
4. **阶段收口**：每个采访 Phase 问完 → 复述本阶段采集结果 → 用户确认 → 才落盘/进下一 Phase
5. **问完才产出**：所有关键问题（Phase 2-4）问完并确认后，才输出对应档案文档——中途不写半成品文件

## Workflow

### Phase 0: 检测当前状态

1. 确认当前工作目录是用户的内容项目根（不是 oracle-bone skill 包目录）
2. 检查是否已存在 `.oracle-state.json`：
   - 存在 → 提示"项目似乎已初始化。重新初始化会覆盖现有配置——确认？"等用户明确确认才继续
   - 不存在 → 继续
3. 检查是否已存在 `rubric_notes.md` / `predictions/` 等核心文件——存在但 state 不存在 → "半初始化"状态，询问"要从现有文件推断状态还是重置？"

### Phase 1: 基础配置（首屏 + 4 问）

先输出首屏（一字不漏）：

```
🎯 oracle-bone / 甲骨 — 初始化

把内容创作变成可校准预测循环：打分 → 盲预测 → 发布 → 复盘 → 进化 rubric。
3000 年前的贞人就在烧龟壳对账——现在轮到你的账号。

接下来 10-15 分钟我会分四个阶段采访你：
1. 基础配置（2 分钟）
2. 你是谁——创作者档案（4 分钟）
3. 你的内容打哪儿去——漏斗规划（3 分钟）
4. 你的观众是谁——画像推导（2 分钟）

两件事先说在前面：

1. **早期预测会不准**——前 5 篇精度大概 ±50%，这是数学事实。
   工具用 🔴🟠🟡🟢🔵 标 confidence 等级，不藏数字——你自己判断能不能信。

2. **强烈建议导对标账号**——5-10 条对标样本，工具立刻有 anchor。
   不然第一批预测基本是占星。后面会再问一次。

准备好开始了吗？
```

**Q1: 内容形态**（决定 rubric starter）

> "你的内容更接近哪一种？
> a) **观点视频**（评论 / 时评 / 论说 / 议题讨论）— 直接匹配内置 rubric（默认推荐）
> b) **转化视频**（产品获客 / 案例展示 / 服务营销）— 匹配转化类 starter
> c) **长文**（公众号 / Substack）d) **短文 thread** e) **播客/长视频** f) 其他 g) 混合"

映射 `content_form`：`opinion-video` / `conversion-video` / `long-essay` / `short-text` / `podcast` / `other` / `mixed`。非 a/b → `rubric_form_mismatch: true`（借观点 rubric 起步，status 持续提示 bump 调权重）。

**Q2: 典型时长**（视频类才问）→ `typical_duration_seconds`（30/90/240/450/900）

**Q3: 发布频率** → `target_publish_cadence_days`（1/2/7/null）

**Q4: 发布平台 + 历史状态**（合并问）

> "你主要在哪些平台发？（多选：抖音/B站/小红书/视频号/YouTube/公众号/其他）
> 发过内容吗？
> a) 没发过 — 后续 /oracle-seed 帮你从兴趣+热点 brainstorm
> b) 发过 — 可以 import 历史让 baseline 更准（需要提供数据，可跳过）"

- 平台集 → `platforms[]`（多平台同步分发是默认建议；平台选择策略 = 内容形态 × 商业模式 × 用户画像，Phase 2/4 采访后可回来微调）
- 选 b → 追问"大概多少条？想现在 import 还是先跳过？"（import 流程：用户提供历史数据 → 建 作品目录 + reconstructed prediction，标 NOT FOR CALIBRATION，`baseline_plays` 取中位数回填；不阻塞主流程）

### Phase 2: 用户档案采访（8 问）→ user-profile.md

> 采访逻辑：**商业模式决定内容定位**（高端餐厅做高端内容，街头面馆做接地气内容）。先搞清楚你怎么收钱，才知道内容该做成什么样。

逐问采访（严格按「采访执行协议」执行：一次一问、答完再问；每问 AI 结合上下文追问 1-2 轮，不等用户写长文）：

| # | 问题 | 挖什么 |
|---|---|---|
| 1 | 你靠什么收钱？客单价什么量级？ | 商业模式（卖服务/卖产品/卖广告位/卖课程/暂不变现攒影响力） |
| 2 | 付钱给你的人是谁？典型客户画个像 | 从商业模式反推核心受众（付费者优先） |
| 3 | 你比绝大多数人懂什么？ | 专业优势（专业 IP 的成功路径靠专业积累） |
| 4 | 你有哪些别人拿不走的资源/经历？ | 不可复制素材库（**本问用深挖式采访**，见下） |
| 5 | 用三个词形容你想立的形象？ | 人设定位（专家型/真实型，非卖货型/娱乐型） |
| 6 | 你的内容风格是什么样的？ | 内容风格（语言口吻：严肃/轻松/毒舌；节奏：快剪高密度/慢节奏深聊；视觉：色调/字幕/封面调性） |
| 7 | 你自己喜欢做、喜欢看什么内容？ | 内容喜好（做起来不累的题材 + 自己会刷的领域——cold-start seed 选题的种子；区分"喜欢做的"vs"擅长做的"） |
| 8 | 哪些内容你绝对不做？ | 内容红线（漏斗外排除项） |

落盘 `user-profile.md`（从 `templates/user-profile.template.md` 复制骨架 + 填采访结果）。落盘前**复述给用户确认**（协作契约 #6）。

**Q4 深挖式采访（经历锚点库）**——像记者追问故事，不像填表：

1. 用户答得具体（有事件/场景/转折）→ 直接记入经历锚点库，追问一句"后来呢？这事改变了你什么？"
2. 用户答得空泛（"没什么特别的"/"就是普通上班"）→ 换具体化切入再问一轮：
   - "最近一次工作上被卡住/搞砸/被人说不行，是什么时候的事？随便讲讲，不用管能不能做成内容"
   - "有没有一件事，你朋友常听你讲、或你常在脑子里回放的？"
   - "你做过什么别人第一次听说会'啊？'出声的事？"（职业转折 / 踩坑翻身 / 极端经历 / 反常识日常）
3. 每条锚点按格式记：**一句话故事（时间/场景/角色/转折）+ 情绪词 + 可展开方向**——这是 oracle-seed Mode A 和 oracle-open-source 镜子检查的直接原料
4. 收集 3-5 条即可收口，不无限追问；一条都挖不出来 → 如实记 `[经历锚点：待挖——seed 首次找选题时补]`，不编造

### Phase 3: 内容漏斗采访（5 问）→ content-plan.md + 轨道注册

> 采访逻辑：内容按漏斗分层——**破圈**（最广受众）/ **认知**（目标用户）/ **转化**（购买意向用户）。每层服务不同人群、不同目标，**流量 ≠ 客户**。

按 [content-funnel-protocol.md](../../shared-references/content-funnel-protocol.md) 的 5 问执行：

1. **三类人群盘点**：会付钱的 / 潜在会付钱的 / 只是爱看的
2. **逐层能力**：破圈层能做吗想占多少？认知层专业优势撑哪类？转化层变现落点是什么？
3. **占比拍板**：AI 只给参照（双轨常见 40/60，三轨常见 4:3:3），**用户定**
4. **各层成功定义**：每轨 2-3 条可观测指标（破圈轨看播放涨粉，转化轨看咨询付费）
5. **漏斗外劝退测试**：绝对不碰的内容清单

产出规划类型：**single**（聚焦一层）/ **dual**（破圈+转化）/ **triple**（三层全做）——按用户在问题 2 的回答决定有哪些层，**不硬凑**。

每轨四要素注册（详见 content-funnel-protocol.md"轨道注册"段）：
- 轨道 id + 用户命名 + funnel_layer
- review_skill 路由（转化轨 → oracle-open-source；破圈/认知轨 → oracle-who-for）
- retro 窗口（流量轨 [3]；转化轨 [3,7,30]）
- rubric starter 路由（破圈/认知 → opinion-video；转化 → conversion-video）+ mix_ratio

落盘 `content-plan.md`，**复述确认**后才进 Phase 4。

### Phase 4: 用户画像推导（按轨道）→ audience-profiles.md

按 content-plan 每轨推导画像。**付费者优先纪律**：画像从"谁付钱"反推，不从"谁点赞"正推。

每轨画像五要素（从 user-profile + Phase 3 回答推导，AI 起草 → 用户确认修订）：
1. 人群定义（是谁 / 怎么刷到 / 为什么停留）
2. 痛点与需求（他们在找什么）
3. 互动特征（会怎么评论 / 什么话术触发咨询）
4. 转化路径（从看到内容到信任到行动）
5. **一般关注画像**（非目标但会刷到的人：会怎么评价 / 会不会转发 / 可能质疑什么）

落盘 `audience-profiles.md`。**这份画像直接被 oracle-simulate-audience 消费**（两类人群模拟的根基）。

### Phase 4.5: 约束初判（暂定 stage_constraint）

从采访信号初判当前最大约束（四类判定表见主 SKILL.md「stage_constraint」段）：

- Phase 2 形象三词/专业优势答不上来 → `positioning_unclear`
- 定位清晰但表达 pattern 无从谈起（script_patterns 空 + 未导对标）→ `expression_unstable`
- Q3 发布频率目标 vs 用户自述可投入时间差距大 → `capacity_limited`
- 转化轨已有内容但零咨询信号（仅 import 历史的老手可判）→ `conversion_blocked`
- 信号都不显著 → `none`

初判值 + 一句依据复述给用户确认（归入 Phase 4 收口确认，不单独加一轮提问）；后续 compass-retro 每 2 期回写。

### Phase 5: 脚手架落盘（逐项解释）

按顺序创建并**解释每一项的作用**（不静默 mkdir）：

1. **`.oracle-state.json`**（schema 见 [state-management.md](../../shared-references/state-management.md)）：
   - 写入 Phase 1-4 收集的全部配置 + `tracks.definitions`（Phase 3 注册）+ `stage_constraint`（Phase 4.5 初判：`{value, basis, updated_at}`）
   - `schema_version: "1.0"`、`mode`（cold-start / calibration）、`calibration_samples_by_track`（每轨 0 起）
   - `initialized_at` 用本地 ISO 8601 含时区（**不要 UTC Z 后缀**）

2. **`rubric_notes.md`** — 按轨道分节：每轨复制对应 starter（`starter-rubrics/opinion-video.md` 或 `conversion-video.md`；cold-start 用 `-zero` 等权版）到该轨节
   ```
   "正在创建 rubric_notes.md — 评分维度的真实来源，按你的轨道分节。
    v0 是没校准前的占位。你账号自己的真权重要从你的数据反推，
    跑完 5 篇有数据的内容后会自动提议升级到校准 v1。"
   ```

3. **三份档案文件**：user-profile.md / content-plan.md / audience-profiles.md（Phase 2-4 已产出，确认落位）

4. **`script_patterns.md`**（复制 template，按轨道分节）+ **`candidates.md`**（空池）+ **`WORKFLOW.md`** / **`STATUS.md`**

5. **目录**：项目根下建 `study/`（对标样本，oracle-learn-from 用）——`scripts/` `predictions/` 不建平铺目录，**每期作品一个 `<NNN>_<标题>/` 目录**（oracle-seed 时建，见 [content-folder-schema.md](../../shared-references/content-folder-schema.md)）

6. **装 hooks**（默认装）：
   - merge `hooks/prediction-immutability.json` + `session-start.json` + `meta-logging.json` 进 `.claude/settings.json`
   - 复制三个 .sh 到 `.oracle-hooks/`，chmod +x，command 路径用 `${CLAUDE_PROJECT_DIR}/.oracle-hooks/`

7. **追加 `.gitignore`**（不覆盖）：`.oracle-cache/` `.oracle-secrets.json`

### Phase 5.5: 对标账号（所有用户都问）

```
🎯 对标账号

工具早期最重要的信号源是对标账号——你 init 完没数据，rubric 等权 v0 等于占星。
找一个你想做成那样的账号，导入 5-10 条高/中/低样本，工具就有 anchor。

a) 现在找 → 立刻进入 /oracle-learn-from（5-15 分钟）
b) 等下找 → 标 pending，状态看板持续提醒
c) 不找 → 用通用 v0 起步

回 a / b / c。
```

- 选 a → Phase 6 hook 测试完毕后 **自动 dispatch 到 /oracle-learn-from**（不让用户手动跑）
- 选 b → `benchmark_status: pending`；选 c → `none`

### Phase 6: 测试 hook + 下一步清单

**hook 测试**（仅当装了 hooks）：
1. 建临时文件 `predictions/_test_hook.md`（含 `## 预测` + `## 复盘` 段）→ 尝试 Edit 预测段 → 钩子应 exit 1 阻塞 → 报"✅ immutability 钩子生效" → 删测试文件
2. 跑一次 `bash .oracle-hooks/session-start.sh` → 应输出报告（空也行）
3. 钩子未生效 → **不假装成功**，明确告知可能原因（settings 未生效/需重启）

**下一步清单**：

```
✅ 初始化完成（规划：双轨 [破圈 40% + 转化 60%]，rubric: v0，样本: 0，confidence: 🔴 极低）

你的三份档案：
  user-profile.md       — 你是谁
  content-plan.md       — 内容往哪打（2 轨 + 占比 + 成功指标）
  audience-profiles.md  — 观众是谁（simulate-audience 的根基）

下次你可以直接说这些：

🌱 找选题        → "找选题"（按轨道分流起 draft）
📊 写完一篇稿子  → "打分这篇 <NNN>_<标题>/scripts/<...>.md"
🎯 准备发布前    → "启动预测 ..."（盲预测，预测段锁定）
🎬 拍完了        → "拍了 ..."
🚀 发布后        → "已发布 https://..."
📈 到复盘窗口    → "复盘 ..."
🎛️ 任何时候      → "状态"

💡 confidence 会随复盘自动提升。不要因为早期不准就跳过预测——
   早期预测的价值是数据采集，不是决策。第 5 次复盘后第一次校准。
```

## Key Rules

1. **不假装成功**：任何步骤失败 → 明确说哪步出错。绝不写"✅ 完成"如果实际没完成
2. **不批量提问**：🔴 一次一问、答完再问、问完才落盘——完整约束见「采访执行协议」；每个采访 Phase 结束复述确认再进下一个
3. **不静默 mkdir**：每创建一个文件都解释作用
4. **占比不代定**：轨道占比是用户战略决策，AI 只给参照系
5. **档案是活文档**：告诉用户后续可修订（compass-retro 会建议修订规划）
6. **import 失败不阻塞**：历史 import 走不通 → 优雅降级到"标估值，不导入"

## Refusals

- 「跳过采访，直接给我创建所有文件」→ 拒绝。没有档案的轨道规划 = 后续所有 skill 退化混池
- 「规划你来定就行」→ 拒绝代定占比与轨道取舍；可给建议参照，用户拍板
- 「不装 hook 但保留 immutability 承诺」→ 允许，state 标 `hooks_installed: false`，status 持续提示"你的 immutability 是君子协定"
- 「我已经在别处初始化过了，把那个项目的配置同步过来」→ 慎重。提示手动 cp state + 三份档案 + rubric_notes，不自动跨项目同步

## Integration

- 写完后，主 SKILL.md 路由解锁所有其他子 skill
- oracle-seed 读 content-plan 分轨；oracle-recommend 按 mix_ratio 过滤；oracle-simulate-audience 读 audience-profiles；oracle-bump 按 tracks 分桶
- 转化轨的 seed / review 额外加载 `references/conversion-track-playbook.md`
