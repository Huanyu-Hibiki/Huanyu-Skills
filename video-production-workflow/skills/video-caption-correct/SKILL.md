---
name: video-caption-correct
description: 字幕校对与口误处理。根据视频文稿校对 video-rough-cut 输出的初始词级字幕，识别 ASR 错字、专有名词、整句口误、重复和填充词，生成可交给剪映的校对字幕。触发词：字幕校对、修字幕、根据原稿纠错、识别口误。
argument-hint: "[project-path] [caption-path]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep
---

# /video-caption-correct

## 定位

在粗剪时间轴上修正文稿识别错误。`video-rough-cut` 负责素材和时间轴，本阶段提供口误、填充词和审核方法；不重新决定完整粗剪策略。

## 流程

1. 读取粗剪输出和原稿，确认字幕对应的是粗剪时间线，不是原始录制时间线。
2. 读取词级 transcript，保留 start/end 和原始文字。
3. 按“只改词，不先断行”的原则修正：错别字、专有名词、ASR 同音词和稿件差异。
4. 识别整句重复、残句、明显卡顿和重说；过删风险高于漏删时，保持保守。
5. 使用脚本识别安全填充词；AI 只处理需要上下文判断的词级问题。
6. 输出校对文本、`speech_errors.json`、不确定清单和 `Sub/caption_corrected.srt`。
7. 把用户无法确认的词标记出来，不擅自“修成听起来更好”的新句子。

🔴 **CHECKPOINT：涉及整句删除或时间轴改动的修正，先列出 diff 清单（原句→改后、影响的时间码）等用户逐条确认；词级错别字修正可直接批量执行。**

## 两个输出概念

| 输出 | 用途 |
|---|---|
| `caption_corrected.srt` | 粗剪阶段交给剪映或 Draft 的校对字幕；单条建议 ≤32 字（句子级），更短的拆条由剪映 Draft 阶段的 `subtitle_split.py` 负责 |
| `master.srt` | 剪映内部精剪完成后重新导出的最终时间轴字幕，由后续阶段生成 |

## 口误规则

- `delete_sentences` 和 `delete_idx` 分开记录；
- 脚本自动识别的口癖与人工判断取并集，不能互相覆盖；
- 不为“可能更顺”删除有效信息；
- 如果删除会造成字幕和口播不同步，优先回到剪辑决策，而不是只改字幕；
- 纠错和断行分两步，不要混成一次不可审计的重写。

## 语义分页与标点（拆条/断行时遵守）

拆条（`subtitle_split.py` / 剪映导入前）按语义断行，不按固定宽度机械切：

- **按语义完整 thought 分页**：断点优先落在标点/语气停顿处；一个完整意思尽量在一页内，避免把主谓/数字与单位/品牌与型号撕开；
- **禁止按固定字符数硬切**：固定宽度代码点切分必然在词中间断开；
- **标点显示规则**：页内标点保留；页尾可省略的分离符（逗号/句号/分号/冒号/顿号）按风格省略，但**页尾问号/叹号必须保留**；成对结构符（引号/括号）后闭合符必须保留；数字/型号/单位中的点号永不删；
- 改动分页后重查最长两行卡与字幕安全区；放大字号后必须重新断行，不是只改 size；
- 中文显示宽度按汉字 1、ASCII 0.5 计（`subtitle_split.py` 的默认口径）。

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| ASR 与文稿差异过大（大量句无法对齐） | 先查音轨是否选对、语言设置是否正确，重跑转录 | 🔴 差异仍大时列出未匹配句让用户人工裁决，不批量猜改 |
| 字幕时间轴对不上粗剪时间线 | 确认输入是粗剪后重映射的 transcript，不是原始录制 | 用 `align_to_manuscript.py --final-keeps` 重映射后再校对 |
| 删除口误会造成字幕与口播不同步 | 不删字幕文本，回到剪辑决策处理音轨 | 把该句记入 `speech_errors.json` 的 `needs_edit_decision`，留给精剪 |
| 专有名词反复被 ASR 写错 | 建立本项目的替换表（错词→正词）统一替换 | 替换表写入交接 note，供下期复用 |

## 反例清单（不要做）

- 不为「可能更顺」重写或删除有效口播内容；
- 不把纠错和断行混成一次不可审计的重写；
- 不用「听起来更好」的新句子替换用户文稿原句；
- 不批量猜测 ASR 大段无法对齐的区域——列出来让用户裁决；
- 不静默删除口误对应的音轨时间——那是剪辑决策，不是字幕决策；
- 不在原始录制时间轴上校对（必须是粗剪后时间线）。

## 执行脚本

脚本统一位于 `<合集根>/scripts/video-caption-correct/`：

```bash
# 首次环境检查
node "<合集根>/scripts/video-caption-correct/doctor.js"

# 默认使用本地 faster-whisper（备选 whisper），不需要 VOLCENGINE_API_KEY
# Windows 用 PowerShell 原生入口（无需 Git Bash）：
powershell -ExecutionPolicy Bypass -File "<合集根>/scripts/video-caption-correct/run_transcribe.ps1" `
  "<项目>/Raw/实拍.mp4" "<项目>/Rough/caption-work" --local
# macOS / Linux：
bash "<合集根>/scripts/video-caption-correct/run_transcribe.sh" \
  "<项目>/Raw/实拍.mp4" "<项目>/Rough/caption-work" --local

# 只有明确需要云端时才使用火山引擎（可选）
# bash "<合集根>/scripts/video-caption-correct/run_transcribe.sh" \
#   "<项目>/Raw/实拍.mp4" "<项目>/Rough/caption-work" --flash

# 生成句子分析和句号映射
node "<合集根>/scripts/video-caption-correct/gen_analysis.js" \
  "<项目>/Rough/caption-work/1_转录/subtitles_words.json" \
  "<项目>/Rough/caption-work/2_分析"

# 自动填充词识别，保留已有人工选择
node "<合集根>/scripts/video-caption-correct/auto_filler.js" \
  "<项目>/Rough/caption-work/2_分析/sentence_map.json" \
  "<项目>/Rough/caption-work/1_转录/subtitles_words.json" \
  "<项目>/Rough/caption-work/2_分析/speech_errors.json"

# 合并整句、词级和静音选择
node "<合集根>/scripts/video-caption-correct/merge_selections.js" \
  "<项目>/Rough/caption-work/2_分析/sentence_map.json" \
  "<项目>/Rough/caption-work/2_分析/speech_errors.json" \
  "<项目>/Rough/caption-work/2_分析/auto_selected.json"
```

审核页相关入口：`generate_review.js`、`serve_review.sh`、`review_server.js`。边界算法入口：`lib/compute_keeps.js`、`lib/refine_boundaries.js`；这些脚本均位于当前 `video-caption-correct` 目录，不再依赖备份 Skill。
