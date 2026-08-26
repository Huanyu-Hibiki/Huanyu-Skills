---
name: oracle-learn-from
description: 从对标账号导入 script + 数据 → 拆 pattern + 派生 rubric 初始信号 → 写到 benchmark.md / script_patterns.md / rubric_notes.md。**工具最早期信号的来源**——cold-start 用户没自己历史时全靠对标，有历史的也建议至少 1 个对标做 sanity check。触发词："学这个账号"/"拆这几个对标视频"/"learn from"/"导入对标账号"/"找对标"。
argument-hint: "<账号名> [— append | --replace] [— track: <id>]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, WebFetch, Skill
---

# /oracle-learn-from — 对标账号导入

工具早期最重要的信号源是**对标账号**——init 完没数据，rubric 等权 v0 等于占星。找一个"你想做成那样"的账号，导入 5-10 条高/中/低样本，工具就有 anchor。

后期当某轨 calibration_samples ≥ 10 时，benchmark 影响自然减弱——你的真实数据成为主信号。但 benchmark.md **不删**，仍是 seed 的 reference frame。

**对标筛选方法**（消费 `references/dbskill-essence-distill.md` §5 五重过滤法）：领域相关 → 数据量级可达（别选百万粉对标千粉账号）→ 内容形态匹配 → 阶段可学（早期账号学成长期打法，别学成熟期）→ 拆得开（拿得到稿子）。

## Overview

```
[Phase 0: 检查 benchmark 状态]
  ↓
[Phase 1: 选 input 方式（script 来源 × 数据来源，两维度独立）]
  ↓
[Phase 2: 收集材料（逐条）]
  ↓
[Phase 3: 询问每条样本的"印象判断"（高/中/低 + 为什么）]
  ↓
[Phase 4: AI 拆 pattern + 派生 rubric 信号（仅定性）]
  ↓
[Phase 5: 用户 review → 改 → 确认]
  ↓
[Phase 6: 落盘 benchmark.md / study/ / script_patterns.md / rubric_notes.md]
  ↓
[Phase 7: 更新 state]
```

## Constants

- **MIN_SAMPLES = 3**（少于拆不出 pattern，拒绝继续）
- **RECOMMENDED_SAMPLES = 5-10** / **MAX_PER_RUN = 15**

## Workflow

### Phase 0: 检查 benchmark 状态

读 state 的 benchmark_status：none/pending → 继续；imported → 询问"已有 benchmark [名] N 条。a) 追加 b) 替换（旧的归档 benchmark.archived/）c) 只看不改"。`--append` / `--replace <name>` 直接走。

**轨道标注**：对标可标 `— track: <id>`（该对标主要服务哪轨）；不标则 pattern 写入通用段。

### Phase 1: 选 input 方式（两个独立维度）

**1a. script 怎么拿？**
- a) **粘文本（默认推荐）**——自己整理或用文案提取工具（各平台小程序/字幕导出/yt-dlp 字幕）
- b) **whisper 转录视频文件**——视频放 `study/<账号名>/<video>/source.mp4`，走 `adapters/script-extraction/`（准确度比 a 差：错字/漏字/标点不准）
- c) **跳过 script，只用元数据 + 印象**——pattern 拆不深但 rubric 信号还行，适合"先快速搭起来将来补"

**1b. 数据怎么拿？**
- a) **手填数字**（最简单：查后台或视频页面报数）
- b) **adapter 自动抓**（如已配置 perf-data adapter：给 URL 自动抓数据 + top 评论）

**推荐组合**：零依赖 = 1a+1a（5 分钟）；评论优先 = 1a+1b。

### Phase 2: 收集材料

逐条收集，每条最少 (script 或 transcript 或 N/A) + 数据（播放/点赞/评论/转发）。能再粘 top 5-10 评论（带赞数）更好——pattern 能挖到模因层。达到 MAX 或用户说"够了"进 Phase 3。

### Phase 3: 询问"印象判断"

每条收完数据后**追加问**：

```
看完这条的印象，算这个账号的：
  a) 高表现样本（代表作/你想做成这样）
  b) 中表现样本（普通水准）
  c) 低表现样本（不想做成这样）
为什么？（一句话——这个判断比数据更能告诉我你想做什么风格）
```

