# oracle-bone · 设计文档与完整流程梳理

> 商王做事之前先烧龟壳：读兆纹，刻卜辞，然后行动。几天后，把真实结果刻回同一块骨头。
> 3000 年前的贞人就在跑校准循环——这套 skill 把它还给内容创作者。
>
> 前身：cheat-on-content（网红作弊器，源自抖音蜗牛学长，经焕羽实战大幅扩展）。
> 本版定位：**通用内容校准器**——剥离个人定制，保留完整方法论与全部 26 个子 skill 流程。
> 命名约定：**只改 skill 名（oracle-\* 前缀），术语全部保留功能词**（预测/复盘/rubric/AI 味/违禁词），不引入占卜意象术语。

---

## 0. 一句话定位

把内容创作变成可校准预测循环：**打分 → 盲预测 → 发布 → 复盘 → 进化 rubric**。

方法论通用——任何能被量化（播放 / 阅读 / 收听 / 点击 / 转化）的内容形态都适用。当前默认**视频优先**（观点视频 rubric 为默认 starter），其他形态走扩展位。

---

## 1. 与 cheat-on-content 的继承关系

### 1.1 完整继承（流程不变）

- 五阶段闭环 + 26 个子 skill 全部功能与衔接顺序
- 三条不可妥协原则（盲预测 / 全量重打 / 工作台非博物馆）及其 hooks 强制
- 冷启动（cold-start）与校准（calibration）双模式
- starter-rubrics 体系（opinion-video 已拟合版 + zero 等权版 + 扩展位）
- 状态管理（全局唯一 state 文件）+ migrations 机制
- buffer 警戒系统（拍/发分离两动作）
- 候选池 schema + 改稿闭环协议 + 观察生命周期
- hooks 三件套（immutability / session-start / meta-logging）
- adapters 架构（trend-sources / perf-data / candidate-pool / script-extraction）

### 1.2 泛化改造（个人专属 → 通用机制）

| 原 OP 专属设定 | 泛化为 |
|---|---|
| 三轨道硬编码（A 借古论今 / B 张三群像 / C 工程史，比例 4:3:3） | **init 内容规划驱动**：初始化时用徐沪生内容漏斗采访，产出单一 / 双轨 / 三轨内容规划，后续流程按规划执行（见 §4） |
| audience-brief 依赖 who-for 先跑 | **init 即产出用户画像**（audience-profiles.md），oracle-simulate-audience 直接以 init 画像为根基；who-for brief 是逐稿深化层 |
| B 轨获客第一性原理 13 条 + 6 问 + 4 步心理闭环评分 | 移入 `references/conversion-track-playbook.md`，内容规划含转化轨时作为该轨手册加载 |
| OP 工作偏好（方案菜单 / 双角度交叉验证 / 真实数据 / 直接改） | 泛化为默认**协作契约**（见 §9），对所有用户生效 |
| 项目根路径写死（知识库 / EPxxx 命名） | init 时配置项目根；作品文件夹泛化为 `<NNN>_<标题>/` 编号制 |
| 徐沪生《做号》/ xuxhusheng 书为私人引用 | 提炼**通用版内容漏斗理论**作为 init 的默认方法论参考（references/content-funnel-theory.md）；references/ 目录开放给用户自由添加参考书籍/文档 |
| 个人风格偏好 | 后续可以根据用户的喜好自己调整 |

### 1.3 剥离项清单

- 张三群像角色库 / 场景库 / 口吻锚点（OP 人设资产）
- 焕羽个人 IP 一致性协议引用
- OP 个人路径、EP004/EP005 特例、B 轨特例分支
- 飞书同步 / 微信多账号发布（个人工具链；adapters 留扩展位）
- dbskill 诊断协议入口（个人知识库依赖）
- Windows/Obsidian/飞书特定 pitfalls → 压缩为 `references/platform-notes.md` 备查

---

## 2. 核心方法论

### 2.1 五阶段闭环

```
   ┌──────────────────────────────────────────────┐
   │                                              │
   ▼                                              │
打分 ──→ 盲预测 ──→ 发布 ──→ T+N 复盘 ──→ 进化 rubric ─┘
```

