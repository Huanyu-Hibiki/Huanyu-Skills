---
name: video-jianying-draft
description: 剪映原生 Draft 生成器。根据 EDL、校对字幕、音频和图片素材创建或更新剪映专业版草稿，直接输出 native draft_content.json 和 assets。触发词：创建剪映草稿、导入剪映、剪映 draft、生成剪映工程。
argument-hint: "[project-path] [--draft-root path]"
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /video-jianying-draft

## 输入

- `Rough/edl.json` 或已确认的 segment list；
- `Sub/caption_corrected.srt`；
- 用户确认的音乐、音效、图片和基础视频；
- 剪映真实草稿根路径。

## 标准命令序列

使用 `<合集根>/scripts/video-jianying-draft/jianying.py`，所有命令使用同一个 cache：

```text
create_draft
  → add_video × N
  → add_subtitle
  → add_audio
  → add_text / add_image / add_effect / add_sticker（按需）
  → save_draft
```

## 规则

- `Rough/.jianying_cache/` 是当前草稿状态唯一载体，命令间不能更换；
- `--output` 用剪映「全局设置→草稿位置」的真实路径；缺省只接受含真草稿子目录的候选探测，探不到报错等显式路径（首次展示结果请用户确认）；
- **字幕断行**：`add_subtitle` 默认把超长字幕条拆成 ≤18 显示单位（汉字 1、ASCII 0.5）的短条——拆分点优先标点、时间轴连续无缝隙，落盘为 `<原名>.split.srt` 供核对；需要原样导入时加 `--no-split`，需要其他长度用 `--max-chars`；
- **同名素材防错链**：不同目录的同名文件（含大小写）自动 `-2` 后缀；同一文件共享素材；
- **重叠音频分道**：同轨音频不可重叠，`add_audio` 默认贪心溢出 `BGM-2` 等新轨（输出 `track` 即实际）；严格模式 `--no-lane-split`；
- **草稿自包含**：`save_draft` 媒体拷进 `assets/` 并改写路径，原素材移动不影响；缺失进 `missing_media`，补齐重存；
- 剪映运行中 `save_draft` 直接拒绝（tasklist 检测），须完全退出；
- 优先在用户第一次打开剪映前完成全量写入；
- 剪映打开后 JSON 可能被加密，禁止直接用 JSON 修改已打开草稿；
- 已有草稿追加字幕优先输出 SRT 让用户在 GUI 导入（先 `subtitle_split.py` 拆条）；
- 不遇到错误就反复 `create_draft` 生成新草稿；
- 每次保存写入 `Rough/jianying_draft_manifest.md`，记录 draft id、cache、输出根和媒体清单。

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| `add_subtitle` 后静帧仍是超长文本框 | 确认没传 `--no-split`；检查 `.split.srt` 是否生成、cue 数是否增加 | 仍不对时用 `subtitle_split.py` 单独跑并人工核对再导入 |
| `save_draft` 输出目录找不到草稿 | `--output` 不是剪映实际草稿根——从「全局设置→草稿位置」复制真实路径 | 🔴 不猜路径；探测只认含真草稿子目录的候选 |
| `save_draft` 报「剪映正在运行」 | 检测拦截——退出剪映后重跑同一命令（cache 还在） | 重启机器再试 |
| 剪映打开草稿报「文件损坏」 | vendor 模板版本与剪映版本不匹配——换 `vendor/template_jianying/.backup/` 里的旧模板重存 | 降级路线：不建 Draft，改交付 SRT + 素材清单，让用户在 GUI 手动导入 |
| 剪映打开后 JSON 被加密 | 预期内行为——禁止改已打开草稿 | 追加内容走「导出 SRT → GUI 导入」路线（先 `subtitle_split.py` 拆条） |
| cache 丢失（`.jianying_cache/` 被删） | 从 `jianying_draft_manifest.md` 找回 draft id 和媒体清单 | 🔴 已打开过的草稿无法增量恢复——重建 Draft 并告知用户已精剪内容会丢，等用户决策 |
| `import_srt` 时间戳解析失败 | SRT 编码不是 UTF-8——转码后重试（脚本已按 `utf-8-sig` 读） | 用 `align_to_manuscript.py` 重新生成干净 SRT |
| 媒体文件被移走 | 草稿自包含不受影响；`missing_media` 项补回后重存 | manifest 记断链，路由回用户补素材 |
| `import pyJianYingDraft` 失败 | env `CAPCUT_MCP_DIR` 失效——已自动回退内置 vendor，修正 `.env` | 确认 `vendor/pyJianYingDraft/` 完整 |
| 新机器/新剪映版本 | 先跑「冒烟测试」再正片 | 冒烟不过按上表排查，仍不过走 SRT 降级 |

🔴 **CHECKPOINT：`save_draft` 前确认草稿根（探测结果首跑也确认）+ 剪映已完全退出（脚本再拦一道）；保存后展示 manifest 与输出 JSON（media_copied/missing_media/字幕条数），确认才算完成。**

## 禁止

