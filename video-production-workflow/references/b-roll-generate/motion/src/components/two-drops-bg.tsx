'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library's own copy of the two-drops composition. The mirror at
// `apps/web/app/projects/[id]/_components/compositions/two-drops-bg.tsx` is
// per-project territory; this one must stay independent so the library page
// never breaks when a project agent edits the per-project copy.
//
// Palette helpers come from `../palettes` (frozen). Do NOT import from
// `@curvable/shared` or the project compositions directory.
// ============================================================================

import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { cornerCyclePalette, twoDropsLightLayers, twoDropsLightShadow } from '../palettes';

export type TwoDropsBgProps = {
  primary: string;
  opacity: number;
  lapPeriod: number;
  loops: number;
  infiniteLoop: boolean;
  // false = dark canvas (screen blend, additive glow); true = light canvas
  // (multiply blend, inverted role mapping so the drops read on white).
  lightMode: boolean;
};

type LayerStructure = {
  scale: number;
  blur: number;
  opacity: number;
  shadow: number;
  role: 'deep' | 'mid' | 'hot' | 'core';
};

const LAYER_STRUCTURE: LayerStructure[] = [
  // Reduced to a 2-layer config tuned in /sandbox/two-drops-tweaker. The
  // middle 'hot' layer is gone  -  its opacity ended at 0 in the sandbox
  // session, so it was contributing only render cost.
  { scale: 3.45, blur: 60,  opacity: 0.55, shadow: 0.63, role: 'deep' },
  { scale: 2.15, blur: 120, opacity: 1.0,  shadow: 0.0,  role: 'core' },
];

const CORNER_RADIUS = 540;
const CORNER_EASE = 0.11;
const HEAD_RADIUS = 130;
const TAIL_LENGTH_MULT = 5.5;
const OVERHANG = 260;
const TAIL_SAMPLES = 30;
const DROP_COUNT = 2;
const PHASE_OFFSETS = [0, 0.5];
const SVG_HALF = 1000;

export const TwoDropsBgDefaults: TwoDropsBgProps = {
  primary: '#F04E23',
  opacity: 1,
  lapPeriod: 8.33,
  loops: 3,
  infiniteLoop: false,
  lightMode: false,
};

export const TwoDropsBgMeta = {
  width: 1920,
  height: 1080,
  fps: 60,
  durationFrames: Math.round(8.33 * 60 * 3),
};

export function computeTwoDropsDuration(p: {
  infiniteLoop: boolean;
  loops: number;
  lapPeriod: number;
  fps: number;
}): number {
  const period = Math.max(0.5, p.lapPeriod);
  if (p.infiniteLoop) return Math.max(60, Math.round(period * p.fps * 30));
  return Math.max(1, Math.round(period * p.fps * Math.max(1, p.loops)));
}

const FADE_MIN_FRAMES = 8;
const FADE_MAX_FRAMES = 30;
const FADE_PERIOD_FRACTION = 0.075;

function fadeFramesFor(lapPeriod: number, fps: number): number {
  const target = Math.round(lapPeriod * fps * FADE_PERIOD_FRACTION);
  return Math.max(FADE_MIN_FRAMES, Math.min(FADE_MAX_FRAMES, target));
}

function smoothstep(t: number): number {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  return t * t * (3 - 2 * t);
}

function perimeterLength(W: number, H: number, rIn: number): number {
  const r = Math.max(0, Math.min(rIn, Math.min(W, H) / 2));
  const w = Math.max(0, W - 2 * r);
  const h = Math.max(0, H - 2 * r);
  const c = (Math.PI * r) / 2;
  return 2 * w + 2 * h + 4 * c;
}

function easedPerimeterT(
  uniformT: number,
  W: number,
  H: number,
  rIn: number,
  strength: number,
): number {
  const r = Math.max(0, Math.min(rIn, Math.min(W, H) / 2));
  const w = Math.max(0, W - 2 * r);
  const h = Math.max(0, H - 2 * r);
  const c = (Math.PI * r) / 2;
  const P = 2 * w + 2 * h + 4 * c;
  if (P === 0) return 0;
  const segLens = [w + c, h + c, w + c, h + c];
  const uStarts = [
    0,
    segLens[0]! / P,
    (segLens[0]! + segLens[1]!) / P,
    (segLens[0]! + segLens[1]! + segLens[2]!) / P,
    1,
  ];
  const seg0PerimStart = (2 * w + 2 * h + 3.5 * c) / P;
  const u = (((uniformT % 1) + 1) % 1);
  let i = 0;
  while (i < 3 && u >= uStarts[i + 1]!) i++;
  const localU = (u - uStarts[i]!) / (uStarts[i + 1]! - uStarts[i]!);
  const ss = localU * localU * (3 - 2 * localU);
  const easedLocal = localU + (ss - localU) * Math.max(0, Math.min(0.7, strength));
  let perimSinceSeg0 = 0;
  for (let j = 0; j < i; j++) perimSinceSeg0 += segLens[j]! / P;
  perimSinceSeg0 += (segLens[i]! / P) * easedLocal;
  return (seg0PerimStart + perimSinceSeg0) % 1;
}