### 2.2 三条不可妥协原则（违反任何一条 = 循环退化为自我安慰）

1. **盲预测（Blind prediction）**：预测必须在看到任何实际数据之前写完。预测文件中 `## 预测` 段一旦写完即 immutable，只能往 `## 复盘` 段追加。hooks 层强制执行。
2. **升级 = 全量重打（Bump = full re-score）**：rubric 升级时，校准池所有有实绩数据的样本必须用新公式重打分；新排序与实际表现排序若在 ≥4/5 样本上不一致，升级被拒；升级必须经跨模型独立审核。
3. **rubric 是工作台，不是博物馆**：被新数据推翻或被吸收为正式维度的观察，删掉。git history 才是档案，绝不留考古层。

### 2.3 冷启动 vs 校准模式

- **cold-start**（默认假设：一条都没发过的新人）：预测简化为 7 维打分 + 一句话 bet，不强求 bucket 数字。强烈建议先跑 oracle-learn-from 导对标。
- **calibration**（已有 5+ 篇数据）：解锁完整 7 组件预测（见 prediction-anatomy.md）。

---

## 3. 初始化设计（oracle-init，本版重点增强）

初始化从「建脚手架」升级为「**为用户建立完整档案 + 内容战略规划**」。整个系统后续按 init 产出执行。

### 3.0 方法论依据

init 的账号定位与用户画像采访依据 **《做号》方法论提炼**：`references/xu-zuohao-positioning-distill.md`（版权安全版：只提炼概念框架 + 原创采访问卷，不含原文复制；源书转录在 template cheat-on-content `references/做号.md`，仅 OP 自用，不随 skill 分发）。核心推导链：**商业模式 → 用户画像 → 内容定位 → 形象与平台策略**。内容漏斗三层模型另见漏斗专题提炼（模板库 `xu-content-funnel-deep.md`）。

### 3.1 五个 Phase

**Phase 1 · 基础配置**
项目根路径 / 内容形态（默认视频）/ 发布平台集（平台选择建议按「内容形态 × 商业模式 × 用户画像」三要素，起步多平台同步分发）/ 模式判定（cold-start vs calibration）。

**Phase 2 · 用户档案（创作者侧采访）→ `user-profile.md`**

采访问卷见提炼文档 §6 Phase 2（6 问：收钱方式与客单价 / 典型客户 / 专业优势 / 不可复制资源 / 三个词形象 / 内容红线）：

| 问题 | 依据 |
|---|---|
| 你靠什么收钱？客单价什么量级？ | 《做号》：商业模式决定内容定位（高端餐厅做高端内容，街头面店做接地气内容） |
| 付钱给你的人是谁？ | 商业模式反推用户画像 |
| 你比绝大多数人懂什么？ | 专业个人 IP 的成功路径靠专业积累（对比网红赛马制） |
| 哪些内容你绝对不做？ | 漏斗外排除项（不相干热点/个人生活谨慎） |
| 形象三个词 / 风格特征 | 人设三原则：内容型非卖货型 / 专家型非娱乐型 / 真实型非虚假型 |

**Phase 3 · 内容漏斗采访（套用徐沪生内容漏斗理论）→ `content-plan.md`**

采访问卷见提炼文档 §6 Phase 3（5 问：三类人群盘点 / 逐层内容能力 / 占比 / 各层成功定义 / 漏斗外劝退测试）。采访问题：

1. 你的内容给谁看？三类人分别是什么：会付钱的 / 潜在会付钱的 / 只是爱看的
2. 对照三层漏斗逐层提问：
   - **顶层·破圈内容**（最广受众，吸引更广泛目标用户）——你能做吗？想占多少？
   - **中间层·认知内容**（目标用户，分享专业积累/行业洞察）——你的专业优势支撑哪类？
   - **底层·转化内容**（购买意向用户，产品/服务/案例）——你的变现落点是什么？
3. 各层占比由用户拍板（AI 只给参照：双轨 40/60、三轨 4:3:3）
4. 每层"成功"长什么样？（播放/涨粉/同频评论 vs 咨询/付费——**流量≠客户**）

