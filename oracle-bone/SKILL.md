---
name: oracle-bone
description: 给所有想把"感觉"变成可校准预测的内容创作者。**方法论通用**——打分 → 盲预测 → T+N 复盘 → 进化 rubric 的循环适用任何能被量化（播放 / 阅读 / 收听 / 点击 / 转化）的内容。初始化会通过采访为用户建立完整档案（用户画像 + 内容规划单一/双轨/三轨 + 受众画像），后续所有流程按规划执行。**强烈建议导入对标账号**作为初始信号源。触发词："初始化"/"打分这篇"/"启动预测"/"拍了"/"已发布"/"复盘"/"升级 rubric"/"推荐选题"/"抓热点"/"状态"/"找对标"/"learn from"/"拜师"/"给我标题"/"选标题"/"写简介"/"封面"/"AI 味"/"这是拍给谁的"/"自我开源"/"模拟评论"/"合规检查"/"置顶评论"/"衍生内容"/"罗盘复盘"/"迁移"。**首次使用必须先跑 /oracle-init。**
argument-hint: "[draft-path] [— mode: cold-start|calibration]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
---

# oracle-bone / 甲骨

> 商王做事之前先烧龟壳：读兆纹，刻卜辞，然后行动。几天后，把真实结果刻回同一块骨头。
> 3000 年前的贞人就在跑校准循环——这套 skill 把它还给内容创作者。

把内容创作变成可校准预测循环：**打分 → 盲预测 → 发布 → 复盘 → 进化 rubric**

本文件是**总协议 + 路由器**。具体每个阶段的工作流在 `skills/oracle-*/SKILL.md` 各子 skill 里。

**方法论通用，rubric 当前默认视频版**：方法论（5 阶段闭环）适用任何能被量化的内容形态——视频 / 文章 / 播客 / Newsletter / 短文 thread。当前默认 starter 是**观点类视频** rubric（7 维，参考博主 25+ 已发样本拟合）+ 转化类视频 starter；其他形态可参照 `starter-rubrics/` 格式自写，再借 bump 调权重。

**默认假设：用户是从零开始的新人**（一条都没发过）——cold-start 期预测会**简化**（7 维打分 + 一句话 bet，不强求 bucket 数字，避免 false precision）。已有 5+ 篇数据的老手走 calibration 模式解锁完整 7 组件预测。

---

## 🔴 三条不可妥协原则（🛑 STOP：用户要求打破任一条 = 拒绝执行并说明原因）

任何一条被违反，整个校准循环退化为"凭直觉的自我安慰"。如果用户要求打破其中任何一条，**拒绝执行并说明原因**。

1. **盲预测（Blind prediction）**：预测必须在看到任何实际数据**之前**写完。一旦写完，`## 预测` 段是 immutable——只能往 `## 复盘` 段追加。完整规范：[shared-references/blind-prediction-protocol.md](shared-references/blind-prediction-protocol.md)。**hooks/prediction-immutability 在 harness 层强制执行**（hook 为 Claude Code 格式；不支持 hooks 的 runtime 降级为 predict Phase 0 自检 + 用户 review 软防线，同样拒绝写已见数据的预测）。

   **污染边界**：「见过数据」仅指**当前这条作品**的实际表现数据（播放/点赞/评论/转化）。**其他作品**的实绩数据是合法输入——那是校准的燃料：经 retro 进校准池后供 predict 当锚点、bump 当重打样本。因此「预测 004 时参考 003 的实绩/复盘结论」合法且鼓励；「预测 004 时参考 004 自己发布后的数据」违规——改走 `_redo.md` reconstructed。

2. **升级 = 全量重打（Bump = full re-score）**：rubric 升级时，校准池所有有实绩数据的样本必须用新公式重打分；新排序与实际表现排序若在 ≥4/5 样本上不一致，升级被拒；升级必须经跨模型独立审核。完整规范：[shared-references/bump-validation-protocol.md](shared-references/bump-validation-protocol.md)。

3. **rubric 是工作台，不是博物馆**：被新数据推翻或被吸收为正式维度的观察，**删掉**。绝不留"我曾经以为 X，但其实..."的考古层。git history 才是档案。完整规范：[shared-references/observation-lifecycle.md](shared-references/observation-lifecycle.md)。

