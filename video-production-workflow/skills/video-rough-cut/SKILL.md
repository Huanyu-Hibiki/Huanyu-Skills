---
name: video-rough-cut
description: 核心 A-roll 粗剪管线。默认使用 faster-whisper（备选 openai-whisper）做词级转录，结合终稿和分镜用 FFmpeg 进行保守粗剪，输出 EDL、粗剪预览、转录缓存和粗剪交接文件。触发词：粗剪、转录、剪口播、按文稿剪视频。
argument-hint: "[project-path] [--engine faster-whisper|whisper] [--output jianying|filmora|render]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep, Skill
---

# /video-rough-cut

## 定位

这是核心编辑阶段，主要处理 A-roll 和结构性剪辑。它可以读取 B-roll 需求，但不在没有 B-roll 分析和用户确认的情况下批量生成 B-roll。

## 输入

- `Raw\` 下的实拍、OBS 或采访原片；
- `video scripts/manuscript.md`；
- `video scripts/storyboard.json`；
- 已存在的转录缓存；
- 用户确认的粗剪策略、画幅和输出方式。

## 流程

1. 检查虚拟环境、`ffmpeg`、`ffprobe`、faster-whisper/Whisper 及模型（`uv run python scripts/setup/download_models.py --list`）。
2. 对每个源文件执行 `ffprobe`，把时长、尺寸、帧率写入 inventory。
3. 读取已有缓存；源文件未变化时禁止重复转录。有项目词典（`video scripts/lexicon.md`）时传 `--lexicon` 做专名偏置。
4. 默认使用 faster-whisper 输出**词级、verbatim** transcript（备选 `--engine whisper`）；不能只生成 phrase/SRT。
5. **文稿自动校对（默认必跑）**：运行 `align_to_manuscript.py`，把文稿作为文本真相源对齐词级时间戳——字幕直接采用文稿拼写（ASR 错字/同音词自动消失），ASR↔文稿偏差、低置信句和口癖候选落盘待复核，产出 `Sub/caption_corrected.srt`、`alignment_report.json`、`speech_errors.json`。
6. 打包为 `Rough/takes_packed.md`，供编辑判断。
7. **Take 挑选（多遍重读必跑）**：运行 `select_takes.py`，找出每句文稿的所有 take 并按匹配度/完整度/停顿/语速打分选最佳，产出 `takes_decision.md` 给用户过目；未匹配句子必须逐条确认（没读 or ASR 太差）。用户裁决有歧义的 take（补读/改文稿/保留最长）后，把裁决追加进项目根 `decision_log.json`（category=`take_selection`）。
8. **卡顿/重复剪除（默认开启）**：运行 `detect_repeats.py`（输入 `finalKeeps_<stem>.json`），在保留段内检测口播不流畅——**词级结巴**（"我们我们来看"，同词连读）和**前缀废弃**（说一半停住重说完整："我觉得这个 → 我觉得这个方案"）**自动剪除首次尝试**，产出 `keeps_dedup_<source>.json`；**非前缀的相似重说**（"非常实用/非常好用"——与排比句文本上无法区分）和**长间隔整句重读**（>2s，select_takes 领域）只进 `repeats_report.md` 待确认清单，**不自动剪**，逐条请用户裁决（🔴 句级删除 diff 确认；确认要剪的手工并入 keeps 再重跑）。
9. **停顿收紧（默认开启）**：运行 `tighten_pauses.py`（输入用 `keeps_dedup_<source>.json`），把保留段内 ≥0.35s 的句中停顿收紧到约 0.25s，产出 `keeps_tightened_<source>.json` 和 `pauses_report.md`；⚠️ 配乐/低音量/多人重叠段先关收紧或人工过一遍，能量门禁缺位时宁可保留。
10. 基于 `takes_decision` + `keeps_tightened` 提出 EDL；**EDL 只能使用被选中的 take，重复 take 和被淘汰 take 不得进入草稿**；不在词中间切断。
11. 先做分段提取、音频淡入淡出和无损 concat，再按需要加入覆盖层。
12. 生成粗剪预览和 `rough_cut_manifest.md`、`missing_materials.md`。
13. 自检接缝、音频爆音、字幕预留空间和内容完整性——渲后对**成片**每个切点 ±1.5s 窗口抽帧+抽波形核对（视觉跳变/爆音/字幕被遮），不拿源素材当检查对象。

## 执行脚本

脚本统一位于 `<合集根>/scripts/video-rough-cut/`：

```bash
# 单个视频：faster-whisper 词级转录（默认引擎，Windows 友好），结果缓存到 Rough/transcripts/
# 备选引擎：--engine whisper（openai-whisper，需 uv sync --extra whisper）
# 有项目词典时传 --lexicon：专名表作为 initial-prompt 偏置，显著降低专名错字
uv run --project "<合集根>" python "<合集根>/scripts/video-rough-cut/transcribe.py" \
  "<项目>/Raw/实拍.mp4" --edit-dir "<项目>/Rough" \
  --lexicon "<项目>/video scripts/lexicon.md"