产出三种规划之一：

| 规划 | 结构 | 适用 | 依据 |
|---|---|---|---|
| **单一内容** | 1 轨（聚焦一层） | 纯品牌/纯转化起步，或精力只够一条线 | 单层聚焦 |
| **双轨内容** | 2 轨（破圈 + 转化） | 最常见配置 | 徐沪生：「如果简单一些，也可以只分两层：追求流量的内容、追求转化的内容」 |
| **三轨内容** | 3 轨（破圈 + 认知 + 转化） | 完整漏斗，品牌/流量/转化全要 | 徐沪生三层漏斗完整版 |

规划内容包括：各轨功能定位、占比（如 40/60、4:3:3）、各轨成功指标（破圈轨看播放/涨粉，转化轨看咨询/付费——**流量≠客户**）、统一价值观/审美约束（漏斗各层底层逻辑必须统一，漏斗外内容不碰：不相干热点/个人生活谨慎）。

**Phase 4 · 用户画像分析（受众侧推导）→ `audience-profiles.md`**

按 content-plan 每轨推导画像（问卷见提炼文档 §6 Phase 4，对应「商业模式反推画像」四问 + 一般关注画像）：
- 人群定义（是谁/怎么刷到/为什么停留）
- 痛点与需求（他们在找什么）
- 互动特征（会怎么评论/什么话术触发咨询）
- 转化路径（从看到内容到信任到行动）
- **一般关注**画像（非目标但会刷到的人：会怎么评价/会不会转发/可能质疑什么）

> oracle-simulate-audience 的两类人群模拟（核心受众/一般关注）**直接以这份画像为根基**，不再要求先跑 who-for。oracle-who-for 保留，作为逐稿深化受众价值的采访层（产出 audience-brief.md），两者是「基线画像 → 逐稿 brief」关系。

**Phase 5 · 脚手架落盘**
state 文件 + rubric_notes（从 starter 兜底）+ predictions/ / scripts/ / candidates.md 等目录 + 装 immutability hook + 初始轨道注册进 state。

### 3.2 init 产出一览

| 文件 | 内容 | 被谁消费 |
|---|---|---|
| `.oracle-state.json` | 全局状态 + 轨道注册 + 占比 | 所有子 skill |
| `user-profile.md` | 创作者档案（身份/优势/变现/风格） | seed / learn-from / who-for / cover |
| `content-plan.md` | 内容规划（单一/双轨/三轨 + 占比 + 成功指标） | seed 分流 / recommend 比例过滤 / bump 分池 / status 看板 |
| `audience-profiles.md` | 各轨用户画像 | simulate-audience / who-for / seed 受众校准 |
| `rubric_notes.md` | 评分规则（按轨道分节） | score / predict / bump |
| 目录骨架 | predictions/ scripts/ candidates.md 等 | — |

---

## 4. 轨道机制（漏斗驱动，后续流程按 init 规划执行）

1. **轨道 = 漏斗层**。init 产出几轨就是几轨（1-3），后续所有 skill 按此执行，不硬编码。
2. **每轨四要素**：独立 rubric 权重、成功指标、review skill 路由、retro 窗口。
   - 破圈/认知类轨道（流量导向）→ review 走 oracle-who-for，retro 窗口 [3d]
   - 转化类轨道（获客导向）→ review 走 oracle-open-source，retro 窗口 [3d, 7d, 30d]，加载 conversion-track-playbook.md
3. **候选池每条标 track**；预测 header 加 track 字段；校准池按轨道分桶；bump 按轨道独立重打；看板分轨显示。
4. **seed 分流**按占比补稀轨；recommend 按占比过滤推荐。
5. 交叉题（一条内容跨两轨）算 0.5 + 0.5。
6. **规划可修订**：跑满若干期后，compass-retro 可建议调整占比/增删轨道——但需用户拍板并同步 state。

---

## 5. 26 个子 skill 完整清单

统一前缀 `oracle-`，功能词与原版一致。

### 阶段 0 · 初始化（一次性）