> 印象**可以**和数据冲突（数据高但用户觉得"不算代表作"）——冲突本身是有用信号，记录下来。

### Phase 4: AI 拆 pattern + 派生 rubric 信号

**4a. Script patterns**（按 script_patterns.md cheat sheet 框架）：开头钩子类型分布 / 主体结构 / 句式句长节奏 / 情绪标记 / 收尾 / 高频词汇。输出 N 个 pattern（每个引用具体样本作证据）。

**4b. Rubric 信号（仅定性，不给数值权重）**：每条样本打分 → 看高表现样本共有哪些维度高、低表现共有哪些低、哪些维度无差异（不是关键维度）。输出方向性结论（"ER 看起来重要：3/3 高样本 ER≥4"）。

**4c. 声音样本提取（可选）**：用户想学这个账号的表达风格时，额外提取声音特征（句长分布/口头禅/语气词/禁用词）写入 script_patterns.md 的"声音参考"段——供后续 draft 校准语气（消费 dbskill 提炼 §5 显式参数法：把风格写成显式参数而非"风格类似 X"的模糊描述）。

### Phase 5: 用户 review

一次性展示：N 个 pattern（各带证据）+ rubric 定性信号 + 选题方向感（主题分布/调性）+ **不直接给数值权重**（5-10 样本拟合容易过拟合，只作 tier-2 信号）。🔴 **CHECKPOINT**：用户 ok 落盘 / 挑刺改到确认——展示前不写任何文件。

### Phase 6: 落盘

1. **benchmark.md**（项目根）：账号信息 + 样本表 + 定性 rubric 派生 + 选题方向感。append → 追加样本行重拆 pattern 不重写全文；replace → 旧的归档
2. **study/<账号名>/<video-id>/**：每条样本子目录（source.mp4 如有 / transcript.md / meta.md——transcript 持久化是 retro diff 的依据，不能只在内存拆）
3. **script_patterns.md** 加"对标 [账号名] 借鉴"段——pattern 标 **Imported, untested**（实拍验证 ≥2 次复盘确认有效才去掉标记升正式）
4. **rubric_notes.md** 加 "benchmark-derived initial signals" 段（仅定性 + "等你自己 N≥5 后正式 bump 时再决定是否调权重"）

### Phase 7: 更新 state

`benchmark_status: imported` + `benchmark_name` + `benchmark_sample_count`。

## Key Rules

1. **必须问印象**——纯看 transcript 拆 pattern 抓表面，加印象才挖到深层
2. **Rubric 信号仅定性**——不直接给数值权重
3. **pattern 默认标 untested**——不污染用户自己的 pattern 库
4. **不直接抓视频**——下载是用户的事（TOS + 反爬）
5. **MIN_SAMPLES = 3** 硬门槛
6. **可重复跑**——append / replace

## Refusals

- 「跳过印象判断直接拆」 → 拒绝。印象是关键 input
- 「我只能给 1 条样本」 → 拒绝。最少 3 条
- 「直接给我数值权重」 → 拒绝。仅定性信号
- 「不写 transcript 文件，内存里拆就行」 → 拒绝。持久化是后续 diff 依据
- 「帮我下载对标视频」 → 拒绝。引导用户自己下

## Integration

- 上游：oracle-init 结束时强烈建议 cold-start 用户跑；status 在 pending + 距 init >24h 持续提醒
- 下游：oracle-seed 读 benchmark.md 知道对标方向；script_patterns 供 draft 选结构；rubric signals 供 bump 参考
- 淡出时机（Claude 判断）：该轨样本 ≥10 默认淡出；更早 = 出现 ≥3 条与 benchmark pattern 不一致的强样本；更晚 = 用户样本都很相似。淡出后 signals 段标 `superseded by user data`，benchmark.md 保留作 sanity check
- 与 oracle-apprentice 分工：learn-from = 账号级统计信号（什么类型数据好），apprentice = 单条稿手艺（这条的钩子怎么埋）。同一博主先 apprentice 学写法再 learn-from 导数据，不要混着一次做两个
