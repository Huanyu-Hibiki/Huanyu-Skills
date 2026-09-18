"""Motion Reverse Reasoning & Decomposition Report Generator.

Orchestrates multimodal decomposition prompts incorporating extracted visual
contact sheets and audio acoustic onsets. Drives multimodal LLMs (collaborative
session agent or offline API adapters) to perform layer separation, kinetic
trajectory tracking, and physical spring easing fitting, yielding a structured
decomposition report in Markdown and a strictly validated motion_ir.json.
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Dict, Literal, Optional, Tuple, Union
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from motion_analyzer.media_extractor import MediaExtractionResult  # noqa: E402
from motion_analyzer.motion_ir import MotionIR  # noqa: E402

# System prompt following motion decomposition specifications
DECOMPOSITION_SYSTEM_PROMPT = """你是一名资深爆款短视频动态包装导演与动效工程师。
你的任务是对提供的短视频关键帧时序网格图（Visual Contact Sheet）以及音频卡点数据进行多模态深度逆向工程，推导出精确符合 Motion IR Schema 契约的结构化动效参数，并分析其视听语言。

### 解构分析原则：
1. **图层物理分离 (Layer Separation)**：
   - 区分背景层 (background, z_index: 0)、矢量图形/主体插画层 (vector_or_illustration)、文字排版层 (typography, z_index >= 1) 等。
2. **生命周期三阶段 (Phases)**：
   - 入场 (entrance): 0~30% 时段，必须结合音频重音卡点 (Onsets/Beats)，使用物理弹簧 (如 `spring(damping: 12, stiffness: 180, mass: 0.8)`) 或 `.out` 缓动。
   - 驻留 (sustain): 30~70% 时段，必须包含持续微动 (如 `breathing_float`, `idle`, `subtle_drift`)，严禁完全静止。
   - 出场 (exit): 70~100% 时段，出场动作快速果断，使用 `.in` 缓动 (如 `power2.in`)，时长比入场更短。