| # | skill | 功能 | 触发词 | 产出 |
|---|---|---|---|---|
| 1 | **oracle-init** | 首次 onboarding：五 Phase——基础配置 → 用户档案采访 → 内容漏斗采访（单一/双轨/三轨规划）→ 用户画像推导 → 脚手架落盘 + 装 hook | "初始化" / "init" / "首次使用" | state + user-profile.md + content-plan.md + audience-profiles.md + rubric_notes + 目录骨架 |
| 2 | oracle-learn-from | 导对标账号 5-10 条样本 → 拆 pattern → 派生 rubric 初始权重信号；可提取用户「声音样本」（风格特征） | "找对标" / "学这个账号" / "learn from" | benchmark.md + script_patterns.md + rubric 权重 |
| 3 | oracle-apprentice | 手艺层拆单条稿（钩子/节奏/金句/结构），四步闭环内化写法；支持视频转录 | "拜师" / "拆这条稿" / "apprentice" | study/<博主>/ 拆解档案 + 知识卡片 |
| 4 | oracle-migrate | state 文件 schema 版本链式迁移（dry-run + 备份 + 幂等） | "迁移" / "migrate" | 升级后 state |

### 阶段 1 · 选题 → 写稿

| # | skill | 功能 | 触发词 | 产出 |
|---|---|---|---|---|
| 5 | oracle-trends | 多 adapter 抓热点 → 去重 → 粗打分 → 入候选池 | "抓热点" / "fetch trends" | candidates.md + trends-history.jsonl |
| 6 | oracle-recommend | 按 rubric 排序候选池推荐 topN（**按 content-plan 占比过滤** + 锚点对比） | "推荐选题" / "next topic" | 控制台输出 |
| 7 | oracle-seed | 对话式选题（默认一次一个）：深挖用户经历 → 按 track 分流起 draft | "找选题" / "我想做一条 X" / "seed" | scripts/<id>.md draft + 作品目录 |
| 8 | oracle-score | 单稿 7 维打分 + composite，只看不落盘（rubric 缺时自动兜底 v0） | "打分这篇" / "score this" | 控制台评分 |

### 阶段 2 · 发布前打磨链（顺序敏感）

| # | skill | 功能 | 触发词 | 产出 |
|---|---|---|---|---|
| 9 | oracle-title | 生成 3-5 个标题候选（多结构类型 + 心理动因） | "给我标题" / "标题候选" | 控制台表格 |
| 10 | oracle-title-pick | 淘汰制评审选最优标题 → 改标题行 + 改文件夹名 + 触发钩子维度重判 | "选标题" / "哪个标题好" | 更新 draft + 目录改名 |
| 11 | oracle-description | 多平台简介生成（按 init 配置的平台集） | "写简介" / "视频描述" | append 到脚本发布文案段 |
| 12 | oracle-cover | 封面架构：统一框架 → 图像生成 prompt（按平台比例派生） | "封面" / "cover" | prompt/cover/ 目录 |
| 13 | oracle-no-ai-slop | AI 味检测与修正（16 模式 + 中文 AI 腔词表 + 口播适配）——**锁定预测前必跑** | "AI 味" / "去 AI 味" / "读着不顺" | 检测报告或改稿 |
| 14 | oracle-who-for | 采访式受众价值审查 ~8 问（流量/共鸣类轨道用；以 init 画像为基线逐稿深化） | "这是拍给谁的" / "who-for" | audience-brief.md |
| 15 | oracle-open-source | 采访式自我开源度审查 ~9 问 + 反套路镜子（转化类轨道用） | "自我开源" / "这条够真诚吗" | open-source-audit.md |
| 16 | oracle-simulate-audience | 评论区预演：**基于 init 用户画像**（audience-profiles.md）模拟「核心受众 / 一般关注」两类人群真实评论感受 | "模拟评论" / "换位思考" / "评论区预判" | 模拟评论 + 修改意见 |
| 17 | oracle-compliance | 平台合规审查：违禁词 / 限流风险双结论（机器层 + 实质层） | "合规检查" / "查违禁词" | 审查报告 |
| 18 | **oracle-predict** | **核心**：盲预测日志（7 维 + bucket + 概率分布 + 反事实；v1/v2/v3 多轮基点） | "启动预测" / "start prediction" | predictions/<id>.md（`## 预测` 段 immutable） |