function perimeterPoint(
  t: number,
  W: number,
  H: number,
  rIn: number,
): { x: number; y: number; angle: number } {
  const r = Math.max(0, Math.min(rIn, Math.min(W, H) / 2));
  const w = Math.max(0, W - 2 * r);
  const h = Math.max(0, H - 2 * r);
  const c = (Math.PI * r) / 2;
  const P = 2 * w + 2 * h + 4 * c;
  if (P === 0) return { x: W / 2, y: H / 2, angle: 0 };
  let s = (((t % 1) + 1) % 1) * P;
  if (s < w) return { x: r + s, y: 0, angle: 0 };
  s -= w;
  if (s < c) {
    const a = (s / c) * (Math.PI / 2);
    return { x: W - r + r * Math.sin(a), y: r - r * Math.cos(a), angle: (a * 180) / Math.PI };
  }
  s -= c;
  if (s < h) return { x: W, y: r + s, angle: 90 };
  s -= h;
  if (s < c) {
    const a = (s / c) * (Math.PI / 2);
    return { x: W - r + r * Math.cos(a), y: H - r + r * Math.sin(a), angle: 90 + (a * 180) / Math.PI };
  }
  s -= c;
  if (s < w) return { x: W - r - s, y: H, angle: 180 };
  s -= w;
  if (s < c) {
    const a = (s / c) * (Math.PI / 2);
    return { x: r - r * Math.sin(a), y: H - r + r * Math.cos(a), angle: 180 + (a * 180) / Math.PI };
  }
  s -= c;
  if (s < h) return { x: 0, y: H - r - s, angle: 270 };
  s -= h;
  const a = (s / c) * (Math.PI / 2);
  return { x: r - r * Math.cos(a), y: r - r * Math.sin(a), angle: 270 + (a * 180) / Math.PI };
}

function buildDropPath(
  W: number,
  H: number,
  headEasedT: number,
  head: { x: number; y: number; angle: number },
  R: number,
  tailLengthPx: number,
): string {
  const P = perimeterLength(W, H, CORNER_RADIUS);
  const tailInPhase = P > 0 ? tailLengthPx / P : 0;
  const headθ = (head.angle * Math.PI) / 180;
  const headSin = Math.sin(headθ);
  const headCos = Math.cos(headθ);
  const topX = R * headSin;
  const topY = -R * headCos;
  const botX = -R * headSin;
  const botY = R * headCos;

  let path = `M ${topX.toFixed(2)} ${topY.toFixed(2)} `;
  path += `A ${R.toFixed(2)} ${R.toFixed(2)} 0 0 1 ${botX.toFixed(2)} ${botY.toFixed(2)} `;

  const samples: Array<{ dx: number; dy: number; sin: number; cos: number; w: number }> = [];
  for (let i = 1; i <= TAIL_SAMPLES; i++) {
    const t = headEasedT - (i / TAIL_SAMPLES) * tailInPhase;
    const sample = perimeterPoint(t, W, H, CORNER_RADIUS);
    const θ = (sample.angle * Math.PI) / 180;
    samples.push({
      dx: sample.x - head.x,
      dy: sample.y - head.y,
      sin: Math.sin(θ),
      cos: Math.cos(θ),
      w: R * (1 - i / TAIL_SAMPLES),
    });
  }
  for (const s of samples) {
    const x = s.dx + s.w * -s.sin;
    const y = s.dy + s.w * s.cos;
    path += `L ${x.toFixed(2)} ${y.toFixed(2)} `;
  }
  for (let i = samples.length - 1; i >= 0; i--) {
    const s = samples[i]!;
    const x = s.dx + s.w * s.sin;
    const y = s.dy + s.w * -s.cos;
    path += `L ${x.toFixed(2)} ${y.toFixed(2)} `;
  }
  path += 'Z';
  return path;
}

function buildFilter(blurPx: number, shadowAlpha: number, shadowColor: string): string {
  const parts = [`blur(${blurPx}px)`];
  if (shadowAlpha > 0) {
    parts.push(`drop-shadow(0 0 ${Math.max(8, blurPx * 0.8)}px ${withColorAlpha(shadowColor, shadowAlpha * 0.7)})`);
    parts.push(`drop-shadow(0 0 ${Math.max(20, blurPx * 1.6)}px ${withColorAlpha(shadowColor, shadowAlpha * 0.45)})`);
  }
  return parts.join(' ');
}

