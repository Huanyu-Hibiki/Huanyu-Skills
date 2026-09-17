"""Narrative opportunity detection and shot brief generation for B-roll packaging."""
from __future__ import annotations

import re
from typing import Any, Dict, Optional
from .broll_registry import find_matching_template, get_template


def generate_shot_brief(sentence: Dict[str, Any], style_pack: str = "vox_explainer",
                        talking_head_zone: Optional[Dict[str, float]] = None,
                        template_id: Optional[str] = None, engine: str = "remotion") -> Dict[str, Any]:
    """Generate a structured narrative shot brief from an explanatory A-roll sentence.

    Ensures the shot represents a genuine explanatory process (data causality,
    spatial expansion, modular decomposition) rather than a mere subtitle card.
    """
    text = sentence.get("text", "") or sentence.get("manuscript", "")
    target_start = float(sentence.get("targetStart", 0.0))
    sentence_dur = float(sentence.get("duration", sentence.get("sourceEnd", 4.0) - sentence.get("sourceStart", 0.0)))

    # Semantic analysis for explanatory intent
    is_data_comparison = bool(
        re.search(r"(\d+).*?(从|到|降至|提升|增加|减少|倍|%|ms|s|G|M)", text) or
        any(k in text for k in ("对比", "性能", "耗时", "响应", "提升", "飞跃", "差距", "下降", "翻倍"))
    )
    is_process = bool(
        any(k in text for k in ("流程", "架构", "流水线", "步骤", "阶段", "分为", "首先", "执行", "配置", "机制"))
    )

    if template_id:
        tmpl = get_template(template_id)
        if not tmpl:
            raise ValueError(f"Unknown template_id: {template_id}")
    elif is_data_comparison or not is_process:
        tmpl = find_matching_template(visual_role="data_causality", style_pack=style_pack, engine=engine)
    else:
        tmpl = find_matching_template(visual_role="process_breakdown", style_pack=style_pack, engine=engine)

    if not tmpl:
        raise RuntimeError(f"No suitable {engine} template found in registry")

    # Clamping duration to template range
    d_min, d_max = tmpl.get("duration_range", [2.5, 8.0])
    shot_dur = round(max(d_min, min(d_max, max(2.5, sentence_dur))), 2)

    # Populate narrative props based on template role
    visual_role = tmpl.get("shot_grammar", {}).get("visual_role")
    props: Dict[str, Any] = {}

    if visual_role == "data_causality":
        # Extract numbers if present
        nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
        b_val = nums[0] if len(nums) > 0 else 1000
        a_val = nums[1] if len(nums) > 1 else (nums[0] / 10 if len(nums) == 1 else 100)
        callout = ""
        if len(nums) >= 3:
            callout = f"{int(nums[2])}x 加速"
        elif "倍" in text:
            m = re.search(r"(\d+(?:\.\d+)?)\s*倍", text)
            callout = f"{m.group(1)}x 提升" if m else "大幅提升"
        else:
            callout = "显著优化"

        props = {
            "title": "系统性能指标对比",
            "beforeLabel": "基线指标",
            "beforeValue": b_val,
            "afterLabel": "优化成效",
            "afterValue": a_val,
            "unit": "ms" if "ms" in text or b_val > 50 else ("s" if "s" in text else "pts"),
            "callout": callout,
            "palette": "deep_blue" if style_pack == "vox_explainer" else "tech_dark",
        }
        visual_intent = f"以数据对比展现从 {props['beforeLabel']} 到 {props['afterLabel']} 的因果变化，突出 {callout}"

    elif visual_role == "process_breakdown":
        props = {
            "title": "核心执行流程",
            "steps": ["代码审计", "单元测试", "草稿合成", "合规验证"],
            "activeStep": 2,
            "palette": "emerald_tech",
        }
        visual_intent = "分步展开系统处理流程，按时间线高亮激活当前执行步骤"

    else:
        props = {
            "title": "核心量化指标",
            "targetNumber": 99.9,
            "prefix": "",
            "suffix": "%",
            "palette": "warm_accent",
        }
        visual_intent = "高光强调核心业务指标与关键结论"

    # Default talking head avoidance zone
    th_zone = talking_head_zone if talking_head_zone is not None else {
        "x": 0.65, "y": 0.50, "w": 0.35, "h": 0.50
    }

    sent_id = sentence.get("id", "sent-0")
    shot_id = f"broll-pkg-{sent_id}"

    shot_brief = {
        "id": shot_id,
        "sentence_id": sent_id,
        "anchor": text[:30],
        "target_start": target_start,
        "duration": shot_dur,
        "fps": int(sentence.get("fps", 25)),
        "route": "packaging",
        "engine": tmpl["engine"],
        "template_id": tmpl["id"],
        "overlay_mode": tmpl.get("overlay_mode", "full_frame"),
        "transparency": tmpl.get("transparency", "opaque"),
        "style_pack": style_pack,
        "shot_grammar": tmpl.get("shot_grammar", {}),
        "visual_intent": visual_intent,
        "props": props,
        "face_avoidance_zone": th_zone,
        "status": "proposed",
    }
    return shot_brief