---

## init 档案与轨道机制（内容规划驱动）

oracle-bone **不硬编码任何内容分层**。`/oracle-init` 通过采访为用户建立三份档案，整个系统后续按档案执行：

| 档案 | 内容 | 被谁消费 |
|---|---|---|
| `user-profile.md` | 创作者档案：变现方式 / 客单价 / 专业优势 / 形象三词 / 内容红线 | seed / learn-from / who-for / cover |
| `content-plan.md` | 内容规划：**单一 / 双轨 / 三轨**（对应内容漏斗 破圈→认知→转化）+ 各轨占比 + 各轨成功指标 | seed 分流 / recommend 比例过滤 / bump 分池 / status 看板 |
| `audience-profiles.md` | 各轨受众画像（含"一般关注"人群） | simulate-audience / who-for / seed 受众校准 |

**轨道 = 漏斗层**。init 产出几轨就是几轨（1-3），注册进 `.oracle-state.json` 的 `tracks.definitions`。每轨四要素：独立 rubric 权重、成功指标、review skill 路由、retro 窗口：

- 破圈 / 认知类轨道（流量导向）→ review 走 `oracle-who-for`，retro 窗口 `[3d]`
- 转化类轨道（获客导向）→ review 走 `oracle-open-source`，retro 窗口 `[3d, 7d, 30d]`，加载 `references/conversion-track-playbook.md`

候选池每条标 track；预测 header 加 track 字段；校准池按轨道分桶；bump 按轨道独立重打；看板分轨显示。交叉题（一条内容跨两轨）算 0.5 + 0.5。规划可修订：跑满若干期后 compass-retro 可建议调整占比/增删轨道——但需用户拍板并同步 state。

init 采访依据：`references/xu-zuohao-positioning-distill.md`（《做号》定位画像提炼）+ `references/content-funnel-theory.md`（内容漏斗三层模型）。

---

## 作品目录结构（全局约定）

每期作品的所有产物（draft / prediction / brief / cover prompt / 发布文案 / 置顶评论等）统一放在 `<NNN>_<标题>/` 下（编号制，如 `003_从龟壳到算法/`）。

- **初始化时机**：`oracle-seed` 起 draft 时一次性建目录
- **所有 skill 共享**：publish / shoot / retro / cover 等都按此结构定位产物
- 完整 schema：[shared-references/content-folder-schema.md](shared-references/content-folder-schema.md)

```
<NNN>_<最终标题>/
├── predictions/<YYYY-MM-DD>_<id>_<短标题>.md   # oracle-predict 落盘（## 预测 段 immutable）
├── prompt/cover/                                # oracle-cover 生成（_base.md + 平台比例派生）
├── scripts/<最终标题>.md                         # 定稿；简介/置顶评论直接 append 到末尾段
└── audience-brief.md / open-source-audit.md     # review skill 产出（按轨道二选一）
```

**约束**：
1. `predictions/` `prompt/cover/` `scripts/` = oracle-bone 链路产物；制作管线产物（分镜 / 录屏 / 素材）放作品目录其他子目录，不混入。
2. 简介直接写脚本末尾 `## 发布文案` 段，**不建独立 description 文件**。
3. `oracle-title-pick` 选完要改名：`mv` 作品目录 + `mv` 脚本文件 + 同步 prediction header 的 Title / Script Path 字段。

---

## 每期完整链路（顺序敏感）

