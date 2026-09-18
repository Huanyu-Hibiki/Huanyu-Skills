"""Motion IR (Intermediate Representation) core data models and contract validation.

Establishes a single source of truth for motion analysis, parameterized
Remotion/GSAP synthesis, and pipeline scheduling.
"""

from __future__ import annotations

import re
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# Common easing patterns:
# - spring(...) e.g. spring(damping: 12, stiffness: 180, mass: 0.8)
# - power1.in, power2.out, power3.inOut, quad.in, cubic.out, expo.inOut, sine.in, etc.
# - linear, ease, ease-in, ease-out, ease-in-out, steps(...)
# - cubic-bezier(...)
EASING_REGEX = re.compile(
    r"^(spring\([^)]+\)|power[1-4]\.(in|out|inOut)|(sine|quad|cubic|quart|quint|expo|circ|back|elastic|bounce)\.(in|out|inOut)|linear|ease|ease-in|ease-out|ease-in-out|steps\(\d+.*?\)|cubic-bezier\([^)]+\))$",
    re.IGNORECASE,
)


class MotionIRMeta(BaseModel):
    """Metadata regarding the motion clip and analysis context."""
    source_name: str = Field(default="", description="Original video filename or shot identifier")
    duration_frames: int = Field(gt=0, description="Total duration in frames (must be > 0)")
    fps: float = Field(default=30.0, gt=0, description="Frame rate per second")
    style_archetype: str = Field(default="vox_explainer", description="Style archetype e.g. vox_explainer, 3d_camera_hud")
    dominant_mood: str = Field(default="neutral", description="Mood descriptor e.g. analytical_high_tempo")


class VisualLanguage(BaseModel):
    """Visual style, palette, and spatial layout properties."""
    color_palette: List[str] = Field(default_factory=list, description="Extracted HEX or RGB color codes")
    texture: str = Field(default="clean", description="Texture characteristics e.g. paper_tear_with_halftone")
    spatial_layout: str = Field(default="centered", description="Layout distribution e.g. split_column_emphasis")


class AudioAnchors(BaseModel):
    """Acoustic rhythm anchors and sync markers."""
    tempo_bpm: Optional[float] = Field(default=None, description="Detected tempo in BPM")
    beats: List[float] = Field(default_factory=list, description="Timestamps of detected beats in seconds")
    onsets: List[float] = Field(default_factory=list, description="Timestamps of acoustic energy onsets in seconds")
    sync_strategy: str = Field(
        default="snap_entrance_to_nearest_beat",
        description="Rule for aligning visual transitions with rhythm",
    )


def _validate_easing_string(easing_val: str) -> str:
    """Validate easing string against supported spring(...) and standard easing curves."""
    if easing_val and not EASING_REGEX.match(easing_val.strip()):
        raise ValueError(
            f"Invalid easing syntax: '{easing_val}'. Must be a valid spring(...) or easing curve."
        )
    return easing_val


class EntrancePhase(BaseModel):
    """Phase 1: Ingress / Entrance motion dynamics."""
    start_time: float = Field(default=0.0, ge=0.0, description="Start timestamp in seconds")
    duration: float = Field(default=0.3, ge=0.0, description="Duration of entrance phase in seconds")
    easing: str = Field(
        default="spring(damping: 12, stiffness: 180, mass: 0.8)",
        description="Physical spring or curve easing definition",
    )
    transforms: List[str] = Field(
        default_factory=list,
        description="CSS/Remotion transform keyframe descriptors e.g. scale(0 -> 1.0)",
    )
    type: Optional[str] = Field(default=None, description="Named transition archetype if applicable")

    @field_validator("easing")
    @classmethod
    def validate_easing(cls, v: str) -> str:
        return _validate_easing_string(v)


class SustainPhase(BaseModel):
    """Phase 2: Dwell / Sustain continuous motion dynamics."""
    duration: float = Field(default=1.0, ge=0.0, description="Duration of sustain state in seconds")
    dynamics: str = Field(default="idle", description="Dynamic effect e.g. breathing_float, floating_wiggle")


class ExitPhase(BaseModel):
    """Phase 3: Egress / Exit motion dynamics."""
    start_time: float = Field(ge=0.0, description="Exit trigger timestamp in seconds")
    duration: float = Field(default=0.3, ge=0.0, description="Exit animation duration in seconds")
    easing: str = Field(default="power2.in", description="Exit easing definition")
    transforms: List[str] = Field(default_factory=list, description="Exit transform descriptors")

    @field_validator("easing")
    @classmethod
    def validate_easing(cls, v: str) -> str:
        return _validate_easing_string(v)


