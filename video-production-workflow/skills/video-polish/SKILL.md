---
name: video-polish
description: 精剪后 B-roll 装配与最终交付。把剪映精剪视频、master.srt、已通过 QA 的 B-roll、音乐和音效放回时间线，调整位置、样式和声音，输出预览、最终成片和 QA 报告。触发词：合成 B-roll、装配素材、精剪成片、输出最终视频。
argument-hint: "[project-path] [--preview|--final]"
allowed-tools: Bash(*), Read, Write, Edit, Glob, Grep, Skill
---

# /video-polish

## 输入

- `Polished/fine_cut.mp4` 或剪映/Filmora 精剪工程；
- `Sub/master.srt`；
- `Polished/B-roll/*/out/final.*`；
- `assets/audio/music`、`assets/audio/sfx`；
- `broll-manifest.md`；
- 用户确认的装配策略。

## 流程

1. 读取 manifest，确认所有已批准的 B-roll 都存在；
2. 按 `master.srt` 和词级锚点定位 B-roll，默认落在关键词后 `0.2-0.5s`；
3. 对全屏 B-roll 使用 cover-crop；透明素材保留 alpha；静态图使用项目确认的静止或微动策略；
4. 处理 B-roll 源音、音效和背景音乐音量，不让辅助音频盖住口播；
5. 字幕放在最终 overlay/filter chain 最后，确保不被 B-roll 遮挡；
6. 输出 `Polished/preview.mp4`，抽取每个 B-roll 中点、入点、出点和接缝检查图；
7. 修复问题后再输出 `Final/video_final.mp4`；
8. 生成 `Polished/final_timeline_manifest.md` 和 `Final/qa-report.md`；
9. 将 `polish`、`delivery` 标记为 `completed`，等待用户进入发布流程。

## QA 清单

- B-roll 是否在关键词或语义落点后出现；
- 是否出现提前切入、接缝闪白、人物碎片或错误画面；
- 字幕是否完整、可读且位于最上层；
- 音频边界是否有爆音，口播是否清晰；
- 画幅、分辨率、帧率、时长和音轨是否符合交付规格；
- AI 画面是否有假字、Logo、水印、伪 UI 或语义漂移；
- 每条第三方素材是否有许可证记录；
- 新版本是否保留 manifest 中所有用户批准的 B-roll；
- `Final/` 是否只写入用户确认后的版本。

### 缺陷分级（QA 报告与返修都用这套口径）

| 级别 | 定义 | 处置 |
|---|---|---|
| **P0** | 观众必然察觉且伤害理解：事实/文字错误、不可读、声画错位、元素相撞遮正文、标注指错目标 | 必须修复才可交付 |
| **P1** | 违反硬规则或明显走样：错峰残影、词锚落点偏差 >0.3s、整镜头音效缺席、动效明显不符简报 | 必须修复才可交付 |
| **P2** | 质感瑕疵：密度/留白/样式 | 记录不挡验收 |

### 独立评审与返修纪律

- 最终 QA 通过后，用**全新上下文的独立 subagent** 做终审（制作者对自己的产出有确认偏差，自评不算数）；评审输入：成片、QA 检查图集、B-roll manifest、动效简报（有则附原版参考帧）；
- 评审材料必须覆盖静帧看不见的三类缺陷：短命动效（逐动效锚点 +0.25s 抽帧核"框住/指向目标没有"）、时域抖动/闪烁（连拍三帧对）、计划 vs 成片核对（manifest/简报声明的元素是否真的都在）；
- 评审循环**最多 3 轮**：3 轮后仍有未清 P0/P1 就停手，把剩余缺陷清单、每轮修复记录和未修复原因原样交用户定夺，不无限自审自修补收敛；
- 用户批注返修**时间码三段闭环**：修改前抽该帧 → 修改后抽同帧 → 成片再抽同帧，路径写进 QA 报告；复核给量化数字（首次可辨时刻/被吞时刻/像素占比），"看起来好了"不算数。

### 可读性与响度终检

