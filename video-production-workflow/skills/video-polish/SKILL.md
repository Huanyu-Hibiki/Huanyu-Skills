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
2. **装配清单来源（三选一，都不许跳过确认闸）**：a) `/b-roll-finder` 的素材落位匹配产出 `Polished/broll-compose.draft.json`——展示 `match_report.md` 匹配表，用户逐条确认后转正为 `broll-compose.json`（semantic_pool 条目此刻完成语义配对）；b) 用户/Agent 手写的 `broll-compose.json`——按既有流程展示核对；c) **用户选择剪映路线**：转正后的 `broll-compose.json` 交给 `/video-jianying-draft load_beats` 灌进装配草稿（fine_cut 底片 + B-roll 轨，见其 SKILL「B-roll 装配草稿」节），由剪映微调后导出——此路线下本 skill 的 FFmpeg 合成跳过，QA 以剪映导出成片后补跑（`final_probe.py` + 人工核对）；
3. **交付承诺核对（装配前必跑）**：运行 `check_delivery_promise.py`——已批准条目文件缺失 = fail 禁止装配（回 `/b-roll-generate` 重做）；静帧兜底导致运动比低于 `delivery_promise` 承诺 = degraded，**必须用户显式批准降级并记入 `decision_log.json`（category=promise_change），不许静默出片**；
4. 按 `master.srt` 和词级锚点定位 B-roll，默认落在关键词后 `0.2-0.5s`；
5. 对全屏 B-roll 使用 cover-crop；透明素材保留 alpha；静态图使用项目确认的静止或微动策略；
6. 处理 B-roll 源音、音效和背景音乐音量，不让辅助音频盖住口播；
7. 字幕放在最终 overlay/filter chain 最后，确保不被 B-roll 遮挡；
8. 输出 `Polished/preview.mp4`，抽取每个 B-roll 中点、入点、出点和接缝检查图；
9. **旁白-画面对齐断言**：运行 `check_cue_alignment.py`——每句字幕 ±1.0s 窗口内必须有画面事件（切点/B-roll 起点），未覆盖句超 15% 时逐句列为 P1 finding（"说到时画面上没东西"）；
10. 修复问题后再输出 `Final/video_final.mp4`；
11. **成片技术探针**：对 `Final/video_final.mp4` 运行 `final_probe.py`（时长核对/音轨/峰值电平/四点抽帧），探针 JSON 存档进 QA 报告；
12. 生成 `Polished/final_timeline_manifest.md` 和 `Final/qa-report.md`；
13. 将 `polish`、`delivery` 标记为 `completed`，等待用户进入发布流程。

## QA 清单

- B-roll 是否在关键词或语义落点后出现；
- 是否出现提前切入、接缝闪白、人物碎片或错误画面；
- 镜头边界有转场处置（禁裸切）、两侧运动方向连续、退场后无 >0.4s 底床空转（口径见 `b-roll-timing-and-qa.md`）；
- 排版几何九项（贴边/间距倒挂/未吸附/偏居中/标注脱靶/字阶违规/包围盒相交/同组同色/390px 不可读）——见 `layout-geometry.md`；
- 蒙皮一致性：模板/生成画面是否按 `style-profile.md` 换皮，语义色是否被错误换相；
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

### 完备性下限（可判定的最低标准）

QA 报告缺任何一项数据本身记为 finding——机检数字写不死，评审深浅就会各次不一：

- 抽帧 ≥4（10% / 35% / 65% / 90% 四点，`final_probe.py` 自动落盘）；
- 时长与装配目标差 ≤5%；
- 音轨存在 + 峰值电平 max_volume ≤ -0.5dBFS（逼近削波回查混音）；
- 字幕逐条存在性核对（master.srt 条数 = 装配链字幕条数）；
- 交付承诺运动比、cue 对齐未覆盖率两个数字必须出现在 QA 报告里。

### 评审 finding 产出规则（防不可执行意见）

