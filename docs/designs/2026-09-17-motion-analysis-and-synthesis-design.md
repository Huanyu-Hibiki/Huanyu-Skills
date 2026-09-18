# 爆款视频动效解构分析与参数化模板生成设计文档

- **创建日期**：2026-09-17
- **状态**：已批准设计 (Approved Design)
- **关联需求**：参考 `hypit`、`vox-director`、`vibe-motion/skills`、`gsap-skills`、`create-vibe-motion`，新增爆款视频动效多模态解构分析功能，产出结构化解构报告并驱动 Remotion / HyperFrames / GSAP 模板自动生成与上轨。

---

## 1. 目标与设计哲学 (Goals & Philosophy)

### 1.1 核心目标
构建一个端到端闭环的动效逆向工程与参数化生成工具链：
1. **输入**：短视频 / 爆款动效片段 (`.mp4` / `.mov` 等，通常为 2~6 秒的独立动态包装镜头）。
2. **阶段一（解构报告）**：通过 FFmpeg 场景抽帧与音频能量重音（Onset/Beat）分析，结合多模态视觉 Agent，输出包含视觉语言、多图层时间轴、物理缓动参数、音画卡点钉帧表与实现原型的《爆款动效解构报告》（Markdown + JSON）。
3. **阶段二（模板生成）**：以解构报告为唯一客观依据（Ground Truth），自动编译出参数化、可独立渲染的 Remotion TSX / GSAP 代码组件，并自动登记进现有管线的 `broll_registry` 与 6 大风格库，供视频生产管线（`B-roll Packaging`）直接调度。

### 1.2 开源许可证与工程吸收原则
- **不生搬硬套庞大外部依赖**：吸收参考项目的核心设计哲学（如 `hypit` 的 Visual IR / 语义卡点概念、`vox-director` 的纸拼贴分层、`gsap-skills` 的物理缓动、`vibe-motion/skills` 的原子动效表现），以原生 Python + UV + Remotion 体系自主实现。
- **纯净合规**：所有生成的模板均为自主参数化组件，不侵犯第三方受限许可证代码。

---

## 2. 系统分层架构与目录拓扑 (System Architecture)

在 `video-production-workflow/scripts/` 下新增专注子模块 `motion-analyzer/`：

```text
video-production-workflow/
├── scripts/
│   ├── motion-analyzer/
│   │   ├── __init__.py
│   │   ├── motion_ir.py              # Motion IR 中间表达数据模型、验证与序列化
│   │   ├── media_extractor.py        # FFmpeg 关键帧时序接触网格图与音频 Onset 能量提取
│   │   ├── motion_reverse_agent.py   # 多模态 Agent 提示词编排与结构化解构推理
│   │   ├── template_synthesizer.py   # 解构报告编译为 Remotion TSX / GSAP 组件
│   │   └── cli.py                    # 独立 CLI 入口 (analyze / synthesize)
│   ├── lib/
│   │   └── broll_registry.py         # 登记解构生成的新模板与参数化入口
│   └── video-auto-edit/
│       └── test_motion_analyzer.py   # 自动化测试套件
├── references/
│   └── motion-analysis/              # 动效解构方法论、参考案例与提示词标准
│       └── motion-decomposition-spec.md
└── templates/
    └── motion-analysis-report.template.md # 爆款动效解构报告标准化模板
```

---

## 3. 核心数据模型：Motion IR Schema

中间表达作为阶段一分析产物与阶段二代码生成的单一契约源：

```json
{
  "$schema": "motion-ir-v1",
  "meta": {
    "source_name": "viral_clip_01.mp4",
    "duration_frames": 90,
    "fps": 30,
    "style_archetype": "vox_explainer",
    "dominant_mood": "analytical_high_tempo"
  },
  "visual_language": {
    "color_palette": ["#1A1A1A", "#F4F0EA", "#E63946", "#F1FAEE"],
    "texture": "paper_tear_with_halftone",
    "spatial_layout": "split_column_emphasis"
  },
  "audio_anchors": {
    "tempo_bpm": 128.0,
    "beats": [0.0, 0.468, 0.937, 1.406, 1.875],
    "onsets": [0.468, 1.120, 1.875],
    "sync_strategy": "snap_entrance_to_nearest_beat"
  },
  "layers": [
    {
      "layer_id": "bg-canvas",
      "type": "background",
      "z_index": 0,
      "motion_dynamics": "subtle_drift_scale_1.0_to_1.05"
    },
    {
      "layer_id": "main-graphic",
      "type": "vector_or_illustration",
      "z_index": 1,
      "phases": {
        "entrance": {
          "start_time": 0.468,
          "duration": 0.35,
          "easing": "spring(damping: 12, stiffness: 180, mass: 0.8)",
          "transforms": ["scale(0 -> 1.05 -> 1.0)", "rotate(-6deg -> 0deg)"]
        },
        "sustain": { "duration": 1.2, "dynamics": "breathing_float" },
        "exit": { "start_time": 2.0, "duration": 0.25, "easing": "power2.in" }
      }
    },
    {
      "layer_id": "headline-text",
      "type": "typography",
      "z_index": 2,
      "typography": { "font_weight": "heavy", "style": "editorial_box" },
      "entrance": { "start_time": 0.55, "type": "stagger_words_slide_up" }
    }
  ],
  "engine_affinity": {
    "recommended_primary": "remotion",
    "fallback": "hyperframes",
    "rationale": "High frame-level spring math and multi-layer React composition."
  }
}
```

---

## 4. 阶段一实现规范：音画多模态分析管线

### 4.1 视觉抽帧与接触网格图 (Visual Contact Sheet)
- **输入边界**：默认优先处理用户指定的 2~8 秒高质量单镜头短视频切片，或通过 `--start 00:15 --end 00:18` 指定长视频中的关键区间，专注单点极致拆解。
- **Agent 协作式调用模型**：
  - `media_extractor.py` 生成网格图和音频卡点表后，输出结构化提示词；
  - 运行在 Agent 会话（如 Antigravity / Claude Code）中时，直接由 Agent 原生视觉能力阅读时序图并填入 `motion_ir.json`；
  - 纯离线环境脚本支持读取环境变量（`GEMINI_API_KEY` / `OPENAI_API_KEY`）作为回退。
- **时序抽样**：
  使用 FFmpeg 抽取 5 个关键动作相位帧：
  1. `0%`：初始进场准备帧
  2. `20%`：主力元素入场高潮帧
  3. `50%`：全要素展开驻留帧
  4. `80%`：退场前置准备帧
  5. `100%`：完结帧
- 使用 FFmpeg `tile` 过滤器自动拼合成一张高解析度的横向时序网格图（`contact_sheet.png`），并打上时间码浮印，减少 Agent 调用 Token 并保证时序全景对比。

### 4.2 音频能量峰值与 Onset 检测 (Acoustic Rhythm Analysis)
- 提取 16kHz 单声道 WAV。
- 使用短时能量均方根（RMS）包络与频谱一阶差分检测客观物理重音（Onsets）。
- 输出毫秒级物理卡点时间列表，作为模型分析音画对齐的基准真相。

### 4.3 报告生成标准模板
自动输出至 `reports/<shot_name>/motion_analysis_report.md` 与 `motion_ir.json`，包含视听特征、逐图层五相位拆解、缓动函数分类与伪代码实现。

---

## 5. 阶段二实现规范：模板合成与管线集成

### 5.1 代码合成引擎 (`template_synthesizer.py`)
- 读取 `motion_ir.json`。
- **Remotion 模式**：
  - 合成符合规范的 React TSX 组件；
  - 自动将 `layers.phases.entrance` 转换为帧级 `spring()` 与 `interpolate()`；
  - 提取开放的可变 Props（标题文本、数值、主题强调色、插图路径）。
- **GSAP 模式**：
  - 合成符合 `gsap-skills` 规范的 `gsap.timeline()` 时间轴序列与贝塞尔曲线代码。

### 5.2 命名空间隔离与版本防覆盖
- **输出目录**：生成的全部组件统一写入独立沙箱目录 `video-production-workflow/templates/synthesized/<style_pack>/<template_id>.tsx`。
- **命名规范**：模板 ID 强制带 `remotion-viral-<style>-<name>-v<N>` 前缀。
- **防破坏规则**：若已存在同名模板，自动递增版本号（如 `-v2`），严禁就地修改或覆盖已有手写生产代码与既有模板。

### 5.3 出厂试渲染质量与安全硬闸门 (Quality & Safety Gate)
- 模板生成后，系统自动执行 **1 秒（30 帧）真实无头渲染探针**：
  1. 验证编译与依赖无语法/类型报错；
  2. 验证导出的透明视频非全黑、非全透明（具备有效视觉运动像素）；
  3. 探针全部通过后，模板状态才被标记为 `approved` 并正式注册到 `broll_registry.py`；
  4. 试渲染失败的模板标记为 `draft_failed`，附带编译器/探针报错日志，等待人工审查，绝不污染生产管线。

---

## 6. 验证与测试策略

1. **单元测试 (`test_motion_analyzer.py`)**：
   - `test_media_extractor_frame_grid_and_onsets`: 验证 FFmpeg 抽帧拼图与音频重音检测输出准确性。
   - `test_motion_ir_schema_validation`: 验证数据模型严格校验非法类型与越界时间戳。
   - `test_template_synthesizer_remotion_code`: 验证合成的 TSX 语法合法且包含计算出的弹簧参数。
   - `test_template_synthesizer_registry_integration`: 验证合成的模板能成功登记进 `broll_registry` 并生成有效 `shot_brief`。
2. **端到端集成测试**：
   - 拿一段合成的测试动效视频，走通 `analyze` -> `synthesize` -> `render` 全链路，验证样片能作为独立包装轨写入剪映草稿。

---

## 7. 错误处理与防御机制

1. **无音频流降级**：若参考视频为纯无声动效，音频分析自动优雅降级，时间轴根据视觉画面关键帧平均分步，不抛致命异常。
2. **模型结构化解析失败重试**：多模态 Agent 解析响应强制经过 Pydantic/dataclass schema 校验，解析失败时自动触发一次修复重试。
3. **合成代码安全沙箱**：自动合成的代码写入预设的安全模板目录，不侵入核心系统文件。