- **手机宽终检**：把成片缩到约 390px 宽（手机上刷到横屏片的实际宽度）复看一遍，每行字幕/卡片文字都要能读；排不下先删次要文案，不缩字号、不留孤字行；桌面全屏预览不是验收标准；
- **响度归一交付**：最终导出统一过 loudnorm，交付前听一遍确认音效相对电平没有变化：

```bash
ffmpeg -i Polished/preview.mp4 -c:v copy -af "loudnorm=I=-15:TP=-1.5:LRA=11" -c:a aac -b:a 192k Final/video_final.mp4
```

### BGM 节拍同步（配了强节奏音乐时）

BGM 卡点装配的完整方法（网格测定、瞬态钉帧、渲后回测 ≤3 帧）见 [references/video-polish/music-beat-sync.md](../../references/video-polish/music-beat-sync.md)。要点：网格验收通过前不定切点；时间线用拍号表达；配 BGM 的片子交付两版——带 BGM 版 + 无 BGM 版（保留口播/SFX），方便用户后期自配音乐。

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| manifest 中已批准 B-roll 的文件缺失 | 该条目暂停装配，路由回 `/b-roll-generate` 重做 | 其余条目正常合成，缺失项在 QA 报告标 ❌ |
| B-roll 时长 ≠ 放置区间 | 以母片设计区间为准，对 B-roll 做变速或补静态帧收尾 | 🔴 需要裁掉内容才能塞进区间时，先问用户 |
| 透明素材在合成后变黑底 | 检查源文件 alpha（`ffprobe` 看 `yuva`），改用 PNG sequence 重合成 | 改用 ProRes 4444 中转再压 WebM |
| 字幕被 B-roll 遮挡 | 确认字幕 filter 在 overlay 之后（chain 最后） | B-roll 缩小/上移避开字幕安全区，不改字幕位置 |
| 口播被音效/音乐盖住 | 先降辅助音轨音量（ducking），再对齐响度 | 🔴 需要重混音时展示分轨方案等用户确认 |

## 输出模式

🔴 **CHECKPOINT：`--final` 输出前必须展示 `--preview` 的 QA 检查图（每个 B-roll 入点/中点/出点/接缝）并得到用户逐条确认；`Final/` 只接收确认后的版本。**

| 模式 | 输出位置 | 说明 |
|---|---|---|
| `--preview` | `Polished/preview.mp4` | 可反复迭代，不代表最终发布 |
| `--final` | `Final/video_final.mp4` | 用户确认后生成，附 QA 报告 |
| 剪映/Filmora 手动 | 工程文件 + 导出文件 | 保存时间线 manifest，确保可追溯 |

## 禁止

- 不在用户确认前写 `Final/`（预览只进 `Polished/`）；
- 不让任何一轮渲染静默丢掉 manifest 中已批准的 B-roll；
- 不让音效/音乐盖过口播；
- 不把字幕放在 B-roll 之下的图层；
- 不用裁掉 B-roll 内容的方式硬塞放置区间（先问用户）；
- 不修改 `Polished/fine_cut.mp4` 和 `Sub/master.srt` 本体；
- 不复用上一期的 QA 结论替代本轮抽帧检查。

## 执行脚本

```bash
uv run --project "<合集根>" python "<合集根>/scripts/video-polish/compose_broll.py" \
  "<项目>/Polished/fine_cut.mp4" \
  "<项目>/Polished/broll-compose.json" \
  --output "<项目>/Polished/preview.mp4" \
  --width 1920 --height 1080 --fps 30
```

`broll-compose.json` 格式：

```json
{
  "beats": [
    {
      "id": "BROLL-001",
      "start": 12.4,
      "end": 16.2,
      "file": "Polished/B-roll/BROLL-001/out/final.mp4"
    }
  ]
}
```

脚本会检查 B-roll 文件存在、时间段不重叠，并使用 FFmpeg 保留基底音频；字幕仍应在最终剪辑链最后应用。

需要静帧、素材起始时间或独立 beat manifest 时，可使用 `render_cutaways.py`：

```bash
uv run --project "<合集根>" python "<合集根>/scripts/video-polish/render_cutaways.py" \
  "<项目>/Polished/fine_cut.mp4" \
  "<项目>/Polished/preview-cutaways.mp4" \
  --beats "<项目>/Polished/broll-compose.json"
```
