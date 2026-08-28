'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library's own copy of the cascading-text composition. Words enter from the
// right with an ease-in-out bezier, drift left continuously, and the camera
// zooms out as the line grows past the third word so longer sentences stay
// readable. Each word fades from `primary` to white shortly after landing.
//
// Per the library convention, only one "highlight" knob (primary) is exposed,
// plus the editable text and two layout handles (finalZoom, startOffset).
// All timing and motion constants are tuned in the sandbox and baked here.
//
// Imports: react, remotion. NO @curvable/shared or per-project compositions.
// Any change here is an intentional library design change.
// ============================================================================

import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';

const STAGE_W = 1920;
const STAGE_H = 1080;
const FPS = 60;

// Baked-in tuning (from the sandbox-saved JSON; "This is it!" 2026-05-15).
const ENTRANCE_DURATION = 1.8;
const APPEAR_INTERVAL = 0.35;
const FONT_SIZE = 120;
const SPACE_WIDTH_PX = -78;
const ZOOM_AFTER_WORD = 3;
// Multi-step zoom: each word's zoom is gated to the back half of its
// entrance so steps read as distinct beats.
const ZOOM_WINDOW_START_MULTI = 0.46;
// Single-zoom mode: all per-word windows span the full entrance so they
// overlap into one continuous curve.
const ZOOM_WINDOW_START_SINGLE = 0;
const ZOOM_WINDOW_END = 1.0;
const ZOOM_DELAY = 0;
const COLOR_FADE_DELAY = 1.2;
const HOLD_SECONDS = 0.35;
const EXIT_FADE_DURATION = 0.4;
const MIN_ZOOM_FLOOR = 0.15;

function measureWordsWithCanvas(words: string[]): number[] {
  const fallback = (w: string) => w.length * FONT_SIZE * 0.55;
  if (typeof document === 'undefined') return words.map(fallback);
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return words.map(fallback);
  ctx.font = `600 ${FONT_SIZE}px system-ui, -apple-system, sans-serif`;
  return words.map((w) => ctx.measureText(w).width);
}

function settleTime(N: number, fadeDuration: number): number {
  if (N === 0) return 0;
  const lastTEnter = (N - 1) * APPEAR_INTERVAL;
  const steps = Math.max(0, N - ZOOM_AFTER_WORD);
  return Math.max(
    lastTEnter + ENTRANCE_DURATION,
    lastTEnter + COLOR_FADE_DELAY + fadeDuration,
    steps > 0 ? lastTEnter + ZOOM_WINDOW_END * ENTRANCE_DURATION + ZOOM_DELAY : 0,
  );
}
const BEZIER = { p1x: 0.76, p1y: 0, p2x: 0.24, p2y: 1 } as const;
// Light/dark mode palette pair. Switching modes only swaps the bg + resting
// text color  -  the accent color knob stays user-controlled.
const DARK_BG = '#000000';
const DARK_RESTING = '#ffffff';
const LIGHT_BG = '#FAFAF7';
const LIGHT_RESTING = '#0B0B12';

export type CascadingTextProps = {
  primary: string;
  text: string;
  padding: number;
  // 0 = no fade (word stays at primary throughout); otherwise the fade
  // duration in seconds. The fade always starts at COLOR_FADE_DELAY after
  // each word's tEnter.
  fadeDuration: number;
  // false = multi-step zoom (each word past `zoomAfterWord` fires its own
  // discrete zoom beat); true = a single continuous zoom curve where all
  // contributions overlap their full entrance.
  oneZoom: boolean;
  // false = dark mode (default): black bg, white resting text. true = light
  // mode: light bg, dark resting text. Accent color is the user's `primary`
  // in both modes.
  lightMode: boolean;
};

export const CascadingTextDefaults: CascadingTextProps = {
  primary: '#F04E23',
  text: 'Curvable makes launch videos in minutes, not hours',
  padding: 260,
  fadeDuration: 0.3,
  oneZoom: true,
  lightMode: false,
};

export const CascadingTextMeta = {
  width: STAGE_W,
  height: STAGE_H,
  fps: FPS,
};

function splitWords(text: string): string[] {
  return text.trim().split(/\s+/).filter(Boolean);
}

