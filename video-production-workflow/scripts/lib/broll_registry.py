"""Registry of motion graphics and narrative Remotion templates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import copy
import hashlib
import hmac
import json
import math
import re
import secrets
import threading
from pathlib import PurePosixPath

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
        "style_packs": ["vox_explainer"],
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
        "id": "remotion-observe-focus",
        "name": "Documentary Observe & Focus Guide",
        "engine": "remotion",
        "engine_version": "^4.0.0",
        "source": "references/b-roll-generate/remotion-templates/templates/observe-focus.tsx",
        "license": "MIT",
        "aspect_ratios": ["16:9", "9:16"],
        "duration_range": [2.0, 8.0],
        "transparency": "full_alpha",
        "overlay_mode": "transparent_overlay",
        "style_packs": ["documentary_observe"],
        "shot_grammar": {
            "visual_role": "observational_evidence",
            "camera_motion": "smooth_tracking_pan",
            "motion_dynamics": "reticle_lock_and_inspect",
            "narrative_focus": "factual_context_inspection",
        },
        "props_schema": {
            "title": {"type": "string", "default": "系统运行现场观察", "max_length": 30},
            "focusArea": {"type": "string", "default": "核心指标"},
            "palette": {"type": "string", "default": "neutral_dark"},
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
        "style_packs": ["motion_packaging", "documentary_observe", "vox_explainer"],
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
        "style_packs": ["product_cinematic", "motion_packaging"],
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
    },
    {
        "id": "remotion-stop-motion-craft",
        "name": "Stop Motion Paper & Tactile Craft",
        "engine": "remotion",
        "engine_version": "^4.0.0",
        "source": "references/b-roll-generate/remotion-material/stop-motion.tsx",
        "license": "MIT",
        "aspect_ratios": ["16:9", "9:16"],
        "duration_range": [2.0, 8.0],
        "transparency": "opaque",
        "overlay_mode": "full_frame",
        "style_packs": ["stop_motion_craft", "vox_explainer"],
        "shot_grammar": {
            "visual_role": "tactile_craft_disassembly",
            "camera_motion": "subtle_handheld_step",
            "motion_dynamics": "stepped_frame_stop_motion",
            "narrative_focus": "tactile_physical_assembly",
        },
        "props_schema": {
            "title": {"type": "string", "default": "手作卡片逐帧拆解", "max_length": 30},
            "steps": {"type": "list", "default": ["剪裁", "拼贴", "组合"]},
            "activeStep": {"type": "integer", "default": 1},
            "palette": {"type": "string", "default": "kraft_paper"},
        }
    }
]


def _has_excessive_nesting(value: Any, maximum_depth: int = 64) -> bool:
    """Bound JSON traversal work independently of its serialized byte size."""
    pending = [(value, 1)]
    while pending:
        current, depth = pending.pop()
        if depth > maximum_depth:
            return True
        if isinstance(current, dict):
            pending.extend((child, depth + 1) for child in current.values())
        elif isinstance(current, list):
            pending.extend((child, depth + 1) for child in current)
    return False

# HyperFrames consumes the same shot-brief fields as Remotion.  The engine
# difference is deliberately registry metadata, not a second manifest format.
HYPERFRAMES_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "hyperframes-editorial-process",
        "name": "Editorial Process Assembly",
        "engine": "hyperframes",
        "engine_version": "0.6.98",
        "source": "references/b-roll-generate/hyperframes/patterns.md#top-level-composition",
        "composition_source": "references/b-roll-generate/hyperframes/patterns.md#top-level-composition",
        "registry_source": "references/b-roll-generate/hyperframes/patterns.md",
        "design_tokens_source": "references/b-roll-generate/hyperframes/house-style.md",
        "seek_safe_source": "references/b-roll-generate/hyperframes/references/captions.md#caption-exit-guarantee",
        "design_tokens": {
            "background": "#201b14",
            "foreground": "#f1e6d2",
            "accent": "#c44927",
            "highlight": "#e0a11f",
        },
        "adoption_scope": {
            "adopted": ["data-composition-id/data-start/data-duration", "paused GSAP timeline", "warm editorial palette"],
            "not_adopted": ["remote assets", "shader transitions", "full Studio runtime"],
        },
        "license": "Apache-2.0",
        "aspect_ratios": ["16:9", "9:16"],
        "duration_range": [2.5, 8.0],
        "transparency": "opaque",
        "overlay_mode": "full_frame",
        "style_packs": ["editorial_magazine", "vox_explainer", "motion_packaging"],
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


AI_VISUAL_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": "ai-visual-vox-metaphor",
        "name": "Vox Conceptual Metaphor",
        "engine": "ai_visual",
        "engine_version": "^1.0.0",
        "source": "models/imagen3/veo2",
        "license": "Proprietary-Generated",
        "aspect_ratios": ["16:9", "9:16"],
        "duration_range": [2.0, 8.0],
        "transparency": "opaque",
        "overlay_mode": "full_frame",
        "style_packs": ["vox_explainer", "documentary_observe", "product_cinematic", "editorial_magazine", "minimal_clean", "motion_packaging"],
        "shot_grammar": {
            "visual_role": "conceptual_metaphor",
            "camera_motion": "slow_pan_or_push",
            "motion_dynamics": "atmospheric_subtle_motion",
            "narrative_focus": "abstract_concept_visualization",
        },
        "props_schema": {
            "prompt": {"type": "string", "min_length": 5, "max_length": 500},
            "negative_prompt": {"type": "string", "default": "text, watermark, blurry, deformed"},
            "aspect_ratio": {"type": "string", "default": "16:9"},
            "provider": {"type": "string", "default": "gemini"},
        }
    }
]


# Templates generated during the current process are kept separate from the
# hand-authored production catalog.  A failed probe therefore cannot become a
# candidate through the normal list/query contract.
_DYNAMIC_TEMPLATES: List[Dict[str, Any]] = []
_DYNAMIC_LOCK = threading.RLock()
_USED_PROBE_RECEIPTS: set[str] = set()
_MAX_DYNAMIC_TEMPLATES = 256
_MAX_DYNAMIC_TEMPLATE_BYTES = 64 * 1024
_SOURCE_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
_PROBE_RECEIPT_SECRET = secrets.token_bytes(32)


@dataclass(frozen=True)
class ProbeReceipt:
    """Opaque proof that a generated template passed the render probe.

    The signing key never leaves this module.  Callers can carry a receipt
    returned by the probe, but cannot manufacture a valid one from metadata.
    """

    template_id: str
    source: str
    source_hash: str
    metadata_digest: str
    nonce: str
    signature: str


def _canonical_template_bytes(template: Dict[str, Any]) -> bytes:
    return json.dumps(template, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _receipt_payload(template_id: str, source: str, source_hash: str, metadata_digest: str, nonce: str) -> bytes:
    return f"{template_id}\0{source}\0{source_hash}\0{metadata_digest}\0{nonce}".encode("utf-8")


def _issue_probe_receipt(template: Dict[str, Any]) -> ProbeReceipt:
    """Issue a receipt to the trusted render-probe integration only."""
    template_id = template.get("id")
    source = template.get("source")
    source_hash = template.get("source_hash")
    if not isinstance(template_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", template_id):
        raise ValueError("unsafe template id")
    if not isinstance(source_hash, str) or not _SOURCE_HASH_RE.fullmatch(source_hash):
        raise ValueError("invalid source hash")
    if (
        not isinstance(source, str)
        or not source
        or source.startswith("/")
        or "\\" in source
        or any(part in {"", ".", ".."} for part in PurePosixPath(source).parts)
    ):
        raise ValueError("invalid template source")
    metadata_digest = hashlib.sha256(_canonical_template_bytes(template)).hexdigest()
    nonce = secrets.token_urlsafe(24)
    signature = hmac.new(
        _PROBE_RECEIPT_SECRET,
        _receipt_payload(template_id, source, source_hash, metadata_digest, nonce),
        hashlib.sha256,
    ).hexdigest()
    return ProbeReceipt(template_id, source, source_hash, metadata_digest, nonce, signature)


def _validate_probe_receipt(template: Dict[str, Any], receipt: ProbeReceipt | None) -> None:
    if not isinstance(receipt, ProbeReceipt):
        raise ValueError("dynamic template requires a render-probe receipt")
    template_id = template.get("id")
    source_hash = template.get("source_hash")
    if receipt.template_id != template_id or receipt.source != template.get("source") or receipt.source_hash != source_hash:
        raise ValueError("probe receipt does not match template metadata")
    expected_digest = hashlib.sha256(_canonical_template_bytes(template)).hexdigest()
    if receipt.metadata_digest != expected_digest:
        raise ValueError("probe receipt does not match template metadata")
    if template.get("registry_source") != "render_probe" or template.get("status") != "approved":
        raise ValueError("template is not a render-probe approval")
    expected = hmac.new(
        _PROBE_RECEIPT_SECRET,
        _receipt_payload(receipt.template_id, receipt.source, receipt.source_hash, receipt.metadata_digest, receipt.nonce),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(receipt.signature, expected):
        raise ValueError("invalid render-probe receipt")


_DYNAMIC_REQUIRED_FIELDS = {
    "id", "name", "engine", "engine_version", "source", "license",
    "aspect_ratios", "duration_range", "transparency", "overlay_mode",
    "style_packs", "shot_grammar", "props_schema", "status", "registry_source", "source_hash",
}


def _validate_dynamic_template(template: Dict[str, Any]) -> None:
    missing = _DYNAMIC_REQUIRED_FIELDS.difference(template)
    if missing:
        raise ValueError(f"dynamic template missing fields: {sorted(missing)}")
    template_id = template.get("id")
    if not isinstance(template_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", template_id):
        raise ValueError("unsafe template id")
    for field in ("name", "engine", "engine_version", "source", "license", "transparency", "overlay_mode"):
        if not isinstance(template.get(field), str) or not template[field].strip():
            raise ValueError(f"invalid dynamic template field: {field}")
    if template.get("engine") not in {"remotion", "gsap"}:
        raise ValueError("invalid dynamic template engine")
    if not isinstance(template.get("registry_source"), str) or not template["registry_source"].strip():
        raise ValueError("invalid dynamic template field: registry_source")
    if not isinstance(template.get("source_hash"), str) or not _SOURCE_HASH_RE.fullmatch(template["source_hash"]):
        raise ValueError("invalid dynamic template field: source_hash")
    if template.get("status") != "approved":
        raise ValueError("only approved templates may be registered")
    ratios = template.get("aspect_ratios")
    styles = template.get("style_packs")
    if not isinstance(ratios, list) or not ratios or any(not isinstance(item, str) or not item.strip() for item in ratios):
        raise ValueError("invalid aspect_ratios")
    if not isinstance(styles, list) or not styles or any(not isinstance(item, str) for item in styles):
        raise ValueError("invalid style_packs")
    if any(not item.strip() for item in styles):
        raise ValueError("invalid style_packs")
    duration_range = template.get("duration_range")
    if (
        not isinstance(duration_range, list)
        or len(duration_range) != 2
        or any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in duration_range)
        or any(not math.isfinite(float(item)) for item in duration_range)
        or duration_range[0] < 0
        or duration_range[0] > duration_range[1]
    ):
        raise ValueError("invalid duration_range")
    grammar = template.get("shot_grammar")
    if not isinstance(grammar, dict) or any(not isinstance(grammar.get(key), str) or not grammar[key] for key in (
        "visual_role", "camera_motion", "motion_dynamics", "narrative_focus"
    )):
        raise ValueError("invalid shot_grammar")
    if not isinstance(template.get("props_schema"), dict) or len(template["props_schema"]) > 16:
        raise ValueError("invalid props_schema")
    try:
        encoded = json.dumps(template, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError, RecursionError) as exc:
        raise ValueError("dynamic template must be serializable") from exc
    if len(encoded.encode("utf-8")) > _MAX_DYNAMIC_TEMPLATE_BYTES:
        raise ValueError("dynamic template exceeds size limit")


def register_dynamic_template(template: Dict[str, Any], *, receipt: ProbeReceipt | None = None) -> Dict[str, Any]:
    """Register one probe-approved template without mutating static catalogs."""
    if not isinstance(template, dict):
        raise ValueError("template must be a JSON object")
    _validate_probe_receipt(template, receipt)
    _validate_dynamic_template(template)
    template_id = template["id"]
    with _DYNAMIC_LOCK:
        if receipt is None or receipt.signature in _USED_PROBE_RECEIPTS:
            raise ValueError("render-probe receipt has already been consumed")
        if len(_DYNAMIC_TEMPLATES) >= _MAX_DYNAMIC_TEMPLATES:
            raise ValueError("dynamic template registry is full")
        if any(item.get("id") == template_id for item in REMOTION_TEMPLATES + HYPERFRAMES_TEMPLATES + AI_VISUAL_TEMPLATES + _DYNAMIC_TEMPLATES):
            raise ValueError("template id already registered")
        stored = copy.deepcopy(template)
        _DYNAMIC_TEMPLATES.append(stored)
        _USED_PROBE_RECEIPTS.add(receipt.signature)
        return copy.deepcopy(stored)


def unregister_dynamic_template(template_id: str) -> bool:
    """Remove a process-local generated template, primarily for test cleanup."""
    with _DYNAMIC_LOCK:
        for index, template in enumerate(_DYNAMIC_TEMPLATES):
            if template.get("id") == template_id:
                del _DYNAMIC_TEMPLATES[index]
                return True
    return False


def list_templates(engine: Optional[str] = "remotion") -> List[Dict[str, Any]]:
    """Return templates for one engine; pass ``None`` to inspect every engine."""
    with _DYNAMIC_LOCK:
        templates = copy.deepcopy(REMOTION_TEMPLATES + HYPERFRAMES_TEMPLATES + AI_VISUAL_TEMPLATES + _DYNAMIC_TEMPLATES)
    return [item for item in templates if item["engine"] == engine] if engine else templates


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve template by unique identifier."""
    for t in list_templates(None):
        if t["id"] == template_id:
            return t
    return None