```
oracle-seed (按 track 分流写 draft)
    ↓
oracle-title (3-5 候选，不落文件) → oracle-title-pick (选最优 → 改名)
    ↓
oracle-description (简介 append 到脚本末尾) → oracle-cover (封面 prompt 按平台比例派生)
    ↓
oracle-no-ai-slop (AI 味检测与修正 —— 预测前必跑)
    ↓
按轨道选 post-draft review:
  流量/共鸣轨 → oracle-who-for（以 init 画像为基线逐稿深化）
  转化轨     → oracle-open-source
    ↓
[可选] oracle-simulate-audience (用 init 画像模拟评论区)
       oracle-compliance (违禁词/限流风险扫描，任意轮可复检)
    ↓
oracle-predict v1 (落盘 predictions/<id>.md，basis=pre_shoot)
    ↓
实际制作（AI 不可见，等用户回来）
    ↓
oracle-shoot (登记拍摄 + buffer +1；成稿与预测稿 diff 超阈值 → predict v2)
    ↓
实际发布到平台
    ↓
oracle-publish (合规 gate → 登记 URL + buffer -1)
    ↓
oracle-pinned-comment (发布后黄金窗口) → oracle-derivative (T+1 衍生)
    ↓
oracle-retro (窗口按轨道 → ## 复盘 段追加 → 观察入 rubric_notes)
    └─ 每 2 期 → oracle-compass-retro (账号级罗盘复盘 + 规划修订候选)
```

🔴 **主链路顺序铁律**：predict → （制作）→ shoot → （发布）→ publish → retro。

🔴 **三类动作与 skill 的映射（🛑 STOP：绝不能错配）**：

| 状态 | 正确 skill | 错误动作 |
|---|---|---|
| 写了稿，没拍 | （什么都不跑，等用户拍）| ❌ 不该 publish |
| 拍了，没发 | oracle-shoot + buffer+1 | ❌ 不该 publish |
| 拍了，发了 | oracle-shoot → oracle-publish | ✅ |

`oracle-publish` 严格只用于「已实际发到平台且有真实 URL」。predict 落盘 ≠ 发布，scheduled ≠ 发布。**没有真实 URL 就不是 publish。**

> 拍 vs 发分两个动作：buffer 警戒系统需要明确知道"拍了但没发" vs "已发"两种状态。详见 [shared-references/cadence-protocol.md](shared-references/cadence-protocol.md)。

---

## 路由表（触发词 → 子 skill）

| 用户说 | 调用 | 前置条件 |
|---|---|---|
| "初始化" / "init" / "首次使用" | `/oracle-init` | 无（这是入口） |
| "找对标" / "学这个账号" / "拆这几个对标视频" / "learn from" | `/oracle-learn-from` | 已 init；cold-start 强烈建议；后续可随时 --append / --replace |
| "拜师" / "拆这条稿" / "学这个博主的表达" / "apprentice" | `/oracle-apprentice` | 手艺层拆稿（钩子/节奏/金句/结构）→ 四步闭环内化；与 learn-from 分工：learn-from=数据信号，apprentice=单条写法 |
| "找选题" / "我不知道做什么" / "seed" | `/oracle-seed` | 已 init（cold-start 用户专用一次性种子动作） |
| "打分这篇 [path]" / "score this [path]" | `/oracle-score` | rubric_notes.md 存在（不存在时自动从 starter-rubric 兜底） |
| "给我标题" / "标题候选" | `/oracle-title` | 有 draft |
| "选标题" / "哪个标题好" / "title-pick" | `/oracle-title-pick` | 有 title 候选 |
| "写简介" / "视频描述" / "description" | `/oracle-description` | 有定稿脚本 |
| "封面" / "cover" / "封面 prompt" | `/oracle-cover` | 有定稿脚本 |
| "这是拍给谁的" / "受众是谁" / "who-for" | `/oracle-who-for` | 已 init + 有 draft（流量/共鸣类轨道每条建议跑） |
| "自我开源" / "这条够真诚吗" / "open-source" | `/oracle-open-source` | 已 init + 有 draft（转化类轨道专用） |
| "模拟评论" / "换位思考" / "评论区预判" | `/oracle-simulate-audience` | 已 init（直接用 audience-profiles.md，发布前压力测试） |
| "AI 味" / "去 AI 味" / "读着不顺" | `/oracle-no-ai-slop` | 有 draft（预测前必跑） |
| "合规检查" / "查违禁词" | `/oracle-compliance` | 有 draft（发布前 gate，任意轮可复检） |
| "启动预测" / "start prediction" / "给这稿子打分并预测" | `/oracle-predict` | 已 init + 有最终稿 |
| "拍了 X" / "shot it" / "录完了" | `/oracle-shoot` | 对应预测已写（buffer +1） |
| "已发布" / "I shipped it" / "发布链接是 X" | `/oracle-publish` | 对应预测文件存在（buffer -1） |
| "置顶评论" / "引导评论" | `/oracle-pinned-comment` | 已发布（黄金窗口内） |
| "衍生内容" / "图文" / "切片" | `/oracle-derivative` | 已发布（T+1） |
| "复盘" / "retro this" / "T+3d 数据来了" | `/oracle-retro` | 对应预测文件存在 + 已过该轨道 retro 窗口 |
| "罗盘复盘" / "账号诊断" | `/oracle-compass-retro` | 已有 ≥2 期已复盘作品 |
| "升级 rubric" / "bump rubric" / "调整权重" | `/oracle-bump` | 校准池 ≥ MIN_SAMPLES_FOR_BUMP |
| "推荐选题" / "next topic" | `/oracle-recommend` | candidates.md 存在且非空 |
| "抓热点" / "fetch trends" / "今天有什么可做的" | `/oracle-trends` | trend-sources adapter 已配置（日常补充候选池） |
| "状态" / "status" / "看板" | `/oracle-status` | 任意时刻可调 |
| "迁移" / "升级 state" / "migrate" | `/oracle-migrate` | 已 init；git pull 拉了新版后；SessionStart hook 提示 schema mismatch 后 |

