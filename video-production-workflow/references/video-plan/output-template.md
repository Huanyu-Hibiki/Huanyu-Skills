# Output Template

Use these structures exactly unless the user provides a different schema.

## File Locations

Planning files go here:

```text
<视频项目根>\{第X期：视频标题}\video scripts\
```

Expected planning files:

```text
video scripts\storyboard.json
video scripts\material_suggestion_doc.md
video scripts\remotion_candidate_list.md
video scripts\music_cue_sheet.json
video scripts\feishu_storyboard_records.json
video scripts\motion_request_list.md
```

Asset request file goes here:

```text
assets\requests\asset_request_list.md
```

Do not save generated planning files in `edit\handoff\`, the skill directory, or workspace root.

## storyboard.json

```json
{
  "project": {
    "episode_id": "EP001",
    "date": "2026-05-05",
    "video_title": "让AI当你的赛博谋臣，是灾难还是外挂？",
    "total_duration_estimate": "8-12min",
    "platforms": ["Bilibili", "YouTube"],
    "aspect_ratio": "16:9",
    "workflow": "实拍 + OBS + 万兴喵影 + Remotion素材补强",
    "project_folder": "<视频项目根>\\{第X期：视频标题}"
  },
  "scenes": [
    {
      "scene_id": "EP001-S01-001",
      "outline": "开场钩子：AI是工具还是赛博谋臣",
      "main_shot_no": "S01",
      "sub_shot_no": "001",
      "script_text": "当AI的智能，在某些方面已经开始超越我们人类的时候，有的人会把它当做工具，而我，把它当做我的赛博伙伴。",
      "estimated_duration_sec": 10,
      "reference_image": {
        "needed": true,
        "path": "",
        "prompt": "深色赛博空间中，多个AI标识以光影形式动态交叠，中心浮现赛博谋臣概念，科技感，深色背景，蓝色能量线，电影感构图，无水印"
      },
      "presentation": {
        "primary": "Remotion全屏解释动画",
        "secondary": ["字幕", "音效点", "背景音乐"]
      },
      "visual": {
        "suggestion": "屏幕快速闪过多个AI Logo，动态交叠。",
        "description": "多个AI标识快速闪现并形成交错光阵，最后汇聚成视频标题。"
      },
      "execution_note": "如果万兴喵影能完成Logo快闪，则优先万兴喵影；如果要做成固定品牌化开场模板，则使用Remotion。",
      "music_mood": "轻赛博铺底",
      "remotion_value": "Maybe",
      "status": "待规划",
      "material_analysis": {
        "visual_need": "Strong",
        "recommended_source": "Filmora_or_Remotion",
        "material_type": "logo_intro",
        "reusability": "Medium",
        "priority": "High"
      },
      "audio_notes": {
        "music_needed": true,
        "sfx_needed": true,
        "sfx_keywords": ["digital whoosh", "glitch hit"],
        "avoid": ["带歌词", "过度史诗化", "压过口播"]
      },
      "risk_flags": ["Logo使用需注意品牌素材合规", "不要让开场动效影响标题可读性"]
    }
  ]
}
```

## material_suggestion_doc.md

Derive from `storyboard.json`.

```md
# Material Suggestion Document

- **Project Folder**: `<视频项目根>\{第X期：视频标题}`
- **Source File**: `video scripts\storyboard.json`

## Summary Table

| Scene ID | Outline | Primary Presentation | Visual Need | Recommended Source | Material Type | Remotion Value | Priority | Asset Needed |
|---|---|---|---|---|---|---|---|---|
| EP001-S01-001 | 开场钩子 | Remotion全屏解释动画 | Strong | Filmora_or_Remotion | logo_intro | Maybe | High | Yes |

## Scene Details

### EP001-S01-001

- **Script Range**: `[scene.script_text]`
- **Visual Intent**: `[scene.visual.suggestion]`
- **Visual Description**: `[scene.visual.description]`
- **Recommended Strategy**: `[specific production-facing strategy]`
- **Source Recommendation**: 实拍 / OBS / 万兴喵影 / Remotion / Stock / 文生图 / 混合
- **Reason**: `[why this source fits better than alternatives]`
- **Audio Need**: `[music and SFX summary]`
- **Asset Need**: `[external asset needs or None]`
- **Safe Area / Placement**: `[placement constraints]`
- **Risks**: `[risk flags]`
```

## remotion_candidate_list.md

Include only `remotion_value = Yes`, or `Maybe` with high reusability.

```md
# Remotion Candidate List

## R01

