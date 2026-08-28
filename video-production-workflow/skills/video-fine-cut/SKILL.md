---
name: video-fine-cut
description: 剪映内部精剪阶段。基于剪映 Draft、校对字幕和已准备素材，剪掉气口与多余片段，调整节奏、字幕、音乐和音效，最终导出精剪视频与时间轴正确的 master.srt。触发词：剪映内部剪辑、剪掉气口、精剪、导出最终字幕。
argument-hint: "[project-path] [--editor jianying|filmora]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep
---

# /video-fine-cut

## 定位

这是用户在剪映或 Filmora 中完成的人工精剪阶段，位于 Draft 生成之后、B-roll 策划之前。它把“粗剪可用”变成“主叙事时间线稳定”，并产出 B-roll Finder 唯一应该读取的精剪 SRT。

## 输入

- `Jianying-draft/` 或 Filmora 工程；
- `Sub/caption_corrected.srt`；
- 已通过 `video-assets` 的音乐、音效和基础素材；
- `Rough/rough_cut_manifest.md`；
- 用户对节奏、气口、删减和保留内容的要求。

## 用户操作

1. 打开 Draft，确认 A-roll 片段顺序和完整表达；
2. 粗剪阶段已完成 take 挑选和停顿收紧：这里只处理残余的气口、节奏不顺和多余尾巴，不应再出现成遍的重复 take（若出现，回到 `/video-rough-cut` 重跑而不是手工删）；
3. 保留完整的操作解释、关键结论和必要反应；
4. 调整字幕样式、分行、音乐、音效和基础包装；
5. 暂不批量加入未经 B-roll Finder 分析的 B-roll；
6. 导出精剪预览和当前时间轴的 SRT。

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| 剪映草稿打不开或时间线损坏 | 用 `Rough/edl.json` + `Rough/.jianying_cache/` 重建 Draft（重走 `video-jianying-draft` 命令序列） | 🔴 重建会丢失已精剪的手工改动——先向用户确认「重剪一遍」还是「只修字幕」，不允许静默重建 |
| `master.srt` 与 `fine_cut.mp4` 时长差 > 0.5s | 字幕沿用了原始时间线；在剪映中重新导出当前时间轴的 SRT | 用 `video-rough-cut` 的 `align_to_manuscript.py --final-keeps` 按 EDL 重映射，映射不确定处标记人工核对 |
| 剪映导不出 SRT 或导出为空 | 在精剪时间线上用剪映「识别字幕」重建，再对照 `caption_corrected.srt` 校对文字 | 以词级 transcript + EDL 手工拼出 master.srt，逐句核对时间码 |
| 音频切点有爆音 | 检查切点是否落在词中间；回退到最近的词边界或静音 | 该切点前后各加 30ms 音频 fade 重导出 |
| 发现成遍重复 take / 大段死停顿 | 说明粗剪跳过了 take 挑选——回 `/video-rough-cut` 跑 `select_takes.py` + `tighten_pauses.py` 重建 EDL | 不在精剪阶段手工逐个删（耗时且不可追溯） |

## 输出

```text
Polished/fine_cut.mp4
Sub/master.srt
Rough/fine_cut_manifest.md
```

`master.srt` 必须来自精剪后的时间线，不能从原始录制字幕直接复制。时间线发生变化后，必须重新导出或重新映射 SRT。

## 完成检查

- 视频与 `master.srt` 时长一致；
- 字幕没有沿用原始时间线偏移；
- 没有把关键口播或 OBS 操作解释剪断；
- 音频切点没有爆音；
- 画面已经足够清楚的段落不强行添加 B-roll；
- 已写入 `fine_cut_manifest.md`，可以交给 `/b-roll-finder`。

🔴 **CHECKPOINT：完成检查全部通过后，向用户展示 fine_cut 与 master.srt 的核对结果，用户确认「精剪完成」才路由到 `/b-roll-finder`。**

## 禁止

- 不手改剪映打开中的草稿 JSON（可能已加密）；
- 不用原始录制时间轴的 SRT 顶替 `master.srt`；
- 不在本阶段手工删除成遍重复 take 和大段停顿（回粗剪重跑脚本，可追溯）；
- 不剪断关键口播、OBS 操作解释和必要反应；
- 不批量添加未经 `/b-roll-finder` 分析的 B-roll；
- 精剪未过完成检查前，不把状态标为 `completed`。

## 执行说明

本阶段是剪映/Filmora 中的人工精剪操作，不由脚本代替编辑决策。脚本支持在精剪后继续进行 FFmpeg 合成和 QA：

```bash
uv run --project "<合集根>" python "<合集根>/scripts/video-polish/compose_broll.py" \
  "<项目>/Polished/fine_cut.mp4" \
  "<项目>/Polished/broll-compose.json" \
  --output "<项目>/Polished/preview.mp4"
```