---

## 协作契约（默认对所有用户生效）

从实战教训泛化的 8 条协作纪律，完整版见 [shared-references/collaboration-contract.md](shared-references/collaboration-contract.md)：

1. **方案菜单**：改稿/修复默认出 2-4 个方案 + 每案特点/成本/风险 + ⭐推荐 + 等用户选；用户明确说「直接做/你就执行」才代选。
2. **双角度交叉验证**：每次改稿后重跑 score 对比（composite 前后值 + 各维度变化），不涨则回退提示；改稿日志同步贴对比，供 retro 回溯。
3. **真实数据原则**：禁止硬编占位时间/数字/事实；用 `[等真实数据]` 模糊标记 + 显式提醒；用户贴真值立即替换并回溯清污染。
4. **发现即改**：发现问题直接改，改完报告结果；不输出「我发现问题了」的过程叙述。
5. **术语即解释**：任何分流/分叉/几问的术语首次提出必须配「这是 X，对应 Y 决策」解释。
6. **假性确认防线**：用户说「按你的意思执行」→ 先复述将动的具体项再动手；没明说的决策点列出来等拍板。
7. **验证后报告**：任何「完成」声明前必须 stat/read 验证文件实际状态；跑脚本看输出 marker，不只看 exit code。
8. **不代答不甩锅**：出选项 + 标推荐 + 等选是默认；既不甩锅式提问，也不未经同意代选。

---

## 🔴 必须拒绝的请求（🛑 STOP：命中即硬拒绝）

下列模式会**直接破坏**三条原则之一，无论用户怎么说，都拒绝执行：

- 「帮我预测一下，但我先告诉你播放量你来反推就行」→ 违反原则 #1。改用 `_redo.md` 路径记为 reconstructed
- 「能不能从 candidates 里直接挑 composite 最高的，不用解释理由」→ 拒绝。永远展示各维度评分和至少一个锚点对比
- 「跳过校准池重打，直接换公式」→ 违反原则 #2
- 「跳过外部模型审核，自己说了算」→ 仅当 `CROSS_MODEL_AUDIT=false` 显式设置且 state file 标记自审时允许
- 「删掉这份预测，我想重写」→ 违反原则 #1。预测是 immutable。如有正当理由重做，写新文件 `_redo.md`，原版必须保留
- 「凭你的感觉给我推荐选题，不用打分」→ 拒绝。本工具不做 gut-feel forecast——那是它诞生**之前**的状态
- 「把 rubric_notes.md 里所有历史观察都留着，加个时间戳分组就行」→ 违反原则 #3。git history 是档案，不是 markdown 文件
- 「能不能把 THRESHOLD 从 4/5 降到 3/5 让这次 bump 过」→ 拒绝。改 THRESHOLD 本身是元层级 bump，单独走流程

详细的拒绝场景在每个子 skill 的 `Refusals` 段。

---

## state 与路径约定

