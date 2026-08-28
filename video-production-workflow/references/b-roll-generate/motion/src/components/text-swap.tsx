'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library's own copy of the text-swap composition. Per-project agents must
// NOT edit this file. They work on per-project compositions only.
//
// Port from /sandbox/text-swap  -  user-signed-off JSON baked as constants
// below (transitionStart, transitionDuration, totalDuration, fontSize,
// fontFamily, fillStartAtRemovalFraction, removalWindowFraction,
// orangeFlashSec, glow layer shapes). The global `primary` knob drives both
// the orange flash colour and both glow layer colours, and `lightMode`
// swaps the canvas + text foreground.
//
// Algorithm:
//   - Word 1 renders in its natural typography. Letters disappear in random
//     pairs across the first 85% of the transition. The 80ms before a
//     letter disappears it flashes in `primary`.
//   - Word 2 renders centered on the same point. A word-2 letter is allowed
//     to appear iff its natural rect doesn't overlap any currently visible
//     (black OR orange) word-1 letter rect. The same 80ms after a letter
//     appears it shows in `primary` before resolving to the text colour.
//   - Two glow layers draw the same letter, scaled and blurred, behind each
//     letter while it's in its orange flash window.
// ============================================================================

import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';

export type TextSwapProps = {
  text1: string;
  text2: string;
  primary: string;
  lightMode: boolean;
};

export const TextSwapDefaults: TextSwapProps = {
  text1: 'Introducing',
  text2: 'Curvable.ai',
  primary: '#f04e23',
  lightMode: false,
};

const FPS = 60;
const STAGE_W = 1920;
const STAGE_H = 1080;

// Baked from the user-signed-off JSON.
const TRANSITION_START_SEC = 0.3;
const TRANSITION_DURATION_SEC = 0.6;
const TOTAL_DURATION_SEC = 1.6;
const FONT_SIZE = 160;
const FONT_FAMILY = "ui-sans-serif, system-ui, -apple-system, Helvetica Neue, sans-serif";
const FILL_START_AT_REMOVAL_FRACTION = 0.5;
const REMOVAL_WINDOW_FRACTION = 0.85;
const ORANGE_FLASH_SEC = 0.08;
const SEED = 1;

const TOTAL_FRAMES = Math.max(1, Math.round(TOTAL_DURATION_SEC * FPS));
const TRANSITION_START_FRAME = Math.round(TRANSITION_START_SEC * FPS);
const TRANSITION_END_FRAME = Math.round((TRANSITION_START_SEC + TRANSITION_DURATION_SEC) * FPS);
const ORANGE_FLASH_FRAMES = Math.max(1, Math.round(ORANGE_FLASH_SEC * FPS));

// Glow layers  -  opacity / size / blur are baked; colour comes from primary.
const GLOW_SHAPES: { opacity: number; sizeMul: number; blurPx: number }[] = [
  { opacity: 1, sizeMul: 0.98, blurPx: 10 },
  { opacity: 0.32, sizeMul: 1.45, blurPx: 26 },
];

const LIGHT_BG = '#FAFAF7';
const LIGHT_TEXT = '#0a0a0a';
const DARK_BG = '#0a0a0a';
const DARK_TEXT = '#FAFAF7';

export const TextSwapMeta = {
  width: STAGE_W,
  height: STAGE_H,
  fps: FPS,
  durationFrames: TOTAL_FRAMES,
};

export const computeTextSwapDuration = (): number => TOTAL_FRAMES;

// ---------------------------------------------------------------------------
// Internal helpers.
// ---------------------------------------------------------------------------

function mulberry32(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) | 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function hashString(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function shuffledIndices(n: number, rng: () => number): number[] {
  const a = Array.from({ length: n }, (_, i) => i);
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    const tmp = a[i]!;
    a[i] = a[j]!;
    a[j] = tmp;
  }
  return a;
}

type LetterRect = { x: number; w: number };
type WordLayout = { rects: LetterRect[]; total: number };

function computeLayout(text: string): WordLayout | null {
  if (typeof document === 'undefined') return null;
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;
  ctx.font = `${FONT_SIZE}px ${FONT_FAMILY}`;
  const widths: number[] = [];
  for (let i = 0; i < text.length; i++) widths.push(ctx.measureText(text[i]!).width);
  const total = widths.reduce((a, b) => a + b, 0);
  const rects: LetterRect[] = [];
  let x = -total / 2;
  for (let i = 0; i < text.length; i++) {
    rects.push({ x, w: widths[i]! });
    x += widths[i]!;
  }
  return { rects, total };
}