def validate_shot_brief(brief: Dict[str, Any], engine: Optional[str] = None) -> Dict[str, Any]:
    """Validate the public shot-brief contract against its registry entry."""
    if not isinstance(brief, dict):
        raise ValueError("shot brief must be a JSON object no larger than 32KiB")
    try:
        encoded_brief = json.dumps(brief, ensure_ascii=False)
    except (TypeError, ValueError, RecursionError) as error:
        raise ValueError("shot brief must be serializable and not deeply nested") from error
    if len(encoded_brief.encode("utf-8")) > 32_768 or _has_excessive_nesting(brief):
        raise ValueError("shot brief must be a JSON object no larger than 32KiB")
    template = get_template(str(brief.get("template_id", "")))
    if not template:
        raise ValueError("unsupported template_id")
    actual_engine = brief.get("engine")
    if actual_engine != template["engine"] or (engine and actual_engine != engine):
        raise ValueError("unsupported engine/template combination")
    if brief.get("style_pack") not in template["style_packs"]:
        raise ValueError("unsupported style_pack for template")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", str(brief.get("id", ""))):
        raise ValueError("unsafe shot id")
    try:
        duration = float(brief.get("duration"))
    except (TypeError, ValueError):
        raise ValueError("invalid duration") from None
    low, high = template["duration_range"]
    if not low <= duration <= high:
        raise ValueError("duration outside template range")
    if "transparency" not in brief or brief["transparency"] != template["transparency"]:
        raise ValueError("transparency capability mismatch")
    if "overlay_mode" not in brief or brief["overlay_mode"] != template["overlay_mode"]:
        raise ValueError("overlay_mode capability mismatch")
    props = brief.get("props", {})
    if not isinstance(props, dict) or len(props) > 16:
        raise ValueError("invalid props")
    return template


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

    # A requested style/engine is an explicit semantic constraint.  Returning
    # a role-only template here would silently change the visual language.
    if style_pack is not None or engine is not None:
        return None

    # Fallback to role match
    for t in templates:
        if t.get("shot_grammar", {}).get("visual_role") == visual_role:
            return t

    return templates[0] if templates else None
