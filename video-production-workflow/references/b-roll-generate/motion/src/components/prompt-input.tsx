'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library copy of the "Prompt input" launch tile. Wraps the canonical
// PromptInput scene from `_components/animations/prompt-input` over a
// Grainient backdrop, both tinted by the global library `primary`.
//
// Two derivations live here:
//   - Grainient color1/2/3: same three-shade recipe as the standalone
//     Grainient preset.
//   - bulbPrimary: a darker, more saturated shade of primary used for the
//     bulb's coloured halo behind the 3D dashboard.
//
// Note: the MiniDashboard inside the PromptInput scene reads CV.accent
// directly (JS constant) for the cursor + send-button colour. Recolouring
// those would require refactoring a composition shared with the Meet
// Curvable scene, so the library entry leaves them on the LP's brand
// orange. The visible BACKDROP (grainient + bulb halo) responds fully to
// the user's primary.
// ============================================================================

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import {
  PromptInput as PromptInputScene,
  PromptInputDefaults as SceneDefaults,
  PromptInputMeta as SceneMeta,
  computePromptInputDuration as computeSceneDuration,
} from '../_upstream/animations/prompt-input';
import { Grainient } from '../_upstream/Grainient';

export type PromptInputProps = {
  primary: string;
  color1: string;
  color2: string;
  color3: string;
  bulbPrimary: string;
  // Accent-coloured details inside the dashboard + cursor. Drive the
  // MiniDashboard / Cursor3D CSS variables (`--cv-md-accent`,
  // `--cv-md-accent-dark`, `--cv-cursor-*`) so the cursor stack, send
  // button, typing-flash glow and "Generating video…" bubble all follow
  // the global brand colour.
  accentDark: string;
  cursorTop: string;
  cursorBot: string;
  cursorStack: [string, string, string, string, string, string, string];
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
// Bulb shade: darker + slightly more saturated than primary. Measured from
// #F04E23 → #DC3A1A (the live PromptInputDefaults.bulbPrimary).
const BULB_DELTA = { dH: -2 / 360, dS: 0.06, dL: -0.06 };

// Accent-dark for the dashboard's send-button gradient bottom stop.
// Measured from #F04E23 → #b13816 in the live MiniDashboard linear-gradient.
const ACCENT_DARK_DELTA = { dH: -2 / 360, dS: 0.07, dL: -0.18 };

// Cursor gradient top/mid/bot stops. Measured from primary #F04E23 to the
// live Cursor3D gradient (#FF7A52 / #F04E23 / #B23914). Top is lighter,
// mid is primary, bot is darker.
const CURSOR_TOP_DELTA = { dH: 2 / 360,  dS: -0.04, dL:  0.15 };
const CURSOR_MID_DELTA = { dH: 0,        dS:  0,     dL:  0 };
const CURSOR_BOT_DELTA = { dH: 0,        dS:  0.08,  dL: -0.18 };

// 7-layer cursor extrusion: progressive lightness from l0 (deepest) to l6
// (closest to primary). dL ramps linearly. Measured against the live
// STACK_BASE colours, evenly distributed in HSL lightness space.
const CURSOR_STACK_DELTAS: { dH: number; dS: number; dL: number }[] = [
  { dH: -2 / 360, dS: 0.16, dL: -0.39 }, // l0
  { dH: -2 / 360, dS: 0.18, dL: -0.34 }, // l1
  { dH: -1 / 360, dS: 0.17, dL: -0.29 }, // l2
  { dH:  0,       dS: 0.15, dL: -0.24 }, // l3
  { dH:  0,       dS: 0.13, dL: -0.19 }, // l4
  { dH:  0,       dS: 0.11, dL: -0.13 }, // l5
  { dH:  0,       dS: 0.09, dL: -0.07 }, // l6
];

export function derivePromptInputPalette(primaryHex: string): {
  color1: string; color2: string; color3: string;
  bulbPrimary: string;
  accentDark: string;
  cursorTop: string;
  cursorBot: string;
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
    bulbPrimary: shift(BULB_DELTA),
    accentDark: shift(ACCENT_DARK_DELTA),
    cursorTop: shift(CURSOR_TOP_DELTA),
    cursorBot: shift(CURSOR_BOT_DELTA),
    cursorStack: stack,
  };
}

const SEEDED = derivePromptInputPalette(DEFAULT_PRIMARY);

export const PromptInputDefaults: PromptInputProps = {
  primary: DEFAULT_PRIMARY,
  ...SEEDED,
};

export const PromptInputMeta = {
  width: SceneMeta.width,
  height: SceneMeta.height,
  fps: SceneMeta.fps,
};

export const computePromptInputDuration = (): number =>
  computeSceneDuration(SceneDefaults);

export const PromptInput: React.FC<PromptInputProps> = ({
  primary,
  color1, color2, color3,
  bulbPrimary,
  accentDark,
  cursorTop, cursorBot, cursorStack,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // Variable bag drives every accent-coloured element that lives inside
  // the live MiniDashboard + Cursor3D. The fallbacks in those files keep
  // every other LP composition (Meet Curvable, per-project copies)
  // identical when no ancestor sets these vars.
  const vars: React.CSSProperties = {
    ['--cv-md-accent' as string]: primary,
    ['--cv-md-accent-dark' as string]: accentDark,
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
    <AbsoluteFill style={{ background: '#0d0d0d', ...vars }}>
      <Grainient color1={color1} color2={color2} color3={color3} tSecOverride={frame / fps} />
      <PromptInputScene {...SceneDefaults} bulbPrimary={bulbPrimary} />
    </AbsoluteFill>
  );
};
