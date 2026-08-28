---
name: founder-ip
description: 创始人 IP 战略层 skill 系统，基于徐沪生《徐沪生个人IP全流程拆解》方法论 + 用户深度访谈结论。覆盖**战略/人设/内容漏斗/商业模式/OPC系统**五层，专门为"非娱乐类创始人 IP"设计。与 `cheat-on-content`（执行层：选题/打分/预测/复盘）互补——本系统产出**战略文档**喂给 cheat-on-content 的执行循环。**不重复造执行层轮子**。适用对象：产品已上线、通过内容获客的创始人/OPC/主理人，尤其是垂直专业领域（工程/法律/医疗/教育等）的非娱乐型 IP。触发词："创始人IP战略"/"ip战略"/"人设定位"/"内容漏斗"/"商业画布"/"OPC系统"/"立项"/"起号"/"founder ip"。**首次使用建议从 /ip-strategy 开始**。
argument-hint: "[— phase: strategy|persona|content-funnel|business-model|opc-system]"
allowed-tools: Bash(*), Read, Write, Edit, Grep, Glob, Skill
---

# Founder IP / 创始人 IP 战略层系统

> 🎯 **为"非娱乐类创始人 IP"设计的战略层系统**
>
> 基于徐沪生《个人IP全流程拆解》方法论（一条创始人，全网 175 万粉丝，近 2000 名 IP 训练营学员的经验沉淀）+ 用户深度访谈结论。
>
> **核心定位**：创始人 IP ≠ 网红 IP。娱乐网红那套（抄爆款、蹭热点、搞笑耍宝、每天 10 条盲盒）对创始人不仅无效，而且有毒。
>
> **与 cheat-on-content 的分工**：
> - `founder-ip` = **战略层**（一次性/低频决策）：为什么做、人设怎么定、内容漏斗怎么设计、商业模式怎么搭、OPC 流水线怎么整合
> - `cheat-on-content` = **执行层**（每周循环）：选题/打分/盲预测/拍摄/发布/复盘
> - founder-ip 产出的战略文档，作为 cheat-on-content 执行循环的**上下文和约束**

---

## 三条不可妥协原则

任何一条被违反，整个战略层退化为"拍脑袋的自嗨"。🔴 **STOP：如果用户要求打破其中任何一条，拒绝执行并说明原因**（不是软化措辞，是拒绝）。

1. **方法论基于可追溯源，不凭空发明**：所有战略建议必须可追溯到（a）徐沪生原书章节、（b）用户访谈结论、（c）dontbesilent 知识库原子、（d）PLG 三大增长资产印证 之一。不接受"我觉得应该 X"这类无依据判断。完整引用：[shared-references/xu-husheng-essence.md](shared-references/xu-husheng-essence.md) + [shared-references/interview-profile.md](shared-references/interview-profile.md) + [shared-references/dontbesilent-index.md](shared-references/dontbesilent-index.md) + [shared-references/plg-three-assets.md](shared-references/plg-three-assets.md) + [shared-references/linkloud-growth-playbook.md](shared-references/linkloud-growth-playbook.md)。

2. **战略文档 immutable，变更需 version bump**：分级保护——**strategy-memo / persona-charter 严格不可改**（`## 决策` 段定稿后只能往 `## 修订记录` 追加，改战略 = 重大事件，需明示理由 + 影响评估）；**business-model-canvas / content-funnel 季度可调但留痕**（调整必须写入修订记录段并附数据依据）。完整规范：[shared-references/strategy-immutability.md](shared-references/strategy-immutability.md)。

3. **执行层不重造**：本系统**不**生成单条视频的选题/脚本/预测/复盘——那是 cheat-on-content 的领地。本系统只产出**战略/规划/SOP 文档**。如用户要求"帮我写这条视频的脚本"，路由到 `/cheat-seed` 而非在本系统内处理。

---

## 五层架构

```
┌─────────────────────────────────────────────────┐
│  战略层（一次性决策 + 季度回顾）                 │
│  /ip-strategy → /ip-persona → /ip-business-model│
└──────────────────┬──────────────────────────────┘
                   ↓ 喂弹药
┌──────────────────────────────────────────────────┐
│  规划层（半年/年度更新）                          │
│  /ip-content-funnel（年度内容漏斗 + 选题库）      │
└──────────────────┬──────────────────────────────┘
                   ↓ 喂弹药
┌──────────────────────────────────────────────────┐
│  执行层（每周循环）← 复用 cheat-on-content       │
│  cheat-seed → score → predict → shoot →          │
│  publish → retro                                  │
└──────────────────┬──────────────────────────────┘
                   ↑ 整合 + SOP
┌──────────────────────────────────────────────────┐
│  系统层（持续优化）                               │
│  /ip-opc-system（OPC 流水线 + 生产日程）          │
└──────────────────────────────────────────────────┘
```

