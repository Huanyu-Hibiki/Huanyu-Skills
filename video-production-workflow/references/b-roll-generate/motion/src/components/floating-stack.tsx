'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library copy of the "Floating stack" launch tile. Renders the canonical
// Stage from `_components/landing/floating-stack/core` (LP-owned, stable)
// over a Grainient backdrop. Both the backdrop and the slab glow tints
// derive from the global `primary` knob, mirroring the way the Grainient
// preset derives its three shades from one brand colour.
//
// Per-project sessions must NEVER edit this file. Imports come only from
// LP-owned sources and the frozen `../palettes` helpers  -  no per-project
// composition dependencies.
// ============================================================================

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import {
  DEFAULT_STATE,
  Stage as FloatingStackStage,
  STAGE as STACK_SIZE,
  type StackState,
} from '../_upstream/floating-stack/core';
import { Grainient } from '../_upstream/Grainient';

export type FloatingStackProps = {
  primary: string;
  // Three Grainient shades derived from primary. The registry's
  // derivePaletteFromPrimary keeps these in sync with the global brand
  // colour; users can still nudge them by hand and the nudge sticks
  // until the next time `primary` changes.
  color1: string;
  color2: string;
  color3: string;
  // Three slab-glow shades. Same derivation contract.
  glowTop: string;
  glowSide: string;
  glowBottom: string;
  // Cursor3D recolour. Drives the same `--cv-cursor-*` CSS variables the
  // Prompt-input library wrapper sets  -  Cursor3D reads them with the LP
  // signoff hexes as fallbacks, so unaffected callers stay identical.
  cursorTop: string;
  cursorBot: string;
  cursorStack: [string, string, string, string, string, string, string];
};

const DEFAULT_PRIMARY = '#F04E23';

// HSL shift helpers (mirror of grainient-bg's). Kept local so this frozen
// file owns its derivation and never reaches into a sibling component.
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

// Grainient: same deltas as the standalone Grainient preset, measured from
// #F04E23 → (#F04E23, #C04F00, #FF6D00). Re-derived here so this file owns
// its palette and stays decoupled.
const GR_DELTAS = [
  { dH: 0, dS: 0, dL: 0 },
  { dH: 12 / 360, dS: 0.13, dL: -0.16 },
  { dH: 13 / 360, dS: 0.13, dL: -0.04 },
];

// Slab glow: dark/mid/dim trio measured from sign-off
// (#F04E23 → glowTop #da3d16, glowSide #ae2f19, glowBottom #3F0F05).
// Hue stays exactly on primary; saturation rises and lightness drops as
// you descend the stack so the glow reads as a vertical depth cue.
const GLOW_DELTAS = {
  top:    { dH: 0, dS: 0.06,  dL: -0.07 },
  side:   { dH: 0, dS: 0.10,  dL: -0.18 },
  bottom: { dH: 0, dS: 0.16,  dL: -0.36 },
};

// Cursor3D recolour pack. Matches the deltas used by the Prompt-input
// library wrapper so the cursor reads the same shade family across both
// component tiles. Floating-stack's Stage instantiates Cursor3D inside it
//  -  Cursor3D reads its colours from CSS variables on the nearest
// ancestor, so this wrapper just needs to set them.
const CURSOR_TOP_DELTA = { dH: 2 / 360, dS: -0.04, dL:  0.15 };
const CURSOR_BOT_DELTA = { dH: 0,       dS:  0.08, dL: -0.18 };
const CURSOR_STACK_DELTAS: { dH: number; dS: number; dL: number }[] = [
  { dH: -2 / 360, dS: 0.16, dL: -0.39 },
  { dH: -2 / 360, dS: 0.18, dL: -0.34 },
  { dH: -1 / 360, dS: 0.17, dL: -0.29 },
  { dH:  0,       dS: 0.15, dL: -0.24 },
  { dH:  0,       dS: 0.13, dL: -0.19 },
  { dH:  0,       dS: 0.11, dL: -0.13 },
  { dH:  0,       dS: 0.09, dL: -0.07 },
];