function rectsOverlap(a: LetterRect, b: LetterRect, eps = 0.5): boolean {
  return a.x + a.w > b.x + eps && b.x + b.w > a.x + eps;
}

type Schedule = {
  highlightAtFrame: (number | undefined)[];
  removeAtFrame: (number | undefined)[];
  placedAtFrame: (number | undefined)[];
  settleAtFrame: (number | undefined)[];
};

function buildSchedule(text1: string, text2: string, w1: WordLayout, w2: WordLayout): Schedule {
  const rng = mulberry32(SEED + hashString(text1) + hashString(text2));
  const removeOrder = shuffledIndices(text1.length, rng);
  const fillOrder = shuffledIndices(text2.length, rng);

  const total = Math.max(1, TRANSITION_END_FRAME - TRANSITION_START_FRAME);
  const removalWindow = total * REMOVAL_WINDOW_FRACTION;
  const fillStartOffset = removalWindow * FILL_START_AT_REMOVAL_FRACTION;

  const removeEventCount = Math.ceil(text1.length / 2);

  type Ev =
    | { type: 'highlight'; frame: number; indices: number[] }
    | { type: 'remove'; frame: number; indices: number[] }
    | { type: 'fill'; frame: number };
  const events: Ev[] = [];

  for (let e = 0; e < removeEventCount; e++) {
    const i1 = removeOrder[e * 2];
    const i2 = removeOrder[e * 2 + 1];
    const idxs: number[] = [];
    if (i1 !== undefined) idxs.push(i1);
    if (i2 !== undefined) idxs.push(i2);
    const highlightFrame =
      removeEventCount === 1
        ? TRANSITION_START_FRAME
        : TRANSITION_START_FRAME + (e * (removalWindow - ORANGE_FLASH_FRAMES)) / Math.max(1, removeEventCount - 1);
    const removeFrame = highlightFrame + ORANGE_FLASH_FRAMES;
    events.push({ type: 'highlight', frame: highlightFrame, indices: idxs });
    events.push({ type: 'remove', frame: removeFrame, indices: idxs });
  }

  const fillStartFrame = TRANSITION_START_FRAME + fillStartOffset;
  const fillSpan = Math.max(1, TRANSITION_END_FRAME - fillStartFrame);
  const fillEventCount = Math.max(Math.ceil(text2.length / 2), removeEventCount);
  for (let e = 0; e < fillEventCount; e++) {
    const frame = fillStartFrame + (fillSpan * (e + 1)) / fillEventCount;
    events.push({ type: 'fill', frame });
  }

  events.sort((a, b) => a.frame - b.frame);

  const highlightAtFrame: (number | undefined)[] = new Array(text1.length).fill(undefined);
  const removeAtFrame: (number | undefined)[] = new Array(text1.length).fill(undefined);
  const placedAtFrame: (number | undefined)[] = new Array(text2.length).fill(undefined);
  const settleAtFrame: (number | undefined)[] = new Array(text2.length).fill(undefined);

  const visible1 = new Set<number>();
  for (let i = 0; i < text1.length; i++) visible1.add(i);
  const queue = [...fillOrder];

  for (const ev of events) {
    if (ev.type === 'highlight') {
      for (const i of ev.indices) if (visible1.has(i)) highlightAtFrame[i] = ev.frame;
    } else if (ev.type === 'remove') {
      for (const i of ev.indices) {
        if (visible1.has(i)) {
          visible1.delete(i);
          removeAtFrame[i] = ev.frame;
        }
      }
    } else {
      let placedThisTick = 0;
      let qi = 0;
      while (placedThisTick < 2 && qi < queue.length) {
        const cand = queue[qi]!;
        const r2 = w2.rects[cand]!;
        let fits = true;
        for (const j of visible1) {
          if (rectsOverlap(w1.rects[j]!, r2)) {
            fits = false;
            break;
          }
        }
        if (fits) {
          placedAtFrame[cand] = ev.frame;
          settleAtFrame[cand] = ev.frame + ORANGE_FLASH_FRAMES;
          queue.splice(qi, 1);
          placedThisTick++;
        } else {
          qi++;
        }
      }
    }
  }

  for (const cand of queue) {
    placedAtFrame[cand] = TRANSITION_END_FRAME;
    settleAtFrame[cand] = TRANSITION_END_FRAME + ORANGE_FLASH_FRAMES;
  }

  return { highlightAtFrame, removeAtFrame, placedAtFrame, settleAtFrame };
}