- **每条 finding 必须指到具体对象**：镜号 / B-roll ID / 时间码 / 文件——指不出来的意见是猜测，不收录；
- **P0/P1 必须附修复动作**（改成什么文案、哪个参数、哪个落点）——给不出修复动作的降级为 `investigation`（调查项），不阻塞交付；
- **发现一个 critical 必须扫同类**（同类转场、同类字幕条全查一遍），不只报眼前这一处；
- **每阶段评审轮次 ≤2**，超轮的遗留项记 warning 放行（配合既有"最多 3 轮"上限：3 轮是硬停，第 2 轮后无新增 critical 就不该再开第 3 轮）；
- P2 检验语：**把标题遮住，这条片和上一条还有区别吗**——同质化即记 P2；同时核风格档偏离清单（超 20% 偏离预算或有偏离无理由 = P1）。

### 独立评审与返修纪律

- 最终 QA 通过后，用**全新上下文的独立 subagent** 做终审（制作者对自己的产出有确认偏差，自评不算数）；评审输入：成片、QA 检查图集、B-roll manifest、动效简报（有则附原版参考帧）；
- **评审材料四件套**（缺件 = 评审盲区）：
  1. **评审拼图**：每句 2 帧 + 动效锚点帧，拼 3×4 网格整版浏览 + 原帧目录可放大——逐句抽帧会漏掉只在 1-2s 内成立的短命动效；
  2. **对照帧**：B-roll 生成来源的参考帧（模板原效果/卡 gallery 帧/风格参考）与成片对应镜头并排——评审判"这是同一个设计的实现吗"，保真缺陷不进评审视野就永远查不出来；
  3. **词落点定妆帧表**：每个 B-roll 锚点的锚字 + 应落时刻 + 定妆帧路径（来源：`b-roll-timing-and-qa.md` 的锚点查表）；
  4. **音效可听度机器报告**：评审没有耳朵——逐 cue 在场/掩蔽分级的机检结果（口径见 `b-roll-timing-and-qa.md` 音频规则）；
- **计划 vs 成片核对**：评审材料附 `storyboard.md` 的设计清单与风格档"不做的事"——"设计默默缺席"类缺陷（计划里声明了但成片没有），评审不知道"应该有"就不会报；
- **评审执行纪律**：报告增量落盘（每看完一镜追加一行，结束行"已看 N/N 镜"才算完成，不以子代理完成通知为准）；镜头多时分片评审（每人 ≤7 镜 + 末人管跨段一致性）；3 次派出仍无报告 → 交付物标注"未获独立评审"，**禁止制作者自评后按已评审交付**；
- 评审材料必须覆盖静帧看不见的三类缺陷：短命动效（逐动效锚点 +0.25s 抽帧核"框住/指向目标没有"）、时域抖动/闪烁（连拍三帧对）、计划 vs 成片核对（manifest/简报声明的元素是否真的都在）；
- **状态切换窗入抽帧清单**：人物角标↔满幅、字幕带换位、分屏↔全屏等几何过渡时刻 ±0.5s 强制抽帧——字幕带换位与人物过渡的穿越冲突只藏在这种窗口里；
- **闸先读闸**：机检/QA 报 FAIL 先读判定口径再改画面（确认闸量的是什么、阈值是否够得着）；由输入决定、本片不可修的问题早下结论交用户（如气口太少导致音效可听度门槛数学上不可达），不硬修；
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

# 交付承诺核对（装配前；degraded 需用户批准降级并记决策日志）
uv run --project "<合集根>" python "<合集根>/scripts/video-polish/check_delivery_promise.py" "<项目>"

# 旁白-画面对齐断言（装配后；未覆盖句 >15% 列 P1）
uv run --project "<合集根>" python "<合集根>/scripts/video-polish/check_cue_alignment.py" "<项目>"

# 成片技术探针（Final 输出后；探针 JSON 进 QA 报告）
uv run --project "<合集根>" python "<合集根>/scripts/video-polish/final_probe.py" \
  "<项目>/Final/video_final.mp4" --expect-duration <装配目标时长秒>
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