# 多个原片并行转录
uv run --project "<合集根>" python "<合集根>/scripts/video-rough-cut/transcribe_batch.py" \
  "<项目>/Raw" --edit-dir "<项目>/Rough" --workers 4 --language zh

# 转成字幕校对阶段兼容的词级格式
uv run --project "<合集根>" python "<合集根>/scripts/video-rough-cut/whisper_to_subtitles_words.py" \
  "<项目>/Rough/transcripts/实拍.json" "<项目>/Rough/transcripts/subtitles_words.json"

# 文稿对齐 + 自动校对（转录后默认必跑）：字幕采用文稿拼写，ASR↔文稿偏差、
# 口癖候选、低置信句落盘待复核；产出 Sub/caption_corrected.srt + alignment_report.json
uv run --project "<合集根>" python "<合集根>/scripts/video-rough-cut/align_to_manuscript.py" \
  "<项目>" "<项目>/Rough/transcripts/subtitles_words.json" "<项目>/Rough/analysis"

# Take 挑选：找出每句的所有 take，打分选最佳（多遍重读的场景必跑）
uv run --project "<合集根>" python "<合集根>/scripts/video-rough-cut/select_takes.py" \
  "<项目>" "<项目>/Rough/transcripts/subtitles_words.json" --output-dir "<项目>/Rough"
# 输出：takes_decision.json / takes_decision.md（给用户过目）/ finalKeeps_<stem>.json

# 卡顿/重复剪除（take 挑选后默认必跑）：词级结巴与前缀废弃自动剪首次尝试，
# 相似重说/整句重读只进 repeats_report.md 待确认；产出 keeps_dedup_<stem>.json
uv run --project "<合集根>" python "<合集根>/scripts/video-rough-cut/detect_repeats.py" \
  "<项目>/Rough/transcripts/subtitles_words.json" \
  --keeps "<项目>/Rough/finalKeeps_<stem>.json" --output-dir "<项目>/Rough"

# 停顿收紧：输入用剪除重复后的 keeps_dedup；保留段内 ≥0.35s 停顿收紧到 ~0.25s
uv run --project "<合集根>" python "<合集根>/scripts/video-rough-cut/tighten_pauses.py" \
  "<项目>/Rough/transcripts/subtitles_words.json" \
  --keeps "<项目>/Rough/keeps_dedup_<stem>.json" --output-dir "<项目>/Rough" \
  --source-media "<项目>/Raw/实拍.mp4"

# 按 EDL 渲染，字幕在 filter chain 最后应用
uv run --project "<合集根>" python "<合集根>/scripts/video-rough-cut/render.py" \
  "<项目>/Rough/edl.json" -o "<项目>/Rough/preview.mp4" --preview