export function deriveFloatingStackPalette(primaryHex: string): {
  color1: string; color2: string; color3: string;
  glowTop: string; glowSide: string; glowBottom: string;
  cursorTop: string; cursorBot: string;
  cursorStack: [string, string, string, string, string, string, string];
} {
  const { h, s, l } = hexToHsl(primaryHex);
  const clamp = (v: number) => Math.max(0, Math.min(1, v));
  const wrap = (v: number) => ((v % 1) + 1) % 1;
  const shift = ({ dH, dS, dL }: { dH: number; dS: number; dL: number }) =>
    hslToHex(wrap(h + dH), clamp(s + dS), clamp(l + dL));
  const stack = CURSOR_STACK_DELTAS.map(shift) as [
    string, string, string, string, string, string, string,
  ];
  return {
    color1: shift(GR_DELTAS[0]!),
    color2: shift(GR_DELTAS[1]!),
    color3: shift(GR_DELTAS[2]!),
    glowTop: shift(GLOW_DELTAS.top),
    glowSide: shift(GLOW_DELTAS.side),
    glowBottom: shift(GLOW_DELTAS.bottom),
    cursorTop: shift(CURSOR_TOP_DELTA),
    cursorBot: shift(CURSOR_BOT_DELTA),
    cursorStack: stack,
  };
}

const SEEDED = deriveFloatingStackPalette(DEFAULT_PRIMARY);

export const FloatingStackDefaults: FloatingStackProps = {
  primary: DEFAULT_PRIMARY,
  ...SEEDED,
};

const FPS = 30;
const LOOP_SECONDS = 10;
const LOOP_FRAMES = LOOP_SECONDS * FPS;

export const FloatingStackMeta = {
  width: STACK_SIZE,
  height: STACK_SIZE,
  fps: FPS,
  durationFrames: LOOP_FRAMES,
};

export const computeFloatingStackDuration = (): number => LOOP_FRAMES;

// Snap float period to a clean divisor of LOOP_SECONDS so the sine wave
// wraps to 0 at the loop boundary (no jump on re-loop). Live default 3.1s
// → 3 cycles in 10s → period 3.333s, visually indistinguishable.
function snapFloatPeriod(originalPeriod: number, loopSeconds: number): number {
  const cycles = Math.max(1, Math.round(loopSeconds / Math.max(0.1, originalPeriod)));
  return loopSeconds / cycles;
}

export const FloatingStack: React.FC<FloatingStackProps> = ({
  primary,
  color1, color2, color3,
  glowTop, glowSide, glowBottom,
  cursorTop, cursorBot, cursorStack,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tSec = frame / fps;
  const state: StackState = {
    ...DEFAULT_STATE,
    floatPeriod: snapFloatPeriod(DEFAULT_STATE.floatPeriod, LOOP_SECONDS),
    glowTop,
    glowSide,
    glowBottom,
  };
  // Cursor3D inside the Stage reads these vars with the LP signoff
  // hexes as fallbacks. Setting them on the wrapper recolours the whole
  // 7-layer extrusion stack + the visible front-face gradient.
  const cursorVars: React.CSSProperties = {
    ['--cv-cursor-top' as string]: cursorTop,
    ['--cv-cursor-mid' as string]: primary,
    ['--cv-cursor-bot' as string]: cursorBot,
    ['--cv-cursor-l0' as string]: cursorStack[0],
    ['--cv-cursor-l1' as string]: cursorStack[1],
    ['--cv-cursor-l2' as string]: cursorStack[2],
    ['--cv-cursor-l3' as string]: cursorStack[3],
    ['--cv-cursor-l4' as string]: cursorStack[4],
    ['--cv-cursor-l5' as string]: cursorStack[5],
    ['--cv-cursor-l6' as string]: cursorStack[6],
  };
  return (
    <AbsoluteFill style={{ background: '#0d0d0d', ...cursorVars }}>
      <Grainient color1={color1} color2={color2} color3={color3} tSecOverride={tSec} />
      <FloatingStackStage state={state} tSecOverride={tSec} />
    </AbsoluteFill>
  );
};