### 阶段 3 · 拍摄 → 发布 → 衍生

| # | skill | 功能 | 触发词 | 产出 |
|---|---|---|---|---|
| 19 | oracle-shoot | 登记拍摄（buffer +1）；成稿与预测稿 diff 超阈值 → 触发 predict v2 | "拍了" / "shot" / "录完了" | state.shoots 队列 |
| 20 | oracle-publish | 发布登记（URL/平台/时间 → 预测 header + state，buffer -1）+ 发布前合规 gate | "已发布" / "I shipped it" / "发布链接是 X" | 更新预测 header + state |
| 21 | oracle-pinned-comment | 发布后黄金窗口生成各平台置顶评论（按轨道策略） | "置顶评论" / "引导评论" | append 到脚本置顶评论段 |
| 22 | oracle-derivative | T+1 衍生内容：从主作品裂变图文/短文 | "衍生内容" / "图文" | 衍生稿（作品目录内） |

### 阶段 4 · 数据回流

| # | skill | 功能 | 触发词 | 产出 |
|---|---|---|---|---|
| 23 | **oracle-retro** | T+N 数据回收 + 复盘（窗口按轨道配置），验证/推翻假设，提炼观察 | "复盘" / "retro this" / "T+3d 数据来了" | `## 复盘` 段 + report + rubric 观察 |
| 24 | oracle-compass-retro | 每 2 期账号级罗盘复盘：五维数据闸门 + 问题分类 + 阶段诊断 + **内容规划修订建议** | "罗盘复盘" / "账号诊断" | 诊断报告（只写候选不改 rubric/plan） |

### 阶段 5 · 进化 + 辅助

| # | skill | 功能 | 触发词 | 产出 |
|---|---|---|---|---|
| 25 | oracle-bump | rubric 升级（全量重打 + 排序一致性 ≥0.8 + 跨模型审核；按轨道独立）或 bucket 轻量重校 | "升级 rubric" / "bump" / "调整权重" | 新版 rubric_notes.md |
| 26 | oracle-status | 状态看板：buffer 颜色 / 各轨校准进度 / 待复盘 / 建议触发器 | "状态" / "看板" / "status" | 控制台看板 |

---

## 6. 完整链路图

```
━━━ 阶段 0：初始化（一次性）━━━
/oracle-init（基础配置 → 用户档案 → 内容漏斗采访[单一/双轨/三轨] → 用户画像 → 脚手架）
    ──→ (cold-start 强烈建议) /oracle-learn-from ──→ rubric 初始锚点
              └─(随时，手艺层)→ /oracle-apprentice

━━━ 阶段 1：选题 → 写稿 ━━━
/oracle-trends ──→ 候选池 ──→ /oracle-recommend（按 plan 占比过滤）
    ──→ /oracle-seed（按 track 分流）──→ draft
(轻量试分: /oracle-score；随时: /oracle-status)

━━━ 阶段 2：发布前打磨链（顺序敏感）━━━
/oracle-title → /oracle-title-pick → /oracle-description → /oracle-cover
    → /oracle-no-ai-slop（必跑）
    → [按轨道 review]  流量/共鸣轨: /oracle-who-for（以 init 画像为基线）
                       转化轨: /oracle-open-source
    → [可选] /oracle-simulate-audience（用 init 画像模拟评论区）
    → [可选] /oracle-compliance（任意轮可复检）
    → /oracle-predict v1 ──→ predictions/<id>.md（预测段 IMMUTABLE）

━━━ 阶段 3：拍摄 → 发布 → 衍生 ━━━
实际制作（AI 不可见，等用户回来）
    → /oracle-shoot（buffer+1；diff 超阈值 → predict v2）
    → 实际发布到平台
    → /oracle-publish（合规 gate → 登记 URL，buffer-1）
    → /oracle-pinned-comment（发布后即时）
    → /oracle-derivative（T+1 衍生）

━━━ 阶段 4：数据回流 ━━━
/oracle-retro（窗口按轨道 → 验证假设 → 观察入 rubric_notes → 限流排查 → 检测 bump 候选）
    └─ 每 2 期 → /oracle-compass-retro（账号级诊断 + 规划修订候选）

━━━ 阶段 5：rubric 进化 → 回到阶段 1 ━━━
/oracle-bump（按轨道：全量重打 + 跨模型审 + 一致性 ≥0.8）
    → 新 rubric ──→ 反哺 seed/score/predict/recommend ──→ 下一期

辅助: /oracle-status（任意时刻） /oracle-migrate（schema 升级）
```