---

## ⭐ GEO 横切维度（融入 content-funnel + opc-system）

**GEO**（Generative Engine Optimization，面向 AI 搜索的优化）不是独立 skill，而是**横切维度**，融入两个子 skill：

| 落点 | 动作 | 完整指南 |
|---|---|---|
| `ip-content-funnel` | 选题 = GEO 长尾关键词库（双重复用）| [shared-references/geo-china-guide.md](shared-references/geo-china-guide.md) |
| `ip-opc-system` | 月度 GEO 自检（问 5 个 AI 搜索引擎）| 同上，第 6 章 |

> **核心理念**：GEO 对你来说不是新工作，而是给现有内容加"AI 可读性"滤镜。完整方法论、国内 AI 搜索生态地图、4 个核心动作、月度自检模板，全部在 [geo-china-guide.md](shared-references/geo-china-guide.md)。

---

## 路由表（触发词 → 子 skill）

| 用户说 | 调用 | 前置条件 | 产出 |
|---|---|---|---|
| "创始人IP战略" / "ip战略" / "ip-strategy" / "立项" / "起号" / "我该不该做IP" | `/ip-strategy` | 无（这是入口） | `strategy-memo.md` |
| "人设定位" / "ip-persona" / "我的人设是什么" / "张三怎么设定" | `/ip-persona` | 建议 strategy 已跑 | `persona-charter.md` |
| "内容漏斗" / "ip-content-funnel" / "年度规划" / "ABC比例" / "选题库" | `/ip-content-funnel` | persona 已跑 | `content-funnel.md` + `topic-pool.md` |
| "商业画布" / "ip-business-model" / "怎么变现" / "咨询漏斗" | `/ip-business-model` | strategy 已跑 | `business-model-canvas.md` |
| "OPC系统" / "ip-opc-system" / "生产流水线" / "2天1期怎么排" | `/ip-opc-system` | 建议其他都跑完 | `opc-sop.md` |
| "创始人IP状态" / "ip-status" / "战略看板" | 内置轻量 status（见下） | 任意时刻可调 | 控制台输出 |

**Mode detection**（首次接到触发词时执行）：
1. 检查当前目录是否有 `strategy-memo.md` → 没有 → 强烈建议先跑 `/ip-strategy`
2. 检查 5 份核心文档的存在性，给出"战略层完整度"看板
3. 不强制阻断——用户可以从任意子 skill 开始，但会提示依赖关系

---

## 内置 status（轻量看板）

任意时刻用户说 "ip-status" / "战略看板"，输出：

```
🎯 Founder IP 战略层看板

文档完整度：
  ✅ strategy-memo.md      (YYYY-MM-DD 定稿)
  ✅ persona-charter.md    (YYYY-MM-DD 定稿)
  ⚠️  content-funnel.md     (未创建 → /ip-content-funnel)
  ✅ business-model-canvas.md
  ⚠️  opc-sop.md            (未创建 → /ip-opc-system)

下次回顾时间：
  - strategy:    2026-Q4 回顾
  - persona:     2026-10-27 半年回顾
  - funnel:      季度滚动更新

与 cheat-on-content 的衔接：
  - 上次 /cheat-retro: 2026-07-20
  - 下次建议: 本周内
```

---

## 失败分支（fallback）

| 触发条件 | 一线处理 | 仍失败兜底 |
|---|---|---|
| 路由目标不存在（如 `cheat-on-content` 未安装，`/cheat-seed` 不可达） | 告知缺失项 + 指向其 README 安装章节 | 把待执行需求暂记 `founder-ip/pending-routes.md`（一行一条：日期 + 需求 + 目标 skill；该文件由本表创建，安装后按行补跑、跑完划掉）；**不硬生成执行层产物** |
| 子 skill 产出文档互相矛盾（如 strategy 使命 vs canvas 变现策略） | 以 strategy-memo（L1 根基）为准，向用户明示冲突 | 提示跑矛盾方的 `--review` 修订对齐；对齐前该组文档不作为 cheat 执行层的上下文 |
| 当前目录不是 IP 项目目录（无 `founder-ip/`，用户只是咨询） | 正常路由，提示"产出将落在 `<当前目录>/founder-ip/`" | 用户指定其他目录 → 按指定目录落盘并回显路径 |

