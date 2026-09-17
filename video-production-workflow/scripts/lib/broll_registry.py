"""Registry of motion graphics and narrative Remotion templates."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

REMOTION_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "remotion-data-causality",
        "name": "Data Causality Comparison",
        "engine": "remotion",
        "engine_version": "^4.0.0",
        "source": "references/b-roll-generate/remotion-templates/templates/comparison-chart.tsx",
        "license": "MIT",
        "aspect_ratios": ["16:9", "9:16"],
        "duration_range": [2.5, 10.0],
        "transparency": "opaque",
        "overlay_mode": "full_frame",
        "style_packs": ["vox_explainer", "documentary_observe", "product_cinematic", "motion_packaging"],
        "shot_grammar": {
            "visual_role": "data_causality",
            "camera_motion": "slow_push_in",
            "motion_dynamics": "staggered_entrance_hold_exit",
            "narrative_focus": "cause_and_effect_transformation",
        },
        "props_schema": {
            "title": {"type": "string", "default": "Performance Comparison", "min_length": 2, "max_length": 30},
            "beforeLabel": {"type": "string", "default": "Baseline", "min_length": 1, "max_length": 15},
            "beforeValue": {"type": "number", "default": 100},
            "afterLabel": {"type": "string", "default": "Optimized", "min_length": 1, "max_length": 15},
            "afterValue": {"type": "number", "default": 20},
            "unit": {"type": "string", "default": "ms", "max_length": 10},
            "callout": {"type": "string", "default": "5x Faster", "max_length": 20},
            "palette": {"type": "string", "default": "deep_blue"},
        }
    },
    {
        "id": "remotion-process-breakdown",
        "name": "Process Architecture Breakdown",
        "engine": "remotion",
        "engine_version": "^4.0.0",
        "source": "references/b-roll-generate/remotion-scenes/src/scenes/LayoutAnimations/StepProgress.tsx",
        "license": "MIT",
        "aspect_ratios": ["16:9", "9:16"],
        "duration_range": [2.0, 8.0],
        "transparency": "full_alpha",
        "overlay_mode": "transparent_overlay",
        "style_packs": ["documentary_observe", "editorial_magazine", "motion_packaging", "vox_explainer"],
        "shot_grammar": {
            "visual_role": "process_breakdown",
            "camera_motion": "pan_reveal",
            "motion_dynamics": "sequential_step_activation",
            "narrative_focus": "modular_disassembly_and_assembly",
        },
        "props_schema": {
            "title": {"type": "string", "default": "Workflow Pipeline", "min_length": 2, "max_length": 30},
            "steps": {"type": "list", "default": ["Plan", "Audit", "Execute", "Verify"]},
            "activeStep": {"type": "integer", "default": 2},
            "palette": {"type": "string", "default": "emerald_tech"},
        }
    },
    {
        "id": "remotion-stat-counter",
        "name": "Kinetic Stat Counter",
        "engine": "remotion",
        "engine_version": "^4.0.0",
        "source": "references/b-roll-generate/remotion-templates/templates/stat-counter.tsx",
        "license": "MIT",
        "aspect_ratios": ["16:9", "9:16"],
        "duration_range": [2.0, 6.0],
        "transparency": "full_alpha",
        "overlay_mode": "transparent_overlay",
        "style_packs": ["motion_packaging", "product_cinematic"],
        "shot_grammar": {
            "visual_role": "metric_counter",
            "camera_motion": "static_focus",
            "motion_dynamics": "exponential_number_roll",
            "narrative_focus": "focal_metric_emphasis",
        },
        "props_schema": {
            "title": {"type": "string", "default": "Total Throughput", "max_length": 25},
            "targetNumber": {"type": "number", "default": 99.9},
            "prefix": {"type": "string", "default": ""},
            "suffix": {"type": "string", "default": "%"},
            "palette": {"type": "string", "default": "warm_accent"},
        }
    }
]

# HyperFrames consumes the same shot-brief fields as Remotion.  The engine
# difference is deliberately registry metadata, not a second manifest format.
HYPERFRAMES_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "hyperframes-editorial-process",
        "name": "Editorial Process Assembly",
        "engine": "hyperframes",
        "engine_version": "local-html-v1",
        "source": "references/b-roll-generate/hyperframes/patterns.md",
        "license": "Apache-2.0",
        "aspect_ratios": ["16:9", "9:16"],
        "duration_range": [2.5, 8.0],
        "transparency": "opaque",
        "overlay_mode": "full_frame",
        "style_packs": ["editorial_magazine", "motion_packaging", "vox_explainer"],
        "shot_grammar": {
            "visual_role": "process_breakdown",
            "camera_motion": "indexed_editorial_push",
            "motion_dynamics": "seek_safe_staggered_assembly",
            "narrative_focus": "modular_disassembly_and_assembly",
        },
        "props_schema": {
            "title": {"type": "string", "default": "Core Process", "min_length": 2, "max_length": 48},
            "steps": {"type": "list", "default": ["Plan", "Build", "Verify"]},
            "activeStep": {"type": "integer", "default": 1},
            "palette": {"type": "string", "default": "warm_editorial"},
        },
    },
]


def list_templates(engine: Optional[str] = "remotion") -> List[Dict[str, Any]]:
    """Return templates for one engine; pass ``None`` to inspect every engine."""
    templates = REMOTION_TEMPLATES + HYPERFRAMES_TEMPLATES
    return [item for item in templates if item["engine"] == engine] if engine else templates


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve template by unique identifier."""
    for t in list_templates(None):
        if t["id"] == template_id:
            return t
    return None


def find_matching_template(visual_role: str, style_pack: Optional[str] = None,
                           duration: Optional[float] = None, engine: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Query template matching visual role, style pack, and duration constraints."""
    candidates = []
    templates = list_templates(engine)
    for t in templates:
        grammar = t.get("shot_grammar", {})
        if grammar.get("visual_role") != visual_role:
            continue
        if style_pack and style_pack not in t.get("style_packs", []):
            continue
        if duration is not None:
            d_min, d_max = t.get("duration_range", [1.0, 60.0])
            if duration < d_min or duration > d_max:
                continue
        candidates.append(t)

    if candidates:
        return candidates[0]

    # Fallback to role match
    for t in templates:
        if t.get("shot_grammar", {}).get("visual_role") == visual_role:
            return t

    return templates[0] if templates else None