```

其他入口：`pack_transcripts.py`（打包转录）、`timeline_view.py`（时间线检查）、`grade.py`（调色）、`generate_filmora_project.py`（Filmora 工程）、`funasr_srt.py`（legacy Fun-ASR SRT，需 `uv sync --extra funasr`）。

## 硬规则

- **转录后先自动文稿校对，再做剪辑决策**：`align_to_manuscript.py` 是流程第 5 步，不是可选项；字幕文本以文稿为准，ASR 偏差只记录不静默改音频；
- 不截断文稿驱动视频中对应的完整解释；有歧义时保守保留；
- **重复 take 不进草稿**：EDL 只能引用 `takes_decision` 选中的 take；被淘汰 take、口误半句和 false start 一律不进时间线；
- **卡顿重复只自动剪两类**：词级结巴（同词连读）和前缀废弃（后文以首次尝试为真前缀且有停顿）；相似重说与排比句文本上无法区分，**只列待确认不自动剪**——宁可留一处结巴给用户裁决，不冒险剪掉排比；
- 字幕不受重复剪除影响：caption_corrected.srt 以文稿拼写为准，文稿本来就没有结巴；音频剪除后字幕时间码由 keeps 链路统一对齐；
- **句中停顿默认收紧**：≥0.35s 的停顿保留约 0.25s 呼吸后剪除；用户明确要求保留呼吸节奏时才跳过 `tighten_pauses`；配乐段、低音量段、多人重叠段先人工确认再收紧（无能量门禁，宁可保留）；
- 每个切点落在词边界，优先吸附到静音；
- 每个切点约 30-200ms 音频 fade；
- 不把原始 `Raw\` 文件作为输出覆盖；
- 字幕在粗剪之后再校准，不能先在原始时间线烧字幕再剪；
- 有多个动效任务时并行处理，不串行等待；
- 策略未确认时不修改剪辑。

EDL 中的 `sources`、`subtitles` 和 overlay 路径可以使用绝对路径；相对路径先相对于 `Rough/edl.json` 所在目录解析，找不到时再相对于项目根解析。这样既兼容 `Raw/...` 项目路径，也兼容 `../Raw/...` 的 EDL 写法。

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 转录失败 / ASR 输出为空 | 检查音轨是否存在（`ffprobe` 看 audio stream）、语言参数是否正确，换引擎（faster-whisper ↔ whisper）重跑 | 🔴 该源文件标记 blocked 记入 `missing_materials.md`，继续处理其他源，不中断整期 |
| 文稿缺失 / `align_to_manuscript` 退出非 0 | 检查 `video scripts/manuscript.md` 是否存在；无文稿时跳过自动校对，在 manifest 标注「字幕未校对」 | 🔴 无文稿不伪造校对字幕——向用户要文稿或路由 `/video-caption-correct` 人工路径 |
| 源文件 hash 变了但转录缓存仍在 | 缓存失效属正常——重新转录该源 | 禁止手工改缓存时间戳凑合用 |
| `select_takes` 大量句子未匹配（>20%） | 先查文稿与口播是否严重偏离（口播自由发挥）；再降低 `--min-match` 到 0.5 重跑 | 🔴 列出未匹配句让用户裁决「补读 / 改文稿 / 保留最长 take」，不自动猜 |
| `detect_repeats` 待确认清单过长（>20 处）或出现误报 | 检查口播是否大量排比/刻意重复（提高 `--review-sim` 或跳过本步）；误报样本核对 `repeats_report.md` 后调阈值 | 🔴 相似重说逐条让用户勾选「剪/留」，勾选结果记 `decision_log`（take_selection）；不批量猜剪 |
| 重复剪除后句子缺尾（前缀判断吃掉过多） | 核对 `repeats_report.md` 的 cut/keep 文本，调小窗口（阈值见脚本头注释）后重跑 | 该处从 keeps_dedup 回退为 finalKeeps 对应段，宁可保留结巴 |
| 选中的 take 与文稿顺序冲突（口播顺序≠文稿顺序） | 按实际口播顺序重排 EDL，并在 manifest 记录顺序差异 | 文稿标记 superseded，提示用户确认最终顺序 |
| `tighten_pauses` 切点出现爆音 | 该切点前后各加 30ms 音频 fade；渲染层已默认 bake，检查是否被跳过 | 把该处停顿从收紧列表移除（保留原停顿），宁松勿爆 |
| 渲染时 `edl.json` 引用的源缺失 | `resolve_path` 已尝试三种基准；检查文件是否被移动 | 🔴 停止渲染，报告缺失段，不跳过该段继续（会静默丢内容） |
| 预览与预期时长偏差 >5% | 检查 EDL 段是否有重叠/遗漏、变速参数是否误设 | 用 `timeline_view.py` 逐段核对 |
| GPU 不可用导致转录极慢 | faster-whisper 自动降为 CPU int8（无需干预）；或分段并行 | 告知用户预计耗时，由用户决定等或换机 |

## 输出

```text
Rough/
├── transcripts/<source>.json
├── analysis/
│   ├── analysis.txt                  # 文稿校正后的分句文本
│   ├── sentence_map.json             # 句→词级 idx 区间
│   ├── auto_selected.json            # 静音 gap idx
│   ├── speech_errors.json            # 口癖删除候选（advisory，待人工确认）
│   └── alignment_report.json         # 对齐置信度 + 来源状态 + ASR↔文稿偏差清单
├── takes_packed.md
├── takes_decision.json / takes_decision.md
├── finalKeeps_<source>.json
├── keeps_dedup_<source>.json          # 剪除卡顿重复后的保留段（detect_repeats）
├── repeats_report.json / .md          # 自动剪除清单 + 待人工确认清单
├── keeps_tightened_<source>.json
├── pauses_report.md
├── edl.json
├── rough_cut_manifest.md
├── missing_materials.md
└── preview.mp4
Sub/
└── caption_corrected.srt             # 文稿拼写 + 粗剪（原始录制）时间线；拆条由剪映 Draft 阶段负责
```

`alignment_report.json` 是校对复核的唯一分流依据：`provenance_counts` 与 `low_confidence_sentences` 判断是否需要人工复核（路由 `/video-caption-correct`），`asr_substitutions` 是错字/专名偏差候选（新错词确认后写入 `video scripts/lexicon.md`，下期生效）。

完成后把 `rough_cut_manifest.md` 和 `missing_materials.md` 交给 `video-plan --mode rough-cut-finalization`，再进入 B-roll 和动效执行规划。