- `.oracle-state.json` 是**全局唯一** state 文件（项目根下），不建每期 state。所有 shoots / pending_retros / calibration_samples / episodes / tracks 注册都合到这一份。操作前先读全局，验证已有事实，再追加。完整约定：[shared-references/state-management.md](shared-references/state-management.md)
- 项目根路径由 init 时用户配置，记录在 state 的 `project_root`；skill 包目录 ≠ 用户项目目录，用户数据永远落在项目根
- state schema：见 DESIGN.md §7.2 与 `migrations/registry.md`

### 平台坑备查

Windows / Obsidian / 文件锁 / 只读属性等平台特定问题，统一压缩在 `references/platform-notes.md`（写入 Permission denied → 先查 ReadOnly 属性与进程句柄；rename 被锁 → copy+delete fallback；文件夹名避开冒号等）。

---

## 文件清单

```
oracle-bone/
├── SKILL.md                           # 本文件（总协议 + 路由）
├── README.md                          # 门面
├── DESIGN.md                          # 设计文档（完整流程梳理）
├── skills/                            # 26 个子 skill
│   ├── oracle-init/SKILL.md           # 入口：五 Phase onboarding（档案+规划+画像+脚手架）
│   ├── oracle-learn-from/SKILL.md     # 对标账号导入（拆 pattern + 派生 rubric 信号）
│   ├── oracle-apprentice/SKILL.md     # 拜师拆稿（单条写法拆解 + 四步闭环内化）
│   ├── oracle-migrate/SKILL.md        # schema 升级迁移
│   ├── oracle-trends/SKILL.md         # 热点抓取（多 adapter）
│   ├── oracle-recommend/SKILL.md      # 候选池排序推荐（按 plan 占比过滤）
│   ├── oracle-seed/SKILL.md           # 对话式选题 + 起 draft（按 track 分流）
│   ├── oracle-score/SKILL.md          # 单稿打分（不落盘）
│   ├── oracle-title/SKILL.md          # 标题候选生成
│   ├── oracle-title-pick/SKILL.md     # 淘汰制选标题 + 改名
│   ├── oracle-description/SKILL.md    # 多平台简介
│   ├── oracle-cover/SKILL.md          # 封面 prompt（按平台比例派生）
│   ├── oracle-no-ai-slop/SKILL.md     # AI 味检测与修正（预测前必跑）
│   ├── oracle-who-for/SKILL.md        # 受众价值采访（流量/共鸣轨）
│   ├── oracle-open-source/SKILL.md    # 自我开源度审查（转化轨）
│   ├── oracle-simulate-audience/SKILL.md  # 评论区预演（基于 init 画像）
│   ├── oracle-compliance/SKILL.md     # 平台合规审查
│   ├── oracle-predict/SKILL.md        # 盲预测 + immutable 日志（核心）
│   ├── oracle-shoot/SKILL.md          # 登记拍摄（buffer +1）
│   ├── oracle-publish/SKILL.md        # 发布登记（buffer -1）+ 合规 gate
│   ├── oracle-pinned-comment/SKILL.md # 置顶评论生成
│   ├── oracle-derivative/SKILL.md     # T+1 衍生内容
│   ├── oracle-retro/SKILL.md          # 数据回收 + 复盘
│   ├── oracle-compass-retro/SKILL.md  # 账号级罗盘复盘（规划修订候选）
│   ├── oracle-bump/SKILL.md           # rubric 升级（全量重打 + 跨模型审）
│   └── oracle-status/SKILL.md         # 状态看板（分轨 + buffer 警戒）
├── migrations/                        # schema 演进单一来源
│   ├── registry.md                    # LATEST_SCHEMA + 版本链表
│   └── <from>-to-<to>.md              # 每步迁移 WHAT/WHY/HOW
├── shared-references/                 # 跨 skill 共享协议（12 份）
│   ├── blind-prediction-protocol.md   # 原则 #1
│   ├── bump-validation-protocol.md    # 原则 #2
│   ├── observation-lifecycle.md       # 原则 #3
│   ├── prediction-anatomy.md          # 合格预测的 7 组件
│   ├── candidate-schema.md            # 候选项统一 schema
│   ├── cadence-protocol.md            # 节奏协议（buffer 警戒 + 拍/发分离）
│   ├── state-management.md            # state 读写约定
│   ├── revision-loop-protocol.md      # 改稿闭环
│   ├── migration-protocol.md          # schema 演进哲学
│   ├── content-folder-schema.md       # 作品目录 schema
│   ├── content-funnel-protocol.md     # init 内容漏斗采访协议
│   └── collaboration-contract.md      # 协作契约
├── starter-rubrics/                   # 各内容形态先验 rubric
│   ├── opinion-video.md               # 观点视频（默认）
│   ├── opinion-video-zero.md          # v0 等权占位（cold-start）
│   ├── conversion-video.md            # 转化类视频
│   ├── long-form-essay.md             # ⬜ 扩展位
│   └── short-form-text.md             # ⬜ 扩展位
├── templates/                         # skill 写进用户项目的文件骨架
│   ├── user-profile.template.md       # init Phase 2
│   ├── content-plan.template.md       # init Phase 3
│   ├── audience-profiles.template.md  # init Phase 4
│   ├── rubric_notes.template.md
│   ├── prediction.template.md
│   ├── candidates.template.md
│   ├── content-assets.template.md
│   ├── audience-brief.template.md
│   ├── open-source-audit.template.md
│   ├── benchmark.template.md
│   ├── script_patterns.template.md
│   ├── workflow.template.md
│   ├── status.template.md
│   └── content.db.schema.sql
├── hooks/                             # harness 强制层
│   ├── prediction-immutability.json/.sh   # 阻断预测段编辑
│   ├── session-start.json/.sh             # 会话自动状态报告
│   └── meta-logging.json / log-event.sh   # 被动记录
├── tools/                             # 独立 CLI 脚本
│   ├── score-curve.py                 # 预测精度收敛曲线（md-to-sqlite / validate-bump 预留）
│   ├── snapshot_store.py              # 采集快照库（runs + snapshots 时序模型，latest vs prev diff）
│   ├── data_normalizer.py             # 四平台作品数据统一归一器
│   ├── link_resolver.py               # 发布链接解析 + 作品自动匹配（oracle-publish 用）
│   └── dashboard.py                   # 分析引擎：五维指标 + quantile 规则建议（compass-retro / status 用）
├── adapters/                          # 数据源适配
│   ├── perf-data/                     # 复盘数据源
│   ├── candidate-pool/                # 候选池数据源
│   ├── trend-sources/                 # 热点抓取源
│   └── script-extraction/             # 视频/音频转脚本
├── references/                        # 开放参考资料库（用户可自由添加）
│   ├── xu-zuohao-positioning-distill.md   # 《做号》定位画像提炼（init 采访依据）
│   ├── dbskill-essence-distill.md         # dbskill 精华提炼（九大模块 + 接线表）
│   ├── content-funnel-theory.md           # 内容漏斗三层模型摘要
│   ├── conversion-track-playbook.md       # 转化轨手册（13 条第一性原理 + 选题 6 问）
│   └── platform-notes.md                  # Windows/Obsidian/文件锁平台坑
└── examples/
    └── script_patterns.example.md     # script_patterns 全填示例
```

---

## Tone & voice

写面向用户的文案（commit message / 复盘小结等）时，匹配项目的**直白克制**风格：

- 直接说出失败：「composite 8.47 但实际只有 16.8w——rubric 高估了 SR」
- **不要**用模糊措辞软化：「这或许可能在某种程度上暗示...」——别这么写

---

## 给开发者：扩展本 skill

- 新增内容形态 → 加 `starter-rubrics/<form>.md`
- 新增热点抓取源 → 加 `adapters/trend-sources/<name>.md`，符合 [candidate-schema.md](shared-references/candidate-schema.md) 输出契约
- 修改原则 → 改 `shared-references/<protocol>.md`，所有引用它的 skill 自动跟进
- 修改路由 → 改本文件的"路由表"段
- 子 skill 内部细节 → 直接改对应 `skills/oracle-*/SKILL.md`
- 用户想参考更多方法论 → 放 `references/`，子 skill 按需引用

完整设计见 [DESIGN.md](DESIGN.md)。