export const computeCascadingTextDuration = (p: Pick<CascadingTextProps, 'text' | 'fadeDuration'>): number => {
  const N = splitWords(p.text).length;
  if (N === 0) return Math.max(1, Math.round(EXIT_FADE_DURATION * FPS));
  const cut = settleTime(N, p.fadeDuration ?? CascadingTextDefaults.fadeDuration) + HOLD_SECONDS;
  return Math.max(1, Math.round((cut + EXIT_FADE_DURATION) * FPS));
};

function bezierXY(t: number, p1x: number, p1y: number, p2x: number, p2y: number): [number, number] {
  const u = 1 - t;
  const x = 3 * u * u * t * p1x + 3 * u * t * t * p2x + t * t * t;
  const y = 3 * u * u * t * p1y + 3 * u * t * t * p2y + t * t * t;
  return [x, y];
}

function bezierEase(progress: number, p1x: number, p1y: number, p2x: number, p2y: number): number {
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 28; i++) {
    const mid = (lo + hi) / 2;
    const [x] = bezierXY(mid, p1x, p1y, p2x, p2y);
    if (x < progress) lo = mid;
    else hi = mid;
  }
  const [, y] = bezierXY((lo + hi) / 2, p1x, p1y, p2x, p2y);
  return y;
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const n = parseInt(full, 16);
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

function lerpHex(a: string, b: string, t: number): string {
  const pa = hexToRgb(a);
  const pb = hexToRgb(b);
  const tt = Math.max(0, Math.min(1, t));
  const r = Math.round(pa.r + (pb.r - pa.r) * tt);
  const g = Math.round(pa.g + (pb.g - pa.g) * tt);
  const bl = Math.round(pa.b + (pb.b - pa.b) * tt);
  return `rgb(${r}, ${g}, ${bl})`;
}

