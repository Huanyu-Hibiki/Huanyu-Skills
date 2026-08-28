'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library's own copy of the ellipse-bloom composition. Per-project agents
// must NOT edit this file. They work on per-project compositions only.
//
// Palette helpers come from `../palettes` (frozen). Do NOT import from
// `@curvable/shared` or the project compositions directory.
//
// Sourced from /sandbox/ellipse-bloom defaults  -  two layers, inner = primary
// highlight, outer = derived darker shade. Hue stays locked to `primary`.
// ============================================================================

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { ellipseBloomPalette, ellipseBloomPaletteLight } from '../palettes';

export type EllipseBloomProps = {
  primary: string;
  lightMode: boolean;
};

export const EllipseBloomDefaults: EllipseBloomProps = {
  primary: '#F04E23',
  lightMode: false,
};

const FPS = 60;
const STAGE_W = 1920;
const STAGE_H = 1080;

// Frozen timing/geometry baked from the sandbox JSON the user signed off on.
// `core` is the inner highlight layer; `outer` is the larger, more blurred
// surrounding ring. Both use derived shades of the primary so a single color
// knob drives the whole composition.
const FADE_IN_DELAY_S = 0.1;
const FADE_IN_DURATION_S = 0.3;
const GROW_DELAY_S = 0;
const GROW_DURATION_S = 0.6;
const START_SCALE = 0.005;
const END_SCALE = 4;
const GLOBAL_WIDTH = 1210;
const GLOBAL_HEIGHT = 720;

const BEZIER = { p1x: 0.841, p1y: 0.014, p2x: 0.268, p2y: 0.877 };

type LayerSpec = {
  role: 'outer' | 'core';
  opacity: number;
  blur: number;
  widthMul: number;
  heightMul: number;
  delay: number;
  offsetX: number;
  offsetY: number;
};

const LAYERS: LayerSpec[] = [
  { role: 'outer', opacity: 0.98, blur: 78, widthMul: 0.78, heightMul: 0.78, delay: 0.12, offsetX: 0, offsetY: 0 },
  { role: 'core',  opacity: 1.00, blur: 72, widthMul: 0.91, heightMul: 0.90, delay: 0.16, offsetX: 0, offsetY: 0 },
];

const HOLD_S = 0.8;
const EXIT_FADE_S = 0.4;
const MAX_LAYER_DELAY = LAYERS.reduce((m, l) => Math.max(m, l.delay), 0);
const SETTLE_S = FADE_IN_DELAY_S + Math.max(FADE_IN_DURATION_S, GROW_DELAY_S + MAX_LAYER_DELAY + GROW_DURATION_S);
const TOTAL_DURATION_S = SETTLE_S + HOLD_S + EXIT_FADE_S;
const TOTAL_FRAMES = Math.max(1, Math.round(TOTAL_DURATION_S * FPS));

export const EllipseBloomMeta = {
  width: STAGE_W,
  height: STAGE_H,
  fps: FPS,
  durationFrames: TOTAL_FRAMES,
};

export const computeEllipseBloomDuration = (): number => TOTAL_FRAMES;

const bezierXY = (t: number, p1x: number, p1y: number, p2x: number, p2y: number): [number, number] => {
  const u = 1 - t;
  const x = 3 * u * u * t * p1x + 3 * u * t * t * p2x + t * t * t;
  const y = 3 * u * u * t * p1y + 3 * u * t * t * p2y + t * t * t;
  return [x, y];
};

const bezierEase = (progress: number): number => {
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 28; i++) {
    const mid = (lo + hi) / 2;
    const [x] = bezierXY(mid, BEZIER.p1x, BEZIER.p1y, BEZIER.p2x, BEZIER.p2y);
    if (x < progress) lo = mid;
    else hi = mid;
  }
  const [, y] = bezierXY((lo + hi) / 2, BEZIER.p1x, BEZIER.p1y, BEZIER.p2x, BEZIER.p2y);
  return y;
};

const transparentize = (color: string): string => {
  // Both palette outputs are oklch(...) strings; color-mix is the cleanest
  // way to fade them to fully transparent without re-parsing the OKLCH.
  return `color-mix(in oklch, ${color} 0%, transparent)`;
};

export const EllipseBloom: React.FC<EllipseBloomProps> = ({ primary, lightMode }) => {
  const background = lightMode ? '#FAFAF7' : '#0a0a0a';
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const palette = lightMode ? ellipseBloomPaletteLight(primary) : ellipseBloomPalette(primary);

  const fadeMul = (() => {
    if (t < FADE_IN_DELAY_S) return 0;
    if (t >= FADE_IN_DELAY_S + FADE_IN_DURATION_S) return 1;
    return (t - FADE_IN_DELAY_S) / Math.max(0.0001, FADE_IN_DURATION_S);
  })();

  const exitFadeStartT = TOTAL_DURATION_S - EXIT_FADE_S;
  const exitFadeMul =
    t > exitFadeStartT ? Math.max(0, 1 - (t - exitFadeStartT) / EXIT_FADE_S) : 1;

  return (
    <AbsoluteFill style={{ backgroundColor: background, overflow: 'hidden' }}>
      {LAYERS.map((layer, i) => {
        const tStart = FADE_IN_DELAY_S + GROW_DELAY_S + layer.delay;
        let s: number;
        if (t <= tStart) s = START_SCALE;
        else if (t >= tStart + GROW_DURATION_S) s = END_SCALE;
        else {
          const p = (t - tStart) / Math.max(0.0001, GROW_DURATION_S);
          s = START_SCALE + (END_SCALE - START_SCALE) * bezierEase(p);
        }
        const w = GLOBAL_WIDTH * layer.widthMul;
        const h = GLOBAL_HEIGHT * layer.heightMul;
        const color = layer.role === 'core' ? palette.core : palette.outer;
        const fade = transparentize(color);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: STAGE_W / 2,
              top: STAGE_H / 2,
              width: w,
              height: h,
              marginLeft: -w / 2,
              marginTop: -h / 2,
              borderRadius: '50%',
              background: `radial-gradient(ellipse at 50% 50%, ${color} 0%, ${color} 45%, ${fade} 100%)`,
              opacity: layer.opacity * fadeMul * exitFadeMul,
              filter: layer.blur > 0 ? `blur(${layer.blur}px)` : undefined,
              transform: `translate(${layer.offsetX}px, ${layer.offsetY}px) scale(${s})`,
              transformOrigin: '50% 50%',
              willChange: 'transform, opacity',
              pointerEvents: 'none',
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