class LayerPhase(BaseModel):
    """Lifecycle multi-phase definitions for a visual layer."""
    entrance: Optional[EntrancePhase] = None
    sustain: Optional[SustainPhase] = None
    exit: Optional[ExitPhase] = None


class TypographyConfig(BaseModel):
    """Specific visual typography properties for text layers."""
    font_family: Optional[str] = None
    font_weight: str = "bold"
    style: str = "default"
    color: Optional[str] = None


class Layer(BaseModel):
    """Visual layer representation with z-index and motion phases."""
    layer_id: str = Field(description="Unique layer identifier")
    type: str = Field(
        default="graphic",
        description="Layer category e.g. background, vector_or_illustration, typography, footage",
    )
    z_index: int = Field(default=0, description="Stacking order")
    motion_dynamics: Optional[str] = Field(default=None, description="Background or persistent motion dynamics")
    typography: Optional[TypographyConfig] = None
    phases: LayerPhase = Field(default_factory=LayerPhase, description="Motion life-cycle phases")

    @model_validator(mode="before")
    @classmethod
    def fold_top_level_phases(cls, data: Any) -> Any:
        """Fold top-level entrance, sustain, exit keys into phases if provided directly on the layer."""
        if not isinstance(data, dict):
            return data

        data_copy = dict(data)
        phases_dict = {}
        if isinstance(data_copy.get("phases"), dict):
            phases_dict = dict(data_copy["phases"])

        for phase_key in ("entrance", "sustain", "exit"):
            if phase_key in data_copy:
                val = data_copy.pop(phase_key)
                if phase_key not in phases_dict:
                    phases_dict[phase_key] = val

        if phases_dict:
            data_copy["phases"] = phases_dict

        return data_copy


class EngineAffinity(BaseModel):
    """Engine recommendation and synthesis preferences."""
    recommended_primary: Literal["remotion", "gsap", "hyperframes"] = "remotion"
    fallback: Optional[Literal["remotion", "gsap", "hyperframes"]] = None
    rationale: str = ""


class MotionIR(BaseModel):
    """Motion Intermediate Representation root schema.

    Acts as the single source of truth across the motion analysis and synthesis lifecycle.
    """
    schema_version: str = Field(default="motion-ir-v1", alias="$schema")
    meta: MotionIRMeta
    visual_language: VisualLanguage = Field(default_factory=VisualLanguage)
    audio_anchors: AudioAnchors = Field(default_factory=AudioAnchors)
    layers: List[Layer] = Field(default_factory=list)
    engine_affinity: EngineAffinity = Field(default_factory=EngineAffinity)

    model_config = {
        "populate_by_name": True,
        "serialize_by_alias": True,
        "extra": "ignore",
    }

    @property
    def total_duration_seconds(self) -> float:
        """Calculate total duration in seconds from duration_frames and fps."""
        return self.meta.duration_frames / self.meta.fps

    @model_validator(mode="after")
    def validate_timings_and_chronology(self) -> MotionIR:
        """Validate that all phase timestamps remain within bounds and are chronological."""
        total_duration = self.total_duration_seconds

        for layer in self.layers:
            phases = layer.phases
            # Check entrance bounds
            if phases.entrance:
                if phases.entrance.start_time > total_duration:
                    raise ValueError(
                        f"Layer '{layer.layer_id}' entrance start_time ({phases.entrance.start_time}s) "
                        f"exceeds total duration ({total_duration:.2f}s)"
                    )
                if phases.entrance.start_time + phases.entrance.duration > total_duration:
                    raise ValueError(
                        f"Layer '{layer.layer_id}' entrance end time "
                        f"({phases.entrance.start_time + phases.entrance.duration:.2f}s) "
                        f"exceeds total duration ({total_duration:.2f}s)"
                    )

            # Check exit bounds & chronology with entrance
            if phases.exit:
                if phases.exit.start_time > total_duration:
                    raise ValueError(
                        f"Layer '{layer.layer_id}' exit start_time ({phases.exit.start_time}s) "
                        f"exceeds total duration ({total_duration:.2f}s)"
                    )
                if phases.exit.start_time + phases.exit.duration > total_duration:
                    raise ValueError(
                        f"Layer '{layer.layer_id}' exit end time "
                        f"({phases.exit.start_time + phases.exit.duration:.2f}s) "
                        f"exceeds total duration ({total_duration:.2f}s)"
                    )
                if phases.entrance and phases.exit.start_time < phases.entrance.start_time:
                    raise ValueError(
                        f"Layer '{layer.layer_id}' exit start_time ({phases.exit.start_time}s) "
                        f"cannot be earlier than entrance start_time ({phases.entrance.start_time}s)"
                    )

        return self