3. **输出契约 (Contract)**：
   - 输出中必须包含一段且仅包含一段完整的 ```json 代码块，其内容必须严格满足 Motion IR Schema (schema_version: "motion-ir-v1")。
"""


def _encode_image_to_base64(image_path: Union[str, Path]) -> Tuple[str, str]:
    """Read local image file and encode to base64 with appropriate MIME type.

    Args:
        image_path: Path to local image file.

    Returns:
        Tuple of (mime_type, base64_encoded_str).

    Raises:
        FileNotFoundError: If image file does not exist.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file does not exist: {path}")

    # Determine MIME type based on extension
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type:
        ext = path.suffix.lower()
        if ext in (".jpg", ".jpeg"):
            mime_type = "image/jpeg"
        elif ext == ".png":
            mime_type = "image/png"
        elif ext == ".webp":
            mime_type = "image/webp"
        else:
            mime_type = "image/png"

    raw_bytes = path.read_bytes()
    b64_str = base64.b64encode(raw_bytes).decode("utf-8")
    return mime_type, b64_str


def build_motion_decomposition_prompt(extraction_result: MediaExtractionResult) -> str:
    """Build structured multimodal prompt injecting visual timeline and audio anchors.

    Args:
        extraction_result: Output from media_extractor containing timing, keyframes, and onsets.

    Returns:
        Structured prompt string ready for multimodal reasoning.
    """
    timestamps_str = ", ".join(str(ts) for ts in extraction_result.keyframe_timestamps)

    if extraction_result.has_audio and extraction_result.audio_anchors.tempo_bpm is not None:
        audio_info = f"""- 检测音轨: 有声
- BPM (节奏): {extraction_result.audio_anchors.tempo_bpm}
- 音频卡点 (Onsets, 秒): {extraction_result.audio_anchors.onsets}
- 节拍脉冲 (Beats, 秒): {extraction_result.audio_anchors.beats}
- 同步策略: {extraction_result.audio_anchors.sync_strategy}"""
    else:
        audio_info = """- 检测音轨: 无音频流 / 静音 (平滑降级为纯视觉动作相位分析)
- BPM: None
- 音频卡点: []
- 同步策略: snap_to_visual_keyframes"""

    contact_sheet_info = extraction_result.contact_sheet_path or "contact_sheet.png"

    prompt = f"""{DECOMPOSITION_SYSTEM_PROMPT}

## 分析目标素材
- 视频文件: {Path(extraction_result.video_path).name}
- 抽样区间: [{extraction_result.start_time:.3f}s -> {extraction_result.end_time:.3f}s] (总长: {extraction_result.duration:.3f}s)
- 时序网格图 (Visual Contact Sheet): {contact_sheet_info}
- 关键帧相位采样时间戳 (0%, 20%, 50%, 80%, 100%): [{timestamps_str}]

## 音频节奏锚点数据
{audio_info}

## 任务要求
请仔细观察附加的时序网格图，结合音频卡点数据，完成以下分析：
1. 视觉语言提取：主色调、纹理质感、版面空间构图。
2. 逐图层解构：识别前景、文字、主体和背景，为每个图层拟合生命周期阶段（进场 entrance、驻留 sustain、退场 exit），提供精确的时间戳与物理缓动参数（优先拟合 spring 参数或 Remotion 缓动曲线）。
3. 引擎推荐：根据图层复杂度推荐最优渲染引擎（remotion / gsap / hyperframes）。
4. 严格输出标准 Motion IR JSON 格式：

```json
{{
  "$schema": "motion-ir-v1",
  "meta": {{
    "source_name": "{Path(extraction_result.video_path).name}",
    "duration_frames": {int(round(extraction_result.duration * 30))},
    "fps": 30.0,
    "style_archetype": "vox_explainer",
    "dominant_mood": "analytical_high_tempo"
  }},
  "visual_language": {{
    "color_palette": ["#1A1A1A", "#F4F0EA", "#E63946"],
    "texture": "paper_tear_with_halftone",
    "spatial_layout": "split_column_emphasis"
  }},
  "audio_anchors": {{
    "tempo_bpm": {extraction_result.audio_anchors.tempo_bpm if extraction_result.audio_anchors.tempo_bpm is not None else "null"},
    "beats": {json.dumps(extraction_result.audio_anchors.beats)},
    "onsets": {json.dumps(extraction_result.audio_anchors.onsets)},
    "sync_strategy": "{extraction_result.audio_anchors.sync_strategy}"
  }},
  "layers": [
    {{
      "layer_id": "bg-canvas",
      "type": "background",
      "z_index": 0,
      "motion_dynamics": "subtle_drift_scale_1.0_to_1.05"
    }},
    {{
      "layer_id": "main-graphic",
      "type": "vector_or_illustration",
      "z_index": 1,
      "phases": {{
        "entrance": {{
          "start_time": 0.2,
          "duration": 0.4,
          "easing": "spring(damping: 12, stiffness: 180, mass: 0.8)",
          "transforms": ["scale(0 -> 1.0)"]
        }},
        "sustain": {{ "duration": 1.0, "dynamics": "breathing_float" }},
        "exit": {{ "start_time": 2.0, "duration": 0.3, "easing": "power2.in" }}
      }}
    }}
  ],
  "engine_affinity": {{
    "recommended_primary": "remotion",
    "fallback": "hyperframes",
    "rationale": "High frame-level spring math and React multi-layer composition."
  }}
}}
```
"""
    return prompt.strip()


def extract_clean_json_payload(raw_text: str) -> Dict[str, Any]:
    """Robustly extract and sanitize JSON payload from LLM responses.

    Handles:
    - Markdown ```json ... ``` blocks
    - Surrounding conversational commentary
    - Trailing commas before closing braces/brackets
    - Balanced brace search fallback

    Args:
        raw_text: Raw string returned by LLM or agent.

    Returns:
        Clean dictionary parsed from JSON.

    Raises:
        ValueError: If no valid JSON structure could be extracted or parsed.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Failed to extract valid JSON payload: empty input")

    clean_text = raw_text.strip()

    # Step 1: Check for markdown json block
    json_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean_text, re.IGNORECASE)
    candidate_str = json_block_match.group(1).strip() if json_block_match else clean_text

    def _sanitize_and_load(s: str) -> Optional[Dict[str, Any]]:
        # Remove single-line comments //...
        s_clean = re.sub(r"//.*$", "", s, flags=re.MULTILINE)
        # Remove trailing commas before } or ]
        s_clean = re.sub(r",\s*([\]}])", r"\1", s_clean)
        try:
            val = json.loads(s_clean)
            if isinstance(val, dict):
                return val
        except Exception:
            pass
        return None

    # Try loading candidate
    res = _sanitize_and_load(candidate_str)
    if res is not None:
        return res

    # Step 2: Bracket-balancing search if markdown block wasn't present or was malformed
    start_idx = clean_text.find("{")
    while start_idx != -1:
        depth = 0
        in_string = False
        escape = False
        end_idx = -1

        for i in range(start_idx, len(clean_text)):
            char = clean_text[i]
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue

            if not in_string:
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        end_idx = i
                        break

        if end_idx != -1:
            snippet = clean_text[start_idx : end_idx + 1]
            res = _sanitize_and_load(snippet)
            if res is not None and ("$schema" in res or "layers" in res or "meta" in res):
                return res

        start_idx = clean_text.find("{", start_idx + 1)

    raise ValueError(f"Failed to extract valid JSON payload from text: {raw_text[:200]}...")


def generate_decomposition_report(motion_ir: MotionIR) -> str:
    """Generate a structured Markdown report from a validated MotionIR object.

    Args:
        motion_ir: Validated MotionIR instance.

    Returns:
        Structured Markdown report text.
    """
    layers_table_rows = []
    for layer in motion_ir.layers:
        ent = (
            f"{layer.phases.entrance.duration}s ({layer.phases.entrance.easing})"
            if layer.phases.entrance
            else "N/A"
        )
        sus = (
            f"{layer.phases.sustain.duration}s ({layer.phases.sustain.dynamics})"
            if layer.phases.sustain
            else "N/A"
        )
        ext = (
            f"{layer.phases.exit.duration}s ({layer.phases.exit.easing})"
            if layer.phases.exit
            else "N/A"
        )
        layers_table_rows.append(
            f"| `{layer.layer_id}` | {layer.type} | {layer.z_index} | {ent} | {sus} | {ext} |"
        )

    layers_table = "\n".join(layers_table_rows)

    bpm_display = (
        f"{motion_ir.audio_anchors.tempo_bpm} BPM"
        if motion_ir.audio_anchors.tempo_bpm
        else "无音频 / 未检测到 BPM"
    )
    onsets_display = (
        ", ".join(f"{t:.3f}s" for t in motion_ir.audio_anchors.onsets)
        if motion_ir.audio_anchors.onsets
        else "无显著卡点"
    )

    json_snippet = motion_ir.model_dump_json(by_alias=True, indent=2)

    report = f"""# 爆款动效逆向解构报告: {motion_ir.meta.source_name}

> 本报告基于多模态时序网格图与短时能量卡点分析自动逆向推理生成，为后续参数化模板合成与管线调度提供单一事实契约 (Ground Truth)。

---

## 1. 视听特征与全局元数据

- **镜头源**: `{motion_ir.meta.source_name}`
- **总时长 / 帧数**: {motion_ir.total_duration_seconds:.2f}s ({motion_ir.meta.duration_frames} 帧 @ {motion_ir.meta.fps} FPS)
- **风格原型 (Archetype)**: `{motion_ir.meta.style_archetype}`
- **主导情绪 (Mood)**: `{motion_ir.meta.dominant_mood}`
- **提取调色盘**: `{'` `'.join(motion_ir.visual_language.color_palette)}`
- **纹理特征**: `{motion_ir.visual_language.texture}`
- **空间构图**: `{motion_ir.visual_language.spatial_layout}`

### 音频节奏锚点
- **节奏律动**: {bpm_display}
- **关键卡点 (Onsets)**: [{onsets_display}]
- **同步策略**: `{motion_ir.audio_anchors.sync_strategy}`

---

## 2. 逐图层生命周期解构表

| 图层 ID | 类型 | Z 轴 | 入场 (Entrance) | 驻留 (Sustain) | 退场 (Exit) |
|---|---|---|---|---|---|
{layers_table}

---

## 3. 推荐渲染引擎与架构建议

- **推荐引擎**: **{motion_ir.engine_affinity.recommended_primary.upper()}**
- **备用引擎**: {motion_ir.engine_affinity.fallback or "None"}
- **选型理由**: {motion_ir.engine_affinity.rationale}

---

## 4. 契约定义 (Motion IR Specification)

```json
{json_snippet}
```

---
*生成时间: 自动生成*
"""
    return report.strip()


class MotionReverseAgent:
    """Agent coordinator for motion reverse engineering and decomposition report generation."""

    def __init__(
        self,
        mode: Literal["collaborative", "offline_adapter"] = "collaborative",
        llm_caller: Optional[Callable[[str, str], str]] = None,
    ):
        """Initialize agent.

        Args:
            mode: 'collaborative' (outputs prompts for interactive session agent)
                  or 'offline_adapter' (invokes external API or mock caller).
            llm_caller: Optional callable (prompt, image_path) -> response_str for offline mode.
        """
        self.mode: Literal["collaborative", "offline_adapter"] = mode
        self.llm_caller = llm_caller

    def prepare_collaborative_prompt(
        self,
        extraction_result: MediaExtractionResult,
    ) -> Dict[str, Any]:
        """Prepare collaborative prompt payload for interactive agents (e.g. Antigravity/Claude)."""
        prompt = build_motion_decomposition_prompt(extraction_result)
        return {
            "prompt": prompt,
            "contact_sheet_path": extraction_result.contact_sheet_path,
            "has_audio": extraction_result.has_audio,
            "source_name": Path(extraction_result.video_path).name,
        }

    def process_response_and_export(
        self,
        raw_response: str,
        output_dir: Union[str, Path],
    ) -> Tuple[MotionIR, str]:
        """Sanitize response, validate MotionIR, write artifacts to output_dir.

        Args:
            raw_response: LLM string response.
            output_dir: Destination folder for motion_ir.json and motion_analysis_report.md.

        Returns:
            Tuple of (MotionIR instance, markdown report string).
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        payload_dict = extract_clean_json_payload(raw_response)
        motion_ir = MotionIR.model_validate(payload_dict)
        report_md = generate_decomposition_report(motion_ir)

        ir_file = output_path / "motion_ir.json"
        ir_file.write_text(motion_ir.model_dump_json(by_alias=True, indent=2), encoding="utf-8")

        report_file = output_path / "motion_analysis_report.md"
        report_file.write_text(report_md, encoding="utf-8")

        logger.info("Successfully exported Motion IR to %s and report to %s", ir_file, report_file)
        return motion_ir, report_md

    def run(
        self,
        extraction_result: MediaExtractionResult,
        output_dir: Union[str, Path],
    ) -> Tuple[MotionIR, str]:
        """Run full extraction-to-report pipeline.

        In 'collaborative' mode without an llm_caller, raises an instruction error.
        In 'offline_adapter' mode, calls the llm_caller or environment adapter.
        """
        prompt = build_motion_decomposition_prompt(extraction_result)
        image_path = extraction_result.contact_sheet_path or ""

        if self.llm_caller:
            response = self.llm_caller(prompt, image_path)
            return self.process_response_and_export(response, output_dir)

        # Fallback to checking GEMINI_API_KEY or OPENAI_API_KEY
        gemini_key = os.environ.get("GEMINI_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if gemini_key:
            response = self._call_gemini_api(prompt, image_path, gemini_key)
            return self.process_response_and_export(response, output_dir)
        elif openai_key:
            response = self._call_openai_api(prompt, image_path, openai_key)
            return self.process_response_and_export(response, output_dir)
        else:
            raise RuntimeError(
                "MotionReverseAgent run() called in offline mode but no LLM caller or API keys "
                "(GEMINI_API_KEY / OPENAI_API_KEY) are configured. Use 'collaborative' mode or provide an adapter."
            )

    def _call_gemini_api(self, prompt: str, image_path: str, api_key: str) -> str:
        """Lightweight external call adapter for Google Gemini multimodal API."""
        # Use header authentication rather than URL query parameter to avoid leaking keys in logs
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        parts: list[dict[str, Any]] = [{"text": prompt}]

        if image_path and Path(image_path).exists():
            mime_type, b64_data = _encode_image_to_base64(image_path)
            parts.append({
                "inline_data": {
                    "mime_type": mime_type,
                    "data": b64_data,
                }
            })

        req_data = json.dumps({"contents": [{"parts": parts}]}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }
        req = urllib.request.Request(url, data=req_data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    content_parts = candidates[0].get("content", {}).get("parts", [])
                    if content_parts:
                        return content_parts[0].get("text", "")
                raise RuntimeError(f"Gemini API returned unexpected response: {result}")
        except Exception as e:
            raise RuntimeError(f"Failed to invoke Gemini API: {e}") from e

    def _call_openai_api(self, prompt: str, image_path: str, api_key: str) -> str:
        """Lightweight external call adapter for OpenAI Vision API."""
        url = "https://api.openai.com/v1/chat/completions"
        content_list: list[dict[str, Any]] = [{"type": "text", "text": prompt}]

        if image_path and Path(image_path).exists():
            mime_type, b64_data = _encode_image_to_base64(image_path)
            content_list.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{b64_data}"},
            })

        req_data = json.dumps({
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": content_list}],
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        req = urllib.request.Request(url, data=req_data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                raise RuntimeError(f"OpenAI API returned unexpected response: {result}")
        except Exception as e:
            raise RuntimeError(f"Failed to invoke OpenAI API: {e}") from e