**三个子闭环**：
- `init 画像 / review 采访 → predict 打分 → retro 验证` = 受众假设→预测→实测
- `retro → bump → 下一轮 predict 更准` = 主校准闭环
- `publish → compass-retro → 候选规则/规划修订 → 改进` = 协作自进化闭环

**主链路顺序铁律**：predict → （制作）→ shoot → （发布）→ publish → retro。publish 严格只用于「已实际发到平台且有真实 URL」。拍（shoot）与发（publish）分离，buffer 警戒依赖此区分。

---

## 7. 数据基础设施

### 7.1 用户项目目录结构（init 时生成）

```
<项目根>/                              # init 时用户配置
├── .oracle-state.json                 # 全局唯一 state
├── user-profile.md                    # 用户档案（init Phase 2）
├── content-plan.md                    # 内容规划：单一/双轨/三轨 + 占比（init Phase 3）
├── audience-profiles.md               # 各轨用户画像（init Phase 4）
├── rubric_notes.md                    # 评分规则（按轨道分节；缺时自动兜底）
├── candidates.md                      # 候选池（每条标 track）
├── benchmark.md                       # 对标账号
├── script_patterns.md                 # 写作 pattern（按轨道分节）
├── audience-brief.md                  # 逐稿受众 brief（跑过 who-for 时）
└── <NNN>_<标题>/                      # 每期作品一个文件夹
    ├── predictions/<日期>_<id>_<短标题>.md   # 预测 + 复盘（预测段 immutable）
    ├── prompt/cover/                        # 封面 prompt
    └── scripts/<标题>.md                     # 定稿（简介/置顶评论 append 末尾）
```

> state 全局唯一是硬规则：不建每期 state，所有 shoots/episodes/calibration_samples 合并在 `<项目根>/.oracle-state.json`。

### 7.2 .oracle-state.json 核心字段

```jsonc
{
  "schema_version": "1.0",
  "mode": "cold-start | calibration",
  "content_form": "opinion-video",          // 默认视频，可扩展
  "project_root": "<用户配置>",
  "platforms": ["bilibili", "douyin", "..."],
  "plan_type": "single | dual | triple",    // init 产出的规划类型
  "tracks": {
    "definitions": [
      { "id": "reach",  "funnel_layer": "破圈",  "name": "<用户命名>",
        "rubric_section": "rubric_notes.md#track-reach",
        "review_skill": "oracle-who-for",
        "success_metrics": ["播放", "涨粉", "同频评论"],
        "retro_windows_days": [3], "mix_ratio": 0.4 },
      { "id": "convert", "funnel_layer": "转化", "name": "<用户命名>",
        "rubric_section": "rubric_notes.md#track-convert",
        "review_skill": "oracle-open-source",
        "success_metrics": ["咨询数", "私信转化"],
        "retro_windows_days": [3, 7, 30], "mix_ratio": 0.6 }
      // 三轨时含 "cognition" 认知层
    ],
    "mix_ratio_note": "<占比与修订记录>"
  },
  "buffer": { "count": 0, "warning_threshold": 3, "critical_threshold": 0 },
  "shoots": [], "pending_retros": [], "episodes": [],
  "calibration_samples": { "by_track": {} },
  "last_published_file": null
}
```

### 7.3 关键协议文件（shared-references）