---

## 🔴 必须拒绝的请求（任一命中 → 拒绝并说明原因，不静默执行、不软化后照做）

| 用户说 | 为什么拒 | 拒后出路 |
|---|---|---|
| 「帮我直接写这条视频的脚本」 | 执行层不重造（原则 #3） | 路由 `/cheat-seed`；未安装则走上方失败分支表第 1 行 |
| 「战略文档我改个字就行，不用记录修订」 | 违反原则 #2，改战略必须留痕 | 走 [strategy-immutability.md](shared-references/strategy-immutability.md) 修订记录格式，改一个字也追加记录 |
| 「这个建议不用依据徐沪生或访谈，按你经验来」 | 违反原则 #1，无据建议 = 凭空发明 | 请用户给出新依据来源并记入修订记录；给不出 → 维持原建议 |
| 「跳过 ip-strategy，直接做人设」 | 不阻断，但人设可能偏离真实战略 | 明示风险后继续；后续 /ip-strategy 定稿时若冲突 → 以 strategy-memo 为准走修订 |
| 「5 份文档一次生成」 | 每份需要用户参与决策，批量生成 = 自嗨 | 一次跑一个；着急的话按引导路径顺序 `/ip-strategy` → `/ip-persona` → `/ip-business-model` → `/ip-content-funnel` → `/ip-opc-system` |

---

## 项目目录结构（用户工作目录）

在用户的 OPC/content project 根目录使用时，5 份核心文档统一放在 `founder-ip/` 下：

```text
<user-project>/
├── founder-ip/
│   ├── strategy-memo.md           # /ip-strategy 产出
│   ├── persona-charter.md         # /ip-persona 产出
│   ├── content-funnel.md          # /ip-content-funnel 产出
│   ├── topic-pool.md              # /ip-content-funnel 产出（选题库）
│   ├── business-model-canvas.md   # /ip-business-model 产出
│   └── opc-sop.md                 # /ip-opc-system 产出
├── content ops/cheat-on-content/  # 执行层产物（cheat 系统的）
└── videos/                        # 视频工程
```

5 份文档之间通过**相对路径引用**（不是 state file），保持简单透明。

---

## 方法论溯源

本系统的所有判断、建议、标准，必须可追溯到以下**三个来源**之一：

1. **徐沪生《个人IP全流程拆解》原书**（主方法论）：路径见 [shared-references/xu-husheng-essence.md](shared-references/xu-husheng-essence.md)（精华提炼，按章节索引）+ [shared-references/xu-content-funnel-deep.md](shared-references/xu-content-funnel-deep.md)（内容漏斗三层模型 + 蟑螂药/米其林等案例深度展开）。徐沪生讲的是创始人 IP 的"**道**"——为什么做、不做什么、长期主义。姊妹书**《做号》（完整书版，162 图）**独家增量已提炼至 [shared-references/xu-zuohao-index.md](shared-references/xu-zuohao-index.md)：自序"转型不转行"起源故事范本（ip-persona Q2 用）+ 第五章选题挖掘问题清单（cheat-seed 深挖用）。

2. **使用者访谈档案**（具体场景）：路径见 [shared-references/interview-profile.md](shared-references/interview-profile.md)（28 问完整记录 + 关键决策清单——**每个使用者自己的档案**，模板见 interview-profile.example.md）。这是使用者的具体情况，优先级最高。

3. **dontbesilent 知识库**（实战派补充）：路径见 [shared-references/dontbesilent-index.md](shared-references/dontbesilent-index.md)（4,176 个知识原子索引）。dontbesilent 讲的是商业变现的"**术**"——怎么定价、对标、转化、避免商业幻觉。原库为**外部可选配置**（版权内容，不在仓库内），获取方式见 [README.md](README.md) 的"外部 reference 配置"段。

**引用格式**：
- `[徐沪生 2.3]` — 徐沪生原书第 2.3 节
- `[访谈 Q8]` — 访谈第 8 问
- `[DB 2024Q4_096]` — dontbesilent 原子 ID（可直查 `原子库/atoms.jsonl`）
- `[DB content_内容创作方法论]` — dontbesilent 知识包名

**三源优先级**：访谈结论 > 徐沪生 > dontbesilent。
**冲突处理**：明示冲突 + 让用户判断（基于具体场景）。永远标注视角差异，不让用户以为只有一个正确答案。

