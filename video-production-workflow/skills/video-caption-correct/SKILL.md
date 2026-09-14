---
name: video-caption-correct
description: 字幕校对复核闸门（条件触发）。粗剪阶段已按文稿自动校对字幕；本阶段只在 alignment_report 出现低置信句/大量偏差或用户主动要求时介入，做词级人工确认、口癖裁决和词典沉淀。触发词：字幕校对、修字幕、根据原稿纠错、识别口误。
argument-hint: "[project-path] [caption-path]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep
---

# /video-caption-correct

## 定位

**复核闸门，不是必经阶段。** `/video-rough-cut` 的第 5 步已经自动完成"按文稿校对"：`align_to_manuscript.py` 以文稿为文本真相源产出 `Sub/caption_corrected.srt`，并把 ASR↔文稿偏差、口癖候选、低置信句写入 `Rough/analysis/`。本阶段只在两种情况介入：

1. `alignment_report.json` 的 `low_confidence_sentences` / `asr_substitutions` / `unmatched_sentences` 超过用户容忍度（经验阈值：低置信句 >10% 或未匹配句 >5 句）；
2. 用户主动要求逐句过字幕。

机器负责"文稿写得对的全部字幕"，人只裁决"机器拿不准的少数派"。

## 输入

- `Rough/transcripts/*.json`（粗剪词级转录，**唯一转录来源**——本阶段不重新转录）；
- `Rough/analysis/alignment_report.json`、`speech_errors.json`、`sentence_map.json`（粗剪自动校对产物）；
- `video scripts/manuscript.md` 终稿；
- `video scripts/lexicon.md` 个人词典（如有）。

## 流程

1. 读 `alignment_report.json`：按 `source` 状态分流——`manuscript_aligned` 句自动通过；`low_confidence` 句和 `asr_substitutions` 是人工队列；`unmatched_sentences` 逐条问用户（没读 or ASR 太差）。
2. 读取词级 transcript，保留 start/end 和原始文字。
3. 按"只改词，不先断行"的原则修正机器拿不准的部分：错别字、专有名词、ASR 同音词和稿件差异。
4. 裁决 `speech_errors.json` 的口癖候选（`delete_idx`）：规则脚本保守识别人工确认取并集；**音频删除是剪辑决策**——确认要删的口误回写剪辑决策（EDL/精剪），字幕文本不同步删除。
5. 复核 `Sub/caption_corrected.srt` 与粗剪时间线对应（不是原始录制时间线）；改动后落 `caption_corrected-v2.srt`，不覆盖已确认版本。
6. **词典沉淀**：本阶段确认的错字/专名（含 `lexicon_rule` 命中项）→ 用户确认后 append 到 `video scripts/lexicon.md`（同 oracle-voice voice-lexicon 格式，专名表 + 纠错规则），下期转录自动生效。

🔴 **CHECKPOINT：涉及整句删除或时间轴改动的修正，先列出 diff 清单（原句→改后、影响的时间码）等用户逐条确认；词级错别字修正可直接批量执行。**

## 两个输出概念

| 输出 | 用途 |
|---|---|
| `caption_corrected.srt`（或 -vN） | 粗剪阶段交给剪映或 Draft 的校对字幕；单条建议 ≤32 字（句子级），更短的拆条由剪映 Draft 阶段的 `subtitle_split.py` 负责 |
| `master.srt` | 剪映内部精剪完成后重新导出的最终时间轴字幕，由后续阶段生成；`align_to_manuscript.py --final-keeps` 仅在精剪导不出 SRT 时作为重映射兜底 |

## 口误规则

- `delete_sentences` 和 `delete_idx` 分开记录；
- 脚本自动识别的口癖与人工判断取并集，不能互相覆盖；
- 不为"可能更顺"删除有效信息；
- 如果删除会造成字幕和口播不同步，优先回到剪辑决策，而不是只改字幕；
- 纠错和断行分两步，不要混成一次不可审计的重写。

## 语义分页与标点（拆条/断行时遵守）

拆条（`subtitle_split.py` / 剪映导入前）按语义断行，不按固定宽度机械切：

- **按语义完整 thought 分页**：断点优先落在标点/语气停顿处；一个完整意思尽量在一页内，避免把主谓/数字与单位/品牌与型号撕开；
- **禁止按固定字符数硬切**：固定宽度代码点切分必然在词中间断开；
- **标点显示规则**：页内标点保留；页尾可省略的分离符（逗号/句号/分号/冒号/顿号）按风格省略，但**页尾问号/叹号必须保留**；成对结构符（引号/括号）后闭合符必须保留；数字/型号/单位中的点号永不删；
- 改动分页后重查最长两行卡与字幕安全区；放大字号后必须重新断行，不是只改 size；
- 中文显示宽度按汉字 1、ASCII 0.5 计（`subtitle_split.py` 的默认口径）；
- **字幕标点策略由风格档声明**（`video scripts/style-profile.md`）：默认保留句读（本节规则即默认档）；风格档选了"极简无标点"档时，拆条时剥离全部句读（数字/型号间半角点号除外），长句停顿靠拆条不靠标点；
- **画面文字不照抄字幕**：画面上的文字（标题卡/花字/关键词强调）是 ≤12 字的提炼，与跟读字幕整句重复 = 同一信息出现两份；复核时发现画面文字与字幕逐字相同要标出，路由回 `/video-plan` 或装配阶段改提炼；
- 跟读字幕本体零动效（整句硬现）；关键词弹出类动效全片 ≤3 次，且只在风格档允许时使用。