export const CascadingText: React.FC<CascadingTextProps> = ({
  primary,
  text,
  padding,
  fadeDuration,
  oneZoom,
  lightMode,
}) => {
  const zoomWindowStart = oneZoom ? ZOOM_WINDOW_START_SINGLE : ZOOM_WINDOW_START_MULTI;
  const backgroundColor = lightMode ? LIGHT_BG : DARK_BG;
  const restingColor = lightMode ? LIGHT_RESTING : DARK_RESTING;
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  const totalDurationSec = durationInFrames / fps;
  const exitFadeStartT = totalDurationSec - EXIT_FADE_DURATION;
  const exitFadeMul =
    t > exitFadeStartT
      ? Math.max(0, 1 - (t - exitFadeStartT) / EXIT_FADE_DURATION)
      : 1;
  const words = useMemo(() => splitWords(text), [text]);
  const N = words.length;

  // Canvas-measured widths in composition coords (DOM measurement returns
  // post-scale screen pixels inside the Player and would collapse layout).
  const widths = useMemo(() => measureWordsWithCanvas(words), [words]);
  const widthOf = (i: number) => widths[i] ?? words[i]!.length * FONT_SIZE * 0.55;

  // Derive everything from `padding`: compute the line's natural width, the
  // zoom required for the line to fit with that padding on both sides, the
  // per-word zoom step that lands exactly at finalZoom on the last step,
  // the cut time (when all motion has settled), and the startOffset that
  // puts the line's center at the viewport center exactly at cut time.
  const lineWidth = useMemo(() => {
    if (widths.length === 0) return 1;
    let w = 0;
    for (let i = 0; i < widths.length; i++) {
      w += widths[i] ?? 0;
      if (i > 0) w += SPACE_WIDTH_PX;
    }
    return Math.max(1, w);
  }, [widths]);

  const numSteps = Math.max(0, N - ZOOM_AFTER_WORD);
  const tCut = settleTime(N, fadeDuration) + HOLD_SECONDS;

  // Fix word 0 at viewport center at t=0. Each word's drift starts at its
  // own tEnter, so the visible line spreads by baseSpeed × APPEAR_INTERVAL
  // between adjacent words. Account for that spread when deriving baseSpeed
  // (so the line midpoint lands on viewport center at tCut) and finalZoom.
  const startOffset = STAGE_W / 2;
  const denom = 2 * tCut - (N - 1) * APPEAR_INTERVAL;
  const baseSpeed =
    N <= 1 ? (tCut > 0 ? lineWidth / (2 * tCut) : 0) : denom > 0.001 ? lineWidth / denom : 0;
  const actualLineWidth = lineWidth + Math.max(0, N - 1) * baseSpeed * APPEAR_INTERVAL;

  const desiredFinalZoom = (STAGE_W - 2 * padding) / actualLineWidth;
  const finalZoom =
    N <= ZOOM_AFTER_WORD || desiredFinalZoom >= 1
      ? Math.min(1, Math.max(MIN_ZOOM_FLOOR, desiredFinalZoom))
      : Math.max(MIN_ZOOM_FLOOR, desiredFinalZoom);
  const zoomStep = numSteps > 0 ? (1 - finalZoom) / numSteps : 0;

  // Each zoom step has its own time window in the middle of its word's
  // entrance (ZOOM_WINDOW_START..ZOOM_WINDOW_END as fractions of
  // ENTRANCE_DURATION). Contributions accumulate independently so steps
  // don't overwrite each other  -  each step zooms by exactly `zoomStep`
  // during its window, with rest gaps between consecutive steps.
  const camScale = useMemo(() => {
    if (numSteps === 0 || zoomStep === 0) return 1;
    const span = Math.max(0.001, ZOOM_WINDOW_END - zoomWindowStart);
    let totalZoomOut = 0;
    for (let i = ZOOM_AFTER_WORD; i < N; i++) {
      const tEnter = i * APPEAR_INTERVAL;
      const winStart = tEnter + zoomWindowStart * ENTRANCE_DURATION + ZOOM_DELAY;
      const winEnd = tEnter + ZOOM_WINDOW_END * ENTRANCE_DURATION + ZOOM_DELAY;
      if (t >= winEnd) {
        totalZoomOut += zoomStep;
      } else if (t > winStart) {
        const localP = (t - winStart) / (ENTRANCE_DURATION * span);
        const eased = bezierEase(localP, BEZIER.p1x, BEZIER.p1y, BEZIER.p2x, BEZIER.p2y);
        totalZoomOut += zoomStep * eased;
      }
    }
    return Math.max(finalZoom, 1 - totalZoomOut);
  }, [t, N, finalZoom, zoomStep, numSteps, zoomWindowStart]);

  // Words enter from the right edge of the widest viewport possible (at
  // finalZoom) so a later zoom can never reveal them prematurely.
  const enterStartX = Math.max(
    (STAGE_W * (1 + 1 / Math.max(0.001, finalZoom))) / 2 + 80,
    (widths.length > 0 ? startOffset + lineWidth : STAGE_W) + 80,
  );

  return (
    <AbsoluteFill style={{ background: backgroundColor, overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transformOrigin: '50% 50%',
          transform: `scale(${camScale})`,
        }}
      >
        {words.map((w, i) => {
          const tEnter = i * APPEAR_INTERVAL;
          if (t < tEnter) return null;
          let slot = startOffset;
          for (let j = 0; j < i; j++) slot += widthOf(j) + SPACE_WIDTH_PX;
          const naturalX = slot - baseSpeed * (t - tEnter);
          const elapsed = t - tEnter;
          let x: number;
          let opacity = 1;
          if (elapsed >= ENTRANCE_DURATION) {
            x = naturalX;
          } else {
            const p = elapsed / ENTRANCE_DURATION;
            const eased = bezierEase(p, BEZIER.p1x, BEZIER.p1y, BEZIER.p2x, BEZIER.p2y);
            x = enterStartX + eased * (naturalX - enterStartX);
            opacity = p;
          }
          let color: string;
          if (fadeDuration <= 0 || t < tEnter + COLOR_FADE_DELAY) {
            color = primary;
          } else {
            const cp = (t - tEnter - COLOR_FADE_DELAY) / fadeDuration;
            color = lerpHex(primary, restingColor, cp);
          }
          return (
            <div
              key={i}
              style={{
                position: 'absolute',
                top: STAGE_H / 2,
                left: 0,
                transform: `translate(${x}px, -50%)`,
                fontSize: FONT_SIZE,
                fontWeight: 600,
                whiteSpace: 'nowrap',
                color,
                opacity: opacity * exitFadeMul,
                fontFamily: 'system-ui, -apple-system, sans-serif',
              }}
            >
              {w}
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