function withColorAlpha(color: string, alpha: number): string {
  const pct = Math.round(Math.max(0, Math.min(1, alpha)) * 100);
  return `color-mix(in srgb, ${color} ${pct}%, transparent)`;
}

export const TwoDropsBg: React.FC<TwoDropsBgProps> = (props) => {
  const frame = useCurrentFrame();
  const { width: W, height: H, fps } = useVideoConfig();
  const elapsed = frame / fps;
  const period = Math.max(0.5, props.lapPeriod);
  const baseT = elapsed / period;

  let lifecycleOpacity = 1;
  if (!props.infiniteLoop) {
    const totalFrames = Math.round(period * fps * Math.max(1, props.loops));
    const fadeFrames = fadeFramesFor(period, fps);
    const fadeOutStart = totalFrames - fadeFrames;
    if (frame < fadeFrames) {
      lifecycleOpacity = smoothstep(frame / fadeFrames);
    } else if (frame >= fadeOutStart) {
      lifecycleOpacity = 1 - smoothstep((frame - fadeOutStart) / fadeFrames);
    }
  }
  const effectiveOpacity = props.opacity * lifecycleOpacity;

  const palette = useMemo(() => cornerCyclePalette(props.primary), [props.primary]);
  // Light-bg variant: each layer has its own derived color + opacity (sandbox-
  // tuned). Dark-bg variant keeps the original role-based palette + the
  // hardcoded opacities in LAYER_STRUCTURE.
  const lightLayers = useMemo(() => twoDropsLightLayers(props.primary), [props.primary]);
  const lightShadow = useMemo(() => twoDropsLightShadow(props.primary), [props.primary]);
  // Screen blend lights up against dark; on a light background the drops
  // disappear. Pick the blend mode based on perceived background lightness.
  const background = props.lightMode ? '#FAFAF7' : '#000000';
  const blendMode: 'screen' | 'multiply' = props.lightMode ? 'multiply' : 'screen';

  return (
    <AbsoluteFill style={{ background, overflow: 'hidden' }}>
      {Array.from({ length: DROP_COUNT }, (_, di) => {
        const Wovh = W + 2 * OVERHANG;
        const Hovh = H + 2 * OVERHANG;
        const t = baseT + PHASE_OFFSETS[di]!;
        const headEasedT = easedPerimeterT(t, Wovh, Hovh, CORNER_RADIUS, CORNER_EASE);
        const head = perimeterPoint(headEasedT, Wovh, Hovh, CORNER_RADIUS);
        const tx = head.x - OVERHANG - SVG_HALF;
        const ty = head.y - OVERHANG - SVG_HALF;
        return (
          <React.Fragment key={di}>
            {LAYER_STRUCTURE.map((layer, li) => {
              const R = HEAD_RADIUS * layer.scale;
              const tailLengthPx = R * TAIL_LENGTH_MULT;
              const d = buildDropPath(Wovh, Hovh, headEasedT, head, R, tailLengthPx);
              const shadowAlpha = Math.max(0, Math.min(1, layer.shadow));
              // On dark backgrounds (screen blend) the outer layers are
              // dark and the core is bright  -  they additively glow. On
              // light backgrounds (multiply blend) we need the inverse:
              // outer layers nearly white so they barely tint, core dark
              // red so it reads as a deep centre. Same palette entries,
              // remapped per role.
              const lightLayer = lightLayers[li];
              const color = props.lightMode
                ? lightLayer?.color ?? '#ffffff'
                : palette[layer.role];
              const layerOpacity = props.lightMode
                ? lightLayer?.opacity ?? layer.opacity
                : layer.opacity;
              const filter = buildFilter(
                layer.blur,
                shadowAlpha,
                props.lightMode ? lightShadow : palette.shadowColor,
              );
              return (
                <svg
                  key={li}
                  width={SVG_HALF * 2}
                  height={SVG_HALF * 2}
                  viewBox={`-${SVG_HALF} -${SVG_HALF} ${SVG_HALF * 2} ${SVG_HALF * 2}`}
                  style={{
                    position: 'absolute',
                    left: 0,
                    top: 0,
                    overflow: 'visible',
                    pointerEvents: 'none',
                    opacity: layerOpacity * effectiveOpacity,
                    filter,
                    mixBlendMode: blendMode,
                    transform: `translate(${tx}px, ${ty}px)`,
                  }}
                >
                  <path d={d} fill={color} />
                </svg>
              );
            })}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

