# founder-ip — 创始人 IP 战略层 Skill 系统

> 🎯 **为"非娱乐类创始人 IP"设计的战略层系统**
>
> 基于**徐沪生《个人IP全流程拆解》方法论** + **dontbesilent 实战派知识库** + **PLG 三大增长资产印证** + **你的访谈档案结论**（interview-profile.md，安装后自建）。
>
> 专门为产品已上线、通过内容获客的创始人 / OPC / 主理人设计，尤其是垂直专业领域（工程/法律/医疗/教育等）的非娱乐型 IP。

---

## 这是什么

一套**战略层 skill 系统**，帮创始人想清楚 5 件事：

1. **为什么做个人 IP**（`ip-strategy`）——立项决心、防网红思维坑、时间承诺、成功标准
2. **人设怎么定**（`ip-persona`）——内容型/专家型/真实型、起源故事、表达风格
3. **内容漏斗怎么设计**（`ip-content-funnel`）——三轨内容比例（A 破圈 / C 认知 / B 转化）、系列定位、利他选题库、GEO 长尾覆盖
4. **商业模式怎么搭**（`ip-business-model`）——咨询枢纽、流量/转化视频分离、变现路径
5. **OPC 流水线怎么整合**（`ip-opc-system`）——生产日程（示例基线：2 天 1 期）、AI 协作边界、瓶颈优化

**与 `cheat-on-content` 的分工**：
- `founder-ip` = **战略层**（一次性/低频决策）
- `cheat-on-content` = **执行层**（每周循环：选题/打分/预测/拍摄/复盘）
- founder-ip 产出的战略文档，作为 cheat-on-content 执行循环的**上下文和约束**

---

## 安装

### 前置条件
- 任一 skills-compatible 运行时（opencode / Claude Code / Codex / Cursor 等）
- （可选但推荐）`cheat-on-content` skill 作为执行层——未安装时本系统自动降级运行，不阻断

### 安装步骤

```bash
# 1. clone 到你的运行时 skills 目录（按 runtime 选路径）
git clone https://github.com/geats0422/founder-ip.git <你的 skills 目录>/founder-ip
```

| Runtime | skills 目录 |
|---|---|
| opencode | `~/.opencode/skills/` |
| Claude Code | `~/.claude/skills/` |
| Codex | `~/.codex/skills/` |
| 通用（多 agent 共享） | `~/.agents/skills/` |

```bash
# 2. 复制访谈档案模板（每个使用者一份，含个人数据，已被 .gitignore 排除）
cd <你的 skills 目录>/founder-ip/shared-references/
cp interview-profile.example.md interview-profile.md

# 3. 编辑 interview-profile.md，填入你的具体情况
# （或直接跑 /ip-strategy，系统会引导你完成访谈）
```

### 配置引用源

本仓库 **自包含可用的核心方法论**（`shared-references/` 下，无需额外配置）：

```text
shared-references/
├── xu-husheng-essence.md          # 徐沪生方法论精华（9 章索引）
├── xu-content-funnel-deep.md      # 徐沪生内容漏斗三层模型 + 经典案例库
├── xu-zuohao-index.md             # 《做号》完整书版索引
├── dontbesilent-index.md          # dontbesilent 知识库索引（指向外部原库）
├── geo-china-guide.md             # 国内 GEO 指南
├── plg-three-assets.md            # PLG 三大增长资产（scaleX 实战印证）
├── linkloud-growth-playbook.md    # LinkLoud 增长方法论（scaleX 实战印证）
├── loop-diagnostics.md            # 循环诊断（四阶段/数据诊断/守正出奇/价格带场域）
├── strategy-immutability.md       # 战略文档修改纪律（L1 严格不可改 / L2 季度留痕 / L3 月度滚动）
└── interview-profile.example.md   # 访谈档案模板（复制为 interview-profile.md 后填写）
```

**外部可选配置**（版权内容，不在仓库内）—— 配置后可回查原文，不配置也不影响 skill 运行：

```text
<your-reference-dir>/
├── dbskill/                        # dontbesilent 知识库（4176 个原子）
│   └── 知识库/
│       ├── 原子库/atoms.jsonl
│       └── Skill知识包/
└── xu-husheng-book/                # 徐沪生原书（MinerU 解析版）
    ├── 徐沪生个人IP全流程拆解.md
    └── images/
```