## 格式化前置检查（机械可判，与纠错解耦）

词典沉淀管"字对不对"，下面这些数值管"观感稳不稳"——复核时逐条机械核对，不合格直接改，不需要问：

| 项 | 标准 |
|---|---|
| 单条显示时长 | ≥ max(1.0s, 字数 ÷ 5) 秒；阅读速度 >7 字/秒的条目拆条 |
| cue 尾延后 | 相对语音结束延后约 200ms，避免字幕闪没 |
| 行长 | 拆条后单行 ≤18 显示单位（`subtitle_split.py` 已管，复核时查 `.split.srt`） |
| 安全区 | 字幕带只进画面下带（1080p 基准 y≥900）；竖屏常驻件靠左下（右缘是点赞栏） |
| 画面文字去重 | 画面文字（标题卡/花字）≤12 字提炼，与跟读字幕逐字重复 = 记录并路由回规划/装配改提炼 |

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 粗剪没跑自动校对（`Rough/analysis/` 不存在） | 路由回 `/video-rough-cut` 补跑第 5 步，不在本阶段从零转录 | 🔴 不重新转录——转录缓存和校对产物都归粗剪所有 |
| ASR 与文稿差异过大（大量句无法对齐） | 先查音轨是否选对、语言设置是否正确，路由回粗剪重跑转录 | 🔴 差异仍大时列出未匹配句让用户人工裁决，不批量猜改 |
| 字幕时间轴对不上粗剪时间线 | 确认输入是粗剪后重映射的 transcript，不是原始录制 | 用 `align_to_manuscript.py --final-keeps` 重映射后再校对 |
| 删除口误会造成字幕与口播不同步 | 不删字幕文本，回到剪辑决策处理音轨 | 把该句记入 `speech_errors.json` 的 `needs_edit_decision`，留给精剪 |
| 专有名词反复被 ASR 写错 | 写入 `video scripts/lexicon.md` 专名表 + 纠错规则，下期 `transcribe.py --lexicon` 自动偏置 | 同期先在复核中逐处修正；词典供下期根治 |

## 反例清单（不要做）

- 不在本阶段重新转录 Raw 素材（转录唯一入口是 `/video-rough-cut`）；
- 不为「可能更顺」重写或删除有效口播内容；
- 不把纠错和断行混成一次不可审计的重写；
- 不用「听起来更好」的新句子替换用户文稿原句；
- 不批量猜测 ASR 大段无法对齐的区域——列出来让用户裁决；
- 不静默删除口误对应的音轨时间——那是剪辑决策，不是字幕决策；
- 不在原始录制时间轴上校对（必须是粗剪后时间线）。

## 执行脚本

脚本统一位于 `<合集根>/scripts/video-caption-correct/`（本阶段只剩审核/复核工具链）：

```bash
# 首次环境检查
node "<合集根>/scripts/video-caption-correct/doctor.js"

# 词级详情/纯文本提取（复核辅助）
node "<合集根>/scripts/video-caption-correct/extract_text.js" \
  "<项目>/Rough/transcripts/subtitles_words.json" "<项目>/Rough/analysis"
node "<合集根>/scripts/video-caption-correct/gen_word_detail.js" \
  "<项目>/Rough/analysis/sentence_map.json" \
  "<项目>/Rough/transcripts/subtitles_words.json" <句号...>

# 人工审核页（可选：低置信句较多时启用）
node "<合集根>/scripts/video-caption-correct/generate_review.js" \
  "<项目>/Rough/transcripts/subtitles_words.json" \
  "<项目>/Rough/analysis/auto_selected.json" \
  "<项目>/Rough/caption-work/audio.mp3" \
  "<项目>/Rough/review"
bash "<合集根>/scripts/video-caption-correct/serve_review.sh" "<项目>/Rough/review"
```

`run_transcribe.ps1/.sh`、`auto_filler.js`、火山云转录（`volcengine_*.sh`）为 **legacy 独立工作流入口**：日常管线不再使用（转录走粗剪，口癖候选由 `align_to_manuscript.py` 自动产出），仅在脱离管线单独处理音频时可用。审核页内嵌的 FCPXML/PRPROJ 导出仅用于脱离本管线的独立剪辑场景——管线内剪辑决策统一走粗剪 EDL → `video-jianying-draft`。

边界算法入口：`lib/compute_keeps.js`、`lib/refine_boundaries.js`（审核页预览用；管线内切割真相源是粗剪 EDL）。