**鼓励双视角对照**：子 skill 在关键建议处，同时引用徐沪生 + dontbesilent，格式见 [dontbesilent-index.md](shared-references/dontbesilent-index.md) 的"子 skill 引用指南"段。

### 📌 印证源（四方支撑）

除三源外，以下来源作为**实战印证**，与三源形成四方支撑（互相验证，增强可信度）：

4. **scaleX 活动实战印证**（PLG 三大资产 + LinkLoud 增长方法论）：路径见 [shared-references/plg-three-assets.md](shared-references/plg-three-assets.md) + [shared-references/linkloud-growth-playbook.md](shared-references/linkloud-growth-playbook.md)
   - `plg-three-assets.md`：硅谷增长专家李艳颖的"渠道+内容+创始人IP=增长引擎"框架，**完全印证** founder-ip 系统
   - `linkloud-growth-playbook.md`：Gavin Newton-Tanzer 的增长方法论（共性提取版），补充了 CLG/7次法则/KOC>kol/品牌基调等维度
   - 引用格式：`[PLG 三大资产]` / `[Wispr Flow 案例]` / `[LinkLoud KOC]` / `[LinkLoud 7次法则]`

### 🔧 诊断框架（循环诊断）

5. **循环诊断方法论**（四阶段状态机 + 数据诊断 + 守正出奇 + 价格带场域）：路径见 [shared-references/loop-diagnostics.md](shared-references/loop-diagnostics.md)（提炼自开源 ip-strategist skill，与三源体系融合）
   - **四阶段状态机**：起号期/稳定上升期/瓶颈期/爆款后续航——`ip-strategy --review` 的阶段判断工具
   - **数据诊断简版**：波赞比/赞粉比/完播曲线异常点/控制变量——`ip-opc-system --optimize` 的月度自检
   - **守正出奇节奏**：70分铺量+定期试爆+偶尔转化（时间维度，与三轨类型比例正交）——`ip-content-funnel` 的节奏设计
   - **价格带场域匹配**：0-50元短视频 / 几千-几千直播间 / 几千+私域——`ip-business-model` 的成交场域校验
   - **认知沉淀三档归档**：✅ 已验证 / ❓ 待验证 / ❌ 已证伪——所有 `--review` 模式的修订记录规范
   - 引用格式：`[循环诊断 阶段]` / `[循环诊断 完播曲线]` / `[循环诊断 守正出奇]` / `[循环诊断 价格带]`

> 💡 **四方支撑的价值**：当 founder-ip 给出某个建议时，如果同时有徐沪生 + dontbesilent + scaleX 实战（PLG + LinkLoud）的印证，用户可以**更确信这不是单一视角的偏见**。

---

## 与其他 skill 的关系

| Skill | 关系 |
|---|---|
| `cheat-on-content` | **执行层互补**。founder-ip 产战略，cheat 跑执行循环。cheat-init 时会读取 founder-ip 文档作为 context |

---

## 引导路径（首次使用建议）

用户第一次进入 founder-ip 系统：

```
1. /ip-strategy       → 锁定战略 + 立项决心（最重要，所有后续的根基）
2. /ip-persona        → 基于战略定人设
3. /ip-business-model → 基于战略 + 人设定变现路径
4. /ip-content-funnel → 基于 persona + business-model 定内容漏斗
5. /ip-opc-system     → 整合所有 + 现有 cheat-on-content 流水线
```

跑完这 5 步，创始人 IP 的战略层就立起来了，后续每周走 cheat-on-content 的执行循环即可。

🔴 **CHECKPOINT**：引导路径一次只跑一份文档——每份在关键决策处停下等用户拍板，定稿落盘前先展示决策摘要供确认；用户未确认不进入下一份（拒绝表第 5 行的执行化）。

---

## 当前版本

- **版本**：1.2.0
- **创建日期**：2026-07-27
- **最近变更**：2026-08-26 分发通用化——confirm 模式/前言措辞去定制、shared-references 场景示例声明化（工程合规示例标注"替换为你的领域"）、移除个人生态地图与本地路径、README 多 runtime 安装；此前 1.1.0 为 darwin 优化轮（轨命名统一 / 显性检查点 / 断链修复 / 三段式 Refusals）
- **方法论来源**：徐沪生《个人IP全流程拆解》（MinerU 解析版）
- **访谈框架**：28 问深度访谈（每个用户建立自己的 `shared-references/interview-profile.md`，模板见 `interview-profile.example.md`，已被 .gitignore 排除不入库）
- **下一步**：用户确认后从 `/ip-strategy` 开始
