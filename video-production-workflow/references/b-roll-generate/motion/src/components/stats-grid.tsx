'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library copy of the "Stats grid" launch tile. Wraps the canonical Stage
// from `_components/landing/stats-cards/core` and tints both the Grainient
// backdrop and the accent colour from a single `primary` knob.
//
// The accent colour rides through the live Stage via the
// `--cv-stack-accent` CSS variable (the live `ACCENT` constant resolves
// to `var(--cv-stack-accent, #F04E23)`). Setting the var on this
// wrapper's root recolours every stroke/fill/text inside the cards. A
// handful of low-alpha rgba(...) glows in the live source still read as
// the LP's orange because they're inline literals  -  the visible card
// chrome (numbers, strokes, button fills, chart paths) all swap.
// ============================================================================

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import {
  Stage as StatsStage,
  DEFAULT_BEATS,
  STAGE as STATS_SIZE,
  FPS,
} from '../_upstream/stats-cards/core';
import { Grainient } from '../_upstream/Grainient';

export type StatsGridProps = {
  primary: string;
  color1: string;
  color2: string;
  color3: string;
};

const DEFAULT_PRIMARY = '#F04E23';

function hexToHsl(hex: string): { h: number; s: number; l: number } {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return { h: 0, s: 0, l: 0.5 };
  const r = parseInt(m[1]!, 16) / 255;
  const g = parseInt(m[2]!, 16) / 255;
  const b = parseInt(m[3]!, 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  let h = 0;
  let s = 0;
  if (d !== 0) {
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)); break;
      case g: h = ((b - r) / d + 2); break;
      case b: h = ((r - g) / d + 4); break;
    }
    h /= 6;
  }
  return { h, s, l };
}
function hslToHex(h: number, s: number, l: number): string {
  const hue2rgb = (p: number, q: number, t: number): number => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  let r: number, g: number, b: number;
  if (s === 0) {
    r = g = b = l;
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }
  const to = (v: number) =>
    Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0');
  return `#${to(r)}${to(g)}${to(b)}`;
}

const GR_DELTAS = [
  { dH: 0, dS: 0, dL: 0 },
  { dH: 12 / 360, dS: 0.13, dL: -0.16 },
  { dH: 13 / 360, dS: 0.13, dL: -0.04 },
];

export function deriveStatsGridPalette(primaryHex: string): {
  color1: string; color2: string; color3: string;
} {
  const { h, s, l } = hexToHsl(primaryHex);
  const clamp = (v: number) => Math.max(0, Math.min(1, v));
  const wrap = (v: number) => ((v % 1) + 1) % 1;
  const shift = ({ dH, dS, dL }: { dH: number; dS: number; dL: number }) =>
    hslToHex(wrap(h + dH), clamp(s + dS), clamp(l + dL));
  return {
    color1: shift(GR_DELTAS[0]!),
    color2: shift(GR_DELTAS[1]!),
    color3: shift(GR_DELTAS[2]!),
  };
}

const SEEDED = deriveStatsGridPalette(DEFAULT_PRIMARY);

export const StatsGridDefaults: StatsGridProps = {
  primary: DEFAULT_PRIMARY,
  ...SEEDED,
};

// One loop = the live Stage's totalFrames beat (frame 0 and totalFrames
// state match by design, so the playhead-driven reveal/exit wraps
// cleanly). Grainient underneath loops on its own 8s cycle.
const LOOP_FRAMES = DEFAULT_BEATS.totalFrames;
const LOOP_SECONDS = LOOP_FRAMES / FPS;

// Snap the idle float period so an integer number of sine cycles fits
// inside one loop  -  otherwise tSec wraps from (LOOP_SECONDS) back to 0
// mid-cycle and every card jumps vertically by ~floatAmplitude px. Same
// trick the floating-stack render composition uses for its loop edge.
function snapFloatPeriod(originalPeriod: number, loopSeconds: number): number {
  const cycles = Math.max(1, Math.round(loopSeconds / Math.max(0.1, originalPeriod)));
  return loopSeconds / cycles;
}
const LIBRARY_BEATS = {
  ...DEFAULT_BEATS,
  floatPeriod: snapFloatPeriod(DEFAULT_BEATS.floatPeriod, LOOP_SECONDS),
};

export const StatsGridMeta = {
  width: STATS_SIZE,
  height: STATS_SIZE,
  fps: FPS,
  durationFrames: LOOP_FRAMES,
};

export const computeStatsGridDuration = (): number => LOOP_FRAMES;

export const StatsGrid: React.FC<StatsGridProps> = ({
  primary,
  color1, color2, color3,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tSec = frame / fps;
  return (
    <AbsoluteFill
      style={{
        background: '#0d0d0d',
        // Drives `--cv-stack-accent` on the descendant Stage. Live source
        // reads `var(--cv-stack-accent, #F04E23)` everywhere ACCENT used
        // to be a literal hex, so this single declaration tints all
        // strokes, fills, text, and button surfaces inside the cards.
        ['--cv-stack-accent' as string]: primary,
      } as React.CSSProperties}
    >
      <Grainient color1={color1} color2={color2} color3={color3} tSecOverride={tSec} />
      <StatsStage playhead={frame} beats={LIBRARY_BEATS} tSecOverride={tSec} />
    </AbsoluteFill>
  );
};
