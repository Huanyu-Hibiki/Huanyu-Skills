---
name: video-jianying-draft
description: 剪映原生 Draft 生成器。根据 EDL、校对字幕、音频和图片素材创建或更新剪映专业版草稿，直接输出 native draft_content.json 和 assets。触发词：创建剪映草稿、导入剪映、剪映 draft、生成剪映工程。
argument-hint: "[project-path] [--draft-root path]"
allowed-tools: Bash(*), Read, Write, Edit, Glob
---

# /video-jianying-draft

## 输入

- `Rough/edl.json` 或已经确认的 segment list；
- `Sub/caption_corrected.srt`；
- 用户确认的音乐、音效、图片和基础视频；
- 剪映 GUI 的真实草稿根路径。

## 标准命令序列

使用 `<合集根>/scripts/video-jianying-draft/jianying.py`，所有命令使用同一个 cache：

```text
create_draft
  → add_video × N
  → add_subtitle
  → add_audio
  → add_text / add_image / add_effect / add_sticker（按已确认需求）
  → save_draft
```

## 规则

- `Rough/.jianying_cache/` 是当前草稿状态唯一载体，命令间不能更换；
- `--output` 必须是剪映 GUI 设置的实际草稿根，不猜默认路径；
- **字幕断行**：`add_subtitle` 默认把超长字幕条拆成 ≤18 显示单位（汉字 1、ASCII 0.5）的短条——拆分点优先标点、时间轴连续无缝隙，落盘为 `<原名>.split.srt` 供核对；需要原样导入时加 `--no-split`，需要其他长度用 `--max-chars`；
- 优先在用户第一次打开剪映前完成全量写入；
- 剪映打开后 JSON 可能被加密，禁止直接用 JSON 修改已打开草稿；
- 已有草稿追加字幕优先输出 SRT 让用户在 GUI 导入（导入前同样先用 `subtitle_split.py` 拆条）；
- 不遇到错误就反复 `create_draft` 生成新草稿；
- 每次保存写入 `Rough/jianying_draft_manifest.md`，记录 draft id、cache、输出根和媒体清单。

## 失败模式与恢复

| 触发条件 | 一线修复 | 仍失败兜底 |
|---|---|---|
| `add_subtitle` 后静帧仍是超长文本框 | 确认没传 `--no-split`；检查 `.split.srt` 是否生成、cue 数是否增加 | 拆分条数仍不对时改用 `subtitle_split.py` 单独跑并人工核对后再导入 |
| `save_draft` 输出目录找不到草稿 | `--output` 不是剪映 GUI 的实际草稿根——让用户在剪映「全局设置→草稿位置」复制真实路径 | 🔴 不猜默认路径；路径未确认前不写入 |
| 剪映打开草稿报「文件损坏」 | vendor 模板版本与剪映版本不匹配——换 `vendor/template_jianying/.backup/` 里的旧模板重存 | 降级路线：不建 Draft，改交付 SRT + 素材清单，让用户在 GUI 手动导入 |
| 剪映打开后 JSON 被加密 | 预期内行为——禁止改已打开草稿 | 追加内容走「导出 SRT → GUI 导入」路线（先 `subtitle_split.py` 拆条） |
| cache 丢失（`.jianying_cache/` 被删） | 从 `jianying_draft_manifest.md` 找回 draft id 和媒体清单 | 🔴 已打开过的草稿无法增量恢复——重建 Draft 并告知用户已精剪内容会丢，等用户决策 |
| `import_srt` 时间戳解析失败 | SRT 编码不是 UTF-8——转码后重试（脚本已按 `utf-8-sig` 读） | 用 `align_to_manuscript.py` 重新生成干净 SRT |
| 媒体文件被移走导致草稿离线 | 素材已在 `assets/` 留副本——重指向副本路径 | manifest 记录断链，路由回用户补素材 |

🔴 **CHECKPOINT：`save_draft` 前必须向用户确认草稿根路径真实存在且剪映已关闭；保存后展示 manifest（draft id、媒体数、字幕条数），用户确认后才算完成。**

## 禁止

- 不在剪映开着草稿时改写它的 JSON（可能已加密，写入即损坏）；
- 不猜默认草稿根路径（`C:\Users\...\JianyingPro Drafts` 之类一律先向用户核实）；
- 不跳过 `subtitle_split` 直接导入句子级长条 SRT；
- 不在同一 cache 上反复 `create_draft` 生成多个空草稿；
- 不把 `Rough/.jianying_cache/` 删除或移出项目（它是草稿状态的唯一载体）；
- 不覆盖已存在的草稿目录（`save_draft` 会先删旧目录——先向用户确认旧草稿可弃）。

## 输出

```text
Jianying-draft/
├── draft_content.json
└── assets/
Rough/
├── .jianying_cache/<draft-id>.pkl
└── jianying_draft_manifest.md
```

完成后用户可以在剪映中进行内部精剪；精剪完成必须导出 `Sub/master.srt`，再进入 B-roll 规划。

## 运行前依赖

剪映适配库和 Draft 模板已经随本 Skill 放在：

```text
<合集根>/scripts/video-jianying-draft/vendor/
├── pyJianYingDraft/
└── template_jianying/
```

如需使用其他 `pyJianYingDraft` 或剪映模板，可设置 `CAPCUT_MCP_DIR` 覆盖默认 vendor 路径。

## CLI 示例

```bash
set CACHE=<项目>/Rough/.jianying_cache
for /f "delims=" %i in ('uv run --project "<合集根>" python "<合集根>/scripts/video-jianying-draft/jianying.py" create_draft --width 1920 --height 1080 --cache-dir "%CACHE%"') do set RESULT=%i
```

实际项目中继续按 `create_draft -> add_video -> add_subtitle -> add_audio -> save_draft` 顺序执行，并把所有命令的 `--cache-dir` 保持一致。`add_subtitle` 常用参数：

```bash
# 默认：拆成 ≤18 显示单位的剪映原生风格短条（另存 .split.srt 供核对）
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
