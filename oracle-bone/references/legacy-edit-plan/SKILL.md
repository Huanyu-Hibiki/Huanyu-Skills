---
name: oracle-edit-plan
description: 剪辑计划 + 成片验收双模式。plan 模式（拍摄登记后）：探测素材清单（ffprobe 或口头盘点，禁止从文件名脑补）→ 基于 draft 调性产出可执行的剪辑计划工件（节奏区间表 / 每个剪切点带理由 / 转场词汇表收敛 / 声音设计 / 邻接多样性 / B-roll 覆盖核对）。accept 模式（成片剪完后）：对照计划机械验收 + 幻灯片感自查 + 逐条带修法的问题清单（审稿三轴），通过后才进 publish。触发词："剪辑计划"/"出剪辑计划"/"成片回来了"/"验收成片"/"成片质检"/"edit plan"。
argument-hint: "<作品目录> [— mode: plan|accept]"
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

> 历史归档，仅供迁移与来源审计；不作为可安装入口。当前制作计划、包装和成片 QA 统一使用 `video-production-workflow`。

# /oracle-edit-plan — 剪辑计划与成片验收

把"实际制作"从黑箱变成**可计划、可验收**：拍摄登记后出一份剪辑计划（AI 按稿子的调性和钩子设计镜头节奏），用户照着剪（或剪完拿来对照），成片回来后逐条验收——验收过了才值得发布。

**为什么存在**：预测偏了，retro 分不清是内容问题还是制作问题——烂剪辑吃掉好稿子是完播率杀手。本 skill 让制作质量第一次进入链路的记录范围。

## 模式分流

- **plan**（默认）：oracle-shoot 登记完成后 → 出剪辑计划，落 `edits/edit-plan.md`
- **accept**：成片剪完 → 对照计划验收，结论落 `edits/acceptance.md`
- 没跑过 plan 直接 accept → 允许（降级：只跑通用验收清单，标注「⚠️ 无剪辑计划基线，节奏类检查跳过」）

## plan 模式

### Phase 0: 前置

1. 读 state → 未 init 提示先跑 /oracle-init
2. 验证作品目录 + `scripts/<id>_final.md`（shoot 定稿快照）存在——缺 → 提示先跑 /oracle-shoot；本 skill 不登记 buffer
3. 读 draft header 的调性 / 轨道 / 目标时长 / 开场策略（开场原型决定前 5 秒的剪辑密度）

### Phase 1: 素材清单探测（禁止从文件名脑补）

| 如果 | 则 |
|---|---|
| 素材在电脑上（目录路径给了） | ffprobe 逐文件探测：分辨率 / 时长 / 有无声轨。示例（按实际扩展名调整）：`for f in <素材目录>/*.mp4; do echo "== $f"; ffprobe -v error -show_entries format=duration -select_streams v:0 -show_entries stream=width,height -of default=noprint_wrappers=1 "$f"; done` |
| 素材在手机 / 口头盘点 | 问三件事：口播条数与总时长大概多少 / B-roll（空镜/演示画面）有几段各几秒 / 有没有竖屏横屏混拍 |
| 什么都不给 | 🔴 停下要素材信息——**绝不按文件名或想象推测素材内容**（协作契约 #3） |

探测后产出**规划含义**（三段以内）：素材总时长 vs 成片目标时长的覆盖率（口播类建议 ≥3:1，低于 2:1 明示"可选素材偏紧"）/ 混拍分辨率提示 / 关键缺口（如"没有结尾 CTA 画面"）。

### Phase 2: 出剪辑计划 → 落 `edits/edit-plan.md`

```markdown
# 剪辑计划 — <NNN>_<标题>

## 0. 素材探测
[清单 + 规划含义]

## 1. 节奏定调（调性 → 镜头时长参考区间）
- 调性：<来自 draft header> → 口播段 <X-Y 秒/镜头>、B-roll 段 <X-Y 秒>
- 前 5 秒（开场原型 <名>）：钩子句镜头 <更短区间>，第一剪切点不晚于 <N> 秒
- 成片总时长目标：<目标时长> ±10%

## 2. 剪切点清单（每刀必带理由——写不出理由的剪切点先别剪）
| # | 片段 | 进点意图 | 时长 | 理由（一行） |
|---|---|---|---|---|
| 1 | 口播-钩子 | <起手证据画面> | 2.5s | 首句信息缺口在第 2 句，切走留悬念 |

## 3. 转场词汇表（全片 ≤4 种，本片选定：<列出>）
- 禁用清单：扫光 / 翻页 / 故障风 / 拉镜 Zoom——社媒模板腔，出现即重剪

## 4. 声音设计
- 主轴：口播（任何画面切换不得打断一句话中间，除非卡情绪重音）
- 跨切：环境声/音乐比画面提前 ~0.5s 滑入下一镜（焊住硬切，比转场特效有效）
- 音乐：<来源/是否需要>；金句后可留**全片唯一一处** ≤2s 静音留白

## 5. 邻接多样性
- 相邻两镜不同景别或不同主体；同机位连用 ≤2 刀；同方向运动镜不连排

## 6. B-roll 覆盖核对
- 需要画面的口播段落：<列表> ↔ 可用素材：<对应>；缺口：<明示，建议补拍或用字幕卡>

## 7. 字幕计划
- <逐句字幕 / 关键句字幕>；安全区提醒（各平台 UI 遮挡位）

## 8. 包装规格（可选——study/<博主>-apprentice/<标题>/packaging-notes.md 或 cover-patterns.md 存在时）
- 逐系统搬运规格（视觉系统六元组 + 动效四语义 + 词锚，语言见 references/packaging-vocabulary.md）；
  词锚直接沿用"transcript 第 N 段"——执行侧（video-production-workflow）的词级时间戳会把它兑现成秒
- 本期明确**不做**的包装（素材/工具够不着的）如实列出，不虚设规格
```

🔴 **CHECKPOINT**：计划是建议——用户确认 / 改某节 / 不用计划直接剪。确认后用户去剪（AI 不可见）。

## accept 模式

### Phase 1: 拿成片

用户给成片文件路径 → ffprobe 探测总时长 / 分辨率 / 音轨存在性；只有口头描述 → 走降级清单（标注未经机械核查）。

### Phase 2: 对照验收（审稿三轴，见协作契约 #12）

**机械核查**（有计划基线时）：

1. 总时长 vs 目标 ±10%？超 → 指出最长的三个段落
2. 前 5 秒：开场钩子句是否在成片最前（对照 draft 开场策略）？
3. 转场是否都在计划的词汇表内？出现禁用转场 → 指出时间点
4. 一句话中间被画面切换打断的次数（卡情绪重音除外）
5. 静音留白 ≤1 处？

**幻灯片感自查**（原生六项，各 ✅/⚠️ + 指位）：

- 同一画面停留过长（口播类 >8s 无变化）？
- 装饰性空镜（画面与正在讲的内容无关）？
- 动态不足（连续静止构图）？
- 意图不明的镜头（说不出它支撑哪句话）？
- 文字堆砌（同屏字幕 + 贴纸 + 大段标题）？
- 口说无凭的"电影感"（镜头语言在暗示稿子没兑现的东西）？

**包装验收**（计划含「包装规格」节时）：逐系统对照——动效是否落在预定的词/句上（词锚核对）？每种字幕配置可读否？共享布局在内容替换后是否仍成立？装饰性动效是否挤占了信息动效？

**输出纪律（契约 #12）**：每条问题指到**具体镜头/时间点**；发现一类问题扫完同类；critical 必带修法（"第 3 刀 12s 处两镜同机位 → 对调 2/3 或中间垫 B-roll"）——提不出修法的标「待查」不阻塞。**最多 2 轮往返**，之后带警告放行，卡点留给数据复盘。

### Phase 3: 验收结论 → 落 `edits/acceptance.md`

- ✅ 通过（含带警告通过）→ 报清单，提示走 publish 链路（登记 URL，不催流程）
- ❌ 不通过 → 问题清单交用户修片 → 修完重新 accept（Phase 1）
- 成片时长 vs 预测的 typical_duration 差 >30% → 提示"成片形态和预测假设差得远，建议 predict v2（basis=post_shoot_pre_publish 同款逻辑）"——用户决定

## Key Rules

1. **素材探测先行**——不按文件名脑补素材；口头盘点三问兜底
2. **每刀带理由**——剪辑计划里写不出理由的剪切点不进计划
3. **转场词汇 ≤4**——收敛是风格，不是限制
4. **验收逐条指位 + 带修法**——审稿三轴（契约 #12），最多 2 轮
5. **不碰制作管线**——本 skill 只产出 edits/ 下的计划与验收文档，不移动/不改用户素材与工程文件

## Refusals

- 「你直接帮我剪」 → 越界。本 skill 出计划与验收，不渲染成片（渲染是制作管线的事）
- 「不用看素材了，你按常规节奏排」 → 拒绝 Phase 1 空跑。没有素材清单的计划是猜的
- 「验收差不多就行，别挑刺了」 → 降级为"带警告通过"并记录未决项——不是静默放行

## Integration

```
oracle-seed → oracle-voice → oracle-title → description → cover → no-ai-slop
    → 按轨道 review → oracle-predict → 实际制作 → oracle-shoot（buffer+1）
    → oracle-edit-plan plan（剪辑计划）→ 用户剪辑 → oracle-edit-plan accept（验收）
    → 实际发布 → oracle-publish
```

可选步骤——有自己剪辑心法的用户可跳过 plan；accept 在发布前任何时候可跑。retro 可读 acceptance.md 区分"内容偏差 vs 制作偏差"。

## 交接给视频生产（video-production-workflow，可选）

执行侧管线（分镜/剪映草稿/B-roll 生成/装配/成片）在姊妹 skill video-production-workflow（下称 VPW）——本 skill 出**内容侧意图**，执行权威在 VPW 自己的闸门，**不越界**。交接按其 [handoff-contracts](../../../video-production-workflow/shared-references/handoff-contracts.md) 打包：

- **单机**（两个 skill 同一 Agent/机器）：把定稿脚本（→ `video scripts/manuscript.md`，带 YAML 头 source=oracle-bone）+ edit-plan.md + packaging-notes.md 复制到 VPW 项目根 `video scripts/`，用户喊 `/video-init --manuscript` 接管；broll/motion 意图可整理为其明文欢迎的 `broll-compose.json` / `motion_request_list.md`。两套项目目录约定不同，**不合并**
- **双机**（本机内容+验收，另一台剪辑机装 VPW/剪映）：产出**制作交接包**——`edits/handoff-manifest.md` 清单（文件 + 用途）+ 定稿 + edit-plan.md + packaging-notes.md，用户经 git/网盘传到 B 机；VPW 在 B 机自闭环（它的 state/审批不跨机），成片 + master.srt 回传本机作品目录后走 accept 验收
- 中间过程对本 skill 不可见（"实际制作 AI 不可见"原则的跨 skill 版）；收片后照常验收，机检数值可参考 VPW 的 qa-report