> ⚠️ 这些是**第三方版权内容**。`shared-references/` 下的索引文件（`dontbesilent-index.md` / `xu-husheng-essence.md`）已包含精华提炼，skill 可以直接用。配置外部原库只是为了**原文回查**（`[徐沪生 X.Y]` / `[DB xxx]` 的完整上下文）。

---

## 使用

### 首次使用（5 步引导）

跑完这 5 步，创始人 IP 的战略层就立起来了：

```
1. /ip-strategy       → 锁定战略 + 立项决心（最重要，所有后续的根基）
2. /ip-persona        → 基于战略定人设
3. /ip-business-model → 基于战略 + 人设定变现路径
4. /ip-content-funnel → 基于 persona + business-model 定内容漏斗
5. /ip-opc-system     → 整合所有 + 现有 cheat-on-content 流水线
```

### 日常使用

战略层跑完后，每周走 `cheat-on-content` 的执行循环即可：

```
cheat-seed → score → predict → shoot → publish → retro
```

### 定期复盘

| 频率 | 动作 |
|---|---|
| 每月 | `/ip-opc-system --optimize`（流水线 + GEO 自检）|
| 每季度 | `/ip-strategy --review` + `/ip-business-model --review` + `/ip-content-funnel --review` |
| 每半年 | `/ip-persona --review` |

---

## 方法论溯源（三源 + 一印证）

所有建议必须可追溯到以下来源之一：

| 源 | 角色 | 引用格式 |
|---|---|---|
| 1. 你的访谈档案结论 | 最高优先级（具体场景）| `[访谈 Q8]` |
| 2. 徐沪生《个人IP全流程拆解》| 主方法论（创始人 IP 的"道"）| `[徐沪生 5.3]` |
| 3. dontbesilent 知识库 | 实战派补充（商业变现的"术"）| `[DB 2024Q4_096]` |
| 4. PLG 三大增长资产 | 实战印证（四方支撑）| `[PLG 创始人IP]` |

**三方一致 = 强信号**。当 founder-ip 给出某个建议时，如果同时有徐沪生 + dontbesilent + PLG 的印证，说明这不是单一视角的偏见。

---

## GEO 横切维度

本系统内置**国内 GEO（Generative Engine Optimization）指南**——面向 AI 搜索的优化。详见 `shared-references/geo-china-guide.md`。

- 国内 AI 搜索生态地图（Kimi/豆包/DeepSeek/元宝/秘塔 等）
- GEO 4 个核心动作（Coverage / Structure / Authority / Citation）
- 月度 GEO 自检模板
- 与 founder-ip 其他 skill 的衔接

---

## 5 个子 skill 一览

| Skill | 对应徐沪生章节 | 核心产出 | 使用频率 |
|---|---|---|---|
| `ip-strategy` | 1+2+9 | 战略备忘录（为什么做 + 防坑 + 立项决心）| 一次性 + 季度回顾 |
| `ip-persona` | 5 | 人设定位文档（三要素 + 起源故事 + 表达风格）| 一次性 + 半年回顾 |
| `ip-content-funnel` | 3+6.1+6.2 | 年度内容漏斗（三轨比例 + 选题库 + GEO 覆盖）| 半年/年度更新 |
| `ip-business-model` | 4 | 商业画布（咨询枢纽 + 流量/转化分离）| 季度更新 |
| `ip-opc-system` | 8（改造版）| OPC 生产 SOP：生产日程（示例基线 2 天 1 期）+ AI 协作 + GEO 自检 | 持续优化 |

---

## 三条不可妥协原则

1. **方法论基于可追溯源，不凭空发明**
2. **战略文档分级保护，变更需留痕**（strategy-memo / persona-charter 严格不可改；canvas / funnel 季度可调须附数据依据，详见 `shared-references/strategy-immutability.md`）
3. **执行层不重造**（单条视频的选题/脚本/预测/复盘，走 cheat-on-content）

---

## 与其他 skill 的关系

| Skill | 关系 |
|---|---|
| `cheat-on-content` | 执行层互补。founder-ip 产战略，cheat 跑执行循环 |

---

## License

AGPL-3.0（与 `cheat-on-content` 保持一致）

---

## 致谢

- **徐沪生**（《个人IP全流程拆解》作者，一条创始人）—— 主方法论来源
- **dontbesilent**（X/Twitter @dontbesilent12）—— 实战派知识库来源
- **scaleX 活动**（2026-07-19）—— PLG 三大增长资产印证
- **cheat-on-content** skill —— 执行层架构参考