// ---------------------------------------------------------------------------
// Component.
// ---------------------------------------------------------------------------

export const TextSwap: React.FC<TextSwapProps> = ({ text1, text2, primary, lightMode }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const bgColor = lightMode ? LIGHT_BG : DARK_BG;
  const textColor = lightMode ? LIGHT_TEXT : DARK_TEXT;

  const w1Layout = useMemo(() => computeLayout(text1), [text1]);
  const w2Layout = useMemo(() => computeLayout(text2), [text2]);

  const schedule = useMemo<Schedule | null>(() => {
    if (!w1Layout || !w2Layout) return null;
    return buildSchedule(text1, text2, w1Layout, w2Layout);
  }, [text1, text2, w1Layout, w2Layout]);

  const w1Phase: ('hidden' | 'black' | 'orange')[] = useMemo(() => {
    if (!schedule) return Array.from({ length: text1.length }, () => 'black');
    return Array.from({ length: text1.length }, (_, i) => {
      if (frame < TRANSITION_START_FRAME) return 'black';
      const removeAt = schedule.removeAtFrame[i];
      const highlightAt = schedule.highlightAtFrame[i];
      if (removeAt !== undefined && frame >= removeAt) return 'hidden';
      if (highlightAt !== undefined && frame >= highlightAt) return 'orange';
      return 'black';
    });
  }, [schedule, frame, text1.length]);

  const w2Phase: ('hidden' | 'black' | 'orange')[] = useMemo(() => {
    if (!schedule) return Array.from({ length: text2.length }, () => 'hidden');
    return Array.from({ length: text2.length }, (_, i) => {
      const placedAt = schedule.placedAtFrame[i];
      const settleAt = schedule.settleAtFrame[i];
      if (placedAt === undefined || frame < placedAt) return 'hidden';
      if (settleAt !== undefined && frame >= settleAt) return 'black';
      return 'orange';
    });
  }, [schedule, frame, text2.length]);

  const wordContainerStyle: React.CSSProperties = {
    position: 'absolute',
    left: '50%',
    top: '50%',
    transform: 'translate(-50%, -50%)',
    color: textColor,
    fontFamily: FONT_FAMILY,
    fontSize: FONT_SIZE,
    lineHeight: 1,
    display: 'flex',
    whiteSpace: 'pre',
  };

  return (
    <AbsoluteFill style={{ background: bgColor }}>
      <div style={{ position: 'absolute', left: 0, top: 0, width, height }}>
        <div style={wordContainerStyle}>
          {Array.from(text1).map((ch, i) => (
            <LetterCell
              key={`w1-${i}`}
              ch={ch}
              phase={w1Phase[i] ?? 'black'}
              textColor={textColor}
              orangeColor={primary}
            />
          ))}
        </div>
        <div style={wordContainerStyle}>
          {Array.from(text2).map((ch, i) => (
            <LetterCell
              key={`w2-${i}`}
              ch={ch}
              phase={w2Phase[i] ?? 'hidden'}
              textColor={textColor}
              orangeColor={primary}
            />
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

function LetterCell({
  ch,
  phase,
  textColor,
  orangeColor,
}: {
  ch: string;
  phase: 'hidden' | 'black' | 'orange';
  textColor: string;
  orangeColor: string;
}) {
  const isOrange = phase === 'orange';
  const isHidden = phase === 'hidden';
  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      {isOrange &&
        GLOW_SHAPES.map((g, i) => (
          <span
            key={i}
            aria-hidden
            style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              transform: `translate(-50%, -50%) scale(${g.sizeMul})`,
              color: orangeColor,
              opacity: g.opacity,
              filter: g.blurPx > 0 ? `blur(${g.blurPx}px)` : undefined,
              pointerEvents: 'none',
              whiteSpace: 'pre',
              lineHeight: 1,
            }}
          >
            {ch}
          </span>
        ))}
      <span
        style={{
          position: 'relative',
          visibility: isHidden ? 'hidden' : 'visible',
          color: isOrange ? orangeColor : textColor,
        }}
      >
        {ch}
      </span>
    </span>
  );
}