- **Related Scene ID**: EP001-S04-001
- **Main Shot**: S04
- **Suggested Template**: MultiAgentResearchFlow
- **Purpose**: 解释同一任务如何被多个AI分头调研并汇总成市场报告
- **Format**: MP4 insert / transparent WebM
- **Duration Estimate**: 8-12s
- **Priority**: High
- **Reusability**: High
- **Text Elements**:
  - 同一调研任务
  - Gemini
  - Kimi
  - ChatGPT
  - 市场报告
- **Notes**: 不要做成纯装饰科技感，核心是解释信息流向。
```

## music_cue_sheet.json

Group by narrative phase, not mechanically by scene.

```json
{
  "music_strategy": {
    "overall_mood": "赛博、技术复盘、谋略感、Build in Public",
    "avoid": ["带歌词", "压过口播", "过度史诗化", "版权风险高的影视感配乐"]
  },
  "cues": [
    {
      "cue_id": "M01",
      "related_scene_ids": ["EP001-S01-001", "EP001-S01-002"],
      "purpose": "开场建立赛博谋臣主题",
      "music_mood": "轻赛博铺底",
      "intensity": "High",
      "duration_estimate_sec": 20,
      "bpm_range": "90-120",
      "sfx_needed": ["digital whoosh", "glitch hit"],
      "asset_needed": true,
      "notes": "短促有冲击，但不能压口播"
    }
  ]
}
```

## asset_request_list.md

Save to `assets\requests\asset_request_list.md` for `video-assets`.

```md
# Asset Request List

- **Project Folder**: `<视频项目根>\{第X期：视频标题}`
- **Output Root**: `assets\`

## Asset 01

- **Related Cue ID**: M01
- **Related Scene IDs**: EP001-S01-001, EP001-S01-002
- **Asset Type**: Background Music
- **Purpose**: 开场建立赛博谋臣氛围
- **Mood**: 轻赛博、低频、短促、有冲击
- **Duration Needed**: 20s
- **License Requirement**:
  - commercial use allowed
  - no attribution preferred
  - no editorial-only
- **Preferred Source**:
  - Pixabay
  - Mixkit
  - YouTube Audio Library
- **Output Format**:
  - WAV 48kHz stereo
- **Target Folder**: `assets\audio\music\`
- **Notes**:
  - 不要带歌词
  - 不要仿影视原声
```

## feishu_storyboard_records.json

Flatten `storyboard.json` for n8n. Use `scene_id` as the upsert key.

```json
{
  "target": {
    "type": "feishu_bitable",
    "table": "分镜表",
    "unique_key": "scene_id"
  },
  "records": [
    {
      "unique_key": "EP001-S01-001",
      "fields": {
        "期数": "EP001",
        "时间": "2026-05-05",
        "视频标题": "让AI当你的赛博谋臣，是灾难还是外挂？",
        "总时长": "8-12min",
        "大纲": "开场钩子：AI是工具还是赛博谋臣",
        "主镜号": "S01",
        "分镜号": "001",
        "逐字稿": "当AI的智能，在某些方面已经开始超越我们人类的时候……",
        "参考图": "",
        "时长": 10,
        "主呈现方式": "Remotion全屏解释动画",
        "辅助呈现方式": ["字幕", "音效点", "背景音乐"],
        "画面建议": "屏幕快速闪过多个AI Logo，动态交叠。",
        "画面描述": "多个AI标识快速闪现并形成交错光阵，最后汇聚成视频标题。",
        "分镜图提示词": "深色赛博空间中，多个AI标识以光影形式动态交叠……",
        "执行说明": "如果万兴喵影能完成Logo快闪，则优先万兴喵影；如果要做成固定品牌化开场模板，则使用Remotion。",
        "配乐情绪": "轻赛博铺底",
        "Remotion价值": "Maybe",
        "状态": "待规划",
        "scene_id": "EP001-S01-001",
        "raw_scene_json": "{\"scene_id\":\"EP001-S01-001\"}"
      }
    }
  ]
}
```

## motion_request_list.md

Generate only after rough cut. Save to `video scripts\motion_request_list.md`.

```md
# Motion Request List

## Motion 01

- **Related Scene ID**: EP001-S04-001
- **Related Rough Cut Clip**: Clip 04
- **Timecode**: 01:15-01:24
- **Source**: Remotion
- **Composition Name**: MultiAgentResearchFlow
- **Purpose**: 解释多AI协同调研流程
- **Format**: MP4 insert / transparent WebM overlay / PNG sequence
- **Resolution**: 1920x1080
- **FPS**: 30
- **Duration**: 9s
- **Text Elements**:
  - 同一调研任务
  - Gemini
  - Kimi
  - ChatGPT
  - 市场报告
- **External Asset Needs**: None / Background music / SFX / stock video / stock image
- **Asset Request Path**: `assets\requests\asset_request_list.md`
- **Notes**: 只做解释信息流向，不做完整视频。
```