| 协议 | 内容 |
|---|---|
| blind-prediction-protocol.md | 原则 #1 完整规范（immutable 边界、_redo 路径、reconstructed 标记） |
| bump-validation-protocol.md | 原则 #2 完整规范（全量重打、排序一致性阈值、跨模型审核） |
| observation-lifecycle.md | 原则 #3 完整规范（观察如何被推翻/吸收/删除） |
| prediction-anatomy.md | 一份合格预测的 7 组件（含 cold-start 简化版） |
| candidate-schema.md | 候选项统一 schema（含轨道标签） |
| cadence-protocol.md | 节奏协议（buffer 警戒 + 选题策略 + 拍/发分离） |
| state-management.md | state 读写约定（全局唯一 + 追加语义） |
| revision-loop-protocol.md | 改稿闭环（review skill 共用 Phase 5） |
| migration-protocol.md | schema 演进哲学 + maintainer checklist |
| content-folder-schema.md | 作品目录 schema（泛化版） |
| content-funnel-protocol.md | **新增**：init 内容漏斗采访协议（三层漏斗 → 单一/双轨/三轨判定 + 占比 + 画像推导流程） |
| collaboration-contract.md | **新增**：协作契约（从 OP 偏好 + pitfalls 泛化，见 §9） |

---

## 8. references/ 目录（开放给用户）

**定位**：方法论参考资料库，**用户可自由添加**想参考的书籍、文档（如徐沪生《做号》转录、自己的行业笔记、其他方法论书摘）。子 skill 按需引用目录内文件。

**默认种子文件**：

| 文件 | 内容 |
|---|---|
| xu-zuohao-positioning-distill.md | 《做号》定位与画像方法论提炼（版权安全版）：定位第一性推导链 + 专业IP vs 网红四大区别 + 画像三法（商业模式反推/对标验证/账号回流验证）+ 人设三原则 + 平台策略 + **init Phase 2-4 采访问卷**（原创设计） |
| dbskill-essence-distill.md | dbskill 知识库精华提炼（dontbesilent，版权安全版）：定位选题 / 标题封面钩子 / 脚本写作 / 平台特性速查 / 对标五重过滤 / 转化心理双引擎 / 语言审查（AI味/爹味/模糊词）/ 发布运营 / 复盘诊断 九大模块 + **oracle 全流程接线表**（§10：26 个子 skill 逐个标注消费哪段） |
| content-funnel-theory.md | 徐沪生内容漏斗理论通用版摘要：三层漏斗（破圈/认知/转化）+ 蟑螂药案例 + 破小圈不破大圈 + 既要又要还要 + 高频阅读低频购买 + 三种人设——init Phase 3 的采访依据 |
| conversion-track-playbook.md | 转化类轨道手册（从 B 轨 13 条第一性原理 + 选题 6 问 + 4 步心理闭环评分泛化） |
| platform-notes.md | Windows/Obsidian/文件锁等平台特定坑（压缩备查） |

> **版权边界约定**：《做号》原书转录与《拆解》PDF、dbskill 完整知识库（12,307 推文原子）**均不随 skill 分发**，仅 OP 自用；skill 内只携带两份提炼文档（概念框架 + 原创表述，无原文段落复制）。compass-retro 的定位验证回路（私域质量/评论区职业构成/转化率链路）引自做号提炼 §3.3；no-ai-slop 的语言审查引自 dbskill 提炼 §7。

> 用户添加参考资料的约定：文件放 references/ 下即可，后续可深度讨论是否需要索引/注册机制（如 references/index.md 让 skill 按主题检索）。

---

## 9. 协作契约（从 OP 偏好泛化，默认生效）

1. **方案菜单**：改稿/修复默认出 2-4 个方案 + 每案特点/成本/风险 + ⭐推荐 + 等用户选；用户明确说「直接做/你就执行」才代选。
2. **双角度交叉验证**：每次改稿后重跑 score 对比（composite 前后值 + 各维度变化），不涨则回退提示；改稿日志同步贴对比，供 retro 回溯。
3. **真实数据原则**：禁止硬编占位时间/数字/事实；用 `[等真实数据]` 模糊标记 + 显式提醒；用户贴真值立即替换并回溯清污染。
4. **发现即改**：发现问题直接改，改完报告结果；不输出「我发现问题了」的过程叙述。
5. **术语即解释**：任何分流/分叉/几问的术语首次提出必须配「这是 X，对应 Y 决策」解释。
6. **假性确认防线**：用户说「按你的意思执行」→ 先复述将动的具体项再动手；没明说的决策点列出来等拍板。
7. **验证后报告**：任何「完成」声明前必须 stat/read 验证文件实际状态；跑脚本看输出 marker，不只看 exit code。
8. **不代答不甩锅**：出选项 + 标推荐 + 等选是默认；既不甩锅式提问，也不未经同意代选。

---

## 10. 新 skill 目录结构

```
<skill 仓库>/oracle-bone/
├── SKILL.md                    # 总协议 + 路由表 + 原则 + 轨道机制 + 协作契约
├── README.md                   # 门面
├── DESIGN.md                   # 本文档
├── CHANGELOG.md / LICENSE / .gitignore
├── install.sh / uninstall.sh
├── skills/                     # 26 个 oracle-*/SKILL.md
├── shared-references/          # §7.3 所列 12 份协议
├── starter-rubrics/
│   ├── opinion-video.md        # 观点视频（继承已拟合版，默认）
│   ├── opinion-video-zero.md   # v0 等权占位
│   ├── conversion-video.md     # 转化类轨道 starter（从 engineering-case-study 泛化）
│   ├── long-form-essay.md      # ⬜ 扩展位
│   └── short-form-text.md      # ⬜ 扩展位
├── templates/                  # 落到用户项目的骨架（user-profile / content-plan /
│                               #   audience-profiles / rubric_notes / prediction / retro /
│                               #   candidates / audience-brief / open-source-audit /
│                               #   benchmark / script_patterns / workflow / status / content.db）
├── hooks/                      # prediction-immutability / session-start / meta-logging
├── tools/                      # score-curve.py（预留 md-to-sqlite / validate-bump）
├── adapters/                   # trend-sources / perf-data / candidate-pool / script-extraction
├── references/                 # 开放参考资料库（§8：3 份默认种子 + 用户自由添加）
└── examples/                   # script_patterns 示例
```

---

## 11. 构建批次

| 批次 | 内容 | 产物 |
|---|---|---|
| 1 | 骨架 | SKILL.md（总协议+路由）+ README + install 脚本 + 目录树 |
| 2 | 核心协议 | shared-references 12 份（重点新写：content-funnel-protocol / collaboration-contract） |
| 3 | 主链子 skill | init（五 Phase 增强版）/ predict / shoot / publish / retro / bump / status |
| 4 | 选题与打磨子 skill | seed / trends / recommend / score / title / title-pick / description / cover |
| 5 | review 与质检子 skill | who-for / open-source / simulate-audience / no-ai-slop / compliance |
| 6 | 支撑子 skill | learn-from / apprentice / migrate / pinned-comment / derivative / compass-retro |
| 7 | 模板与 starter | templates/ + starter-rubrics/ + hooks/ + tools/ + adapters/ + references/ 种子 |

## 12. 已拍板决策记录

1. ✅ 命名：oracle-bone；子 skill 统一 oracle-* 前缀 + 功能词；**术语保持功能词，不用占卜意象词**
2. ✅ init 增强：用户档案 + 内容规划（单一/双轨/三轨）+ 用户画像；后续流程按规划执行
3. ✅ init 采访依据：《做号》方法论提炼（`references/xu-zuohao-positioning-distill.md`，版权安全版，落 template shared-references + oracle-bone/references 双份；原书转录不随 skill 分发）
4. ✅ dbskill 知识库精华提炼（`references/dbskill-essence-distill.md`，版权安全版，双份落盘）：九大模块 + 26 子 skill 接线表；重点消费方 = no-ai-slop（语言审查）/ learn-from（五重过滤+显式参数法）/ init 画像（付费者共性反共识）
5. ✅ oracle-simulate-audience 以 init 用户画像为根基
6. ✅ references/ 开放给用户自由添加参考资料（默认种子 5 份）
7. ✅ 内容形态：视频优先（opinion-video 为默认 starter）
8. ✅ state 文件：.oracle-state.json（与原版隔离）
9. ✅ 预测文件结构：保持原版（`## 预测` immutable / `## 复盘` 追加），不改四段卜辞制