- 不在剪映开着草稿时改写它的 JSON（写入即损坏；`save_draft` 进程检测会拦）；
- 不把草稿根猜在未验证目录上（探测只认含真草稿子目录的候选，探不到等用户给路径）；
- 不跳过 `subtitle_split` 直接导入句子级长条 SRT；
- 不在同一 cache 上反复 `create_draft` 生成多个空草稿；
- 不把 `Rough/.jianying_cache/` 删除或移出项目（它是草稿状态的唯一载体）；
- 替换已存在草稿前不问用户——旧草稿进 `.jianying-trash/`、失败自动回滚，仍需确认可弃；
- 不把自包含草稿目录直接分发他人（JSON 含本机绝对路径）——对外只交付成片。

## 输出

```text
<草稿根>/<draft-id>/
├── draft_content.json      # 素材路径已指向 assets/，自包含
└── assets/                 # 媒体副本（同名自动后缀）
Rough/
├── .jianying_cache/<draft-id>.pkl
└── jianying_draft_manifest.md
```

完成后用户可以在剪映中进行内部精剪；精剪完成必须导出 `Sub/master.srt`，再进入 B-roll 规划。

## 实测标定与经验常数

来源：video-shotcraft（Mac 11.2 实测）+ pyJianYingDraft 上游（Win 5.9/10.8）；Win 或有偏差，先冒烟再调参。

- **字号单位**：`Text_style(size=…)` ≈ 画布高度百分比——size 15 ≈150px @1080p；CSS px ÷ 10.8 ≈ size（64px→6.0）；
- **垂直定位**：`transform_y=t` 半高归一，`屏幕 y = 540 × (1 − t)`；底部 t ≈ −0.70 / −0.825（y≈915/985）；
- **颜色**：0–1 浮点三元组（`#2C2C2C`→`(0.173,)*3`）；`--font-color` 传 `#RRGGBB` 自动换算；
- **微秒边界铁律**：相邻段起点/终点各自取整再相减——起点与时长分别取整产生 1µs 缝隙即 `SegmentOverlap`；自行算帧→微秒时遵守（脚本按秒已规避）；
- **双语拆两轨**：一段文本一字号，中文大英文小分 `字幕ZH`/`字幕EN`；
- **字体**：不指定用默认；导出后可在剪映换字体微调。

## 冒烟测试（新机器/新版本首跑）

临时 cache 建最小三轨草稿走完整链路，验证后再正片：

```bash
# ffmpeg lavfi: testsrc2 6s + sine 5s 到 <tmp>\
# 再 create_draft → add_video → add_audio → add_text → save_draft（cache=<tmp>\）
```

三查：① 不报「内容已损坏/媒体丢失」；② 三轨都在；③ 文字可改内容/字号。不过按失败表排查；验证完删草稿。

## 交付验收

1. 脚本自检：`save_draft` 输出的 `media_copied`/`missing_media` 符合预期，无 `.tmp` 残留；
2. 用户三查：播放连贯（含分道混音）；改字幕；试变速；
3. `.jianying-trash/` 无残留（有则提示手动删）。

## 运行前依赖

剪映适配库和 Draft 模板已经随本 Skill 放在：

```text
<合集根>/scripts/video-jianying-draft/vendor/
├── pyJianYingDraft/
└── template_jianying/
```

如需使用其他 `pyJianYingDraft` 或剪映模板，可设置 `CAPCUT_MCP_DIR` 覆盖默认 vendor（失效路径自动回退内置）。

## CLI 示例

```bash
set CACHE=<项目>/Rough/.jianying_cache
for /f "delims=" %i in ('uv run --project "<合集根>" python "<合集根>/scripts/video-jianying-draft/jianying.py" create_draft --width 1920 --height 1080 --cache-dir "%CACHE%"') do set RESULT=%i
```

实际项目按 `create_draft -> add_video -> add_subtitle -> add_audio -> save_draft` 顺序执行，`--cache-dir` 全程一致；`--output` 可省略（自动探测，首跑展示结果）；`add_audio` 默认贪心分道。常用参数：

```bash
# BGM 与重叠 SFX 各带 --track-name；同轨装不下自动溢出 BGM-2
... add_audio --draft-id <id> --cache-dir "%CACHE%" --file <bgm> --track-name BGM
... add_audio --file <sfx> --track-name SFX --target-start 12.5 --volume 0.6

# 字幕：默认拆 ≤18 显示单位短条（另存 .split.srt 核对）
... add_subtitle --draft-id <id> --cache-dir "%CACHE%" --srt "<项目>/Sub/caption_corrected.srt"

# 调整单条长度 / 原样导入
... add_subtitle --srt <srt> --max-chars 15      # 更短更碎
... add_subtitle --srt <srt> --no-split          # 不拆分
```

单独预演拆分（不建草稿）：

```bash
uv run --project "<合集根>" python "<合集根>/scripts/video-jianying-draft/subtitle_split.py" \
  "<项目>/Sub/caption_corrected.srt" -o "<项目>/Sub/caption_split.srt" --max-chars 18
```