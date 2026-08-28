'use client';

// LIVE source of truth for the LP "Stats grid" template tile. Owns
// Stage, all card renderers, types, defaults, and helpers. The
// sandbox at /sandbox/stats-cards imports from here and adds editor
// chrome on top  -  live never imports from sandbox (option-B
// inversion).
//
// Beat plan (canonical):
//   1. A single hero card animates in, full-size, centred. Has a chart
//      and a big headline stat.
//   2. After a hold, that card shrinks toward the top-left grid slot,
//      while three more cards fade/scale in to fill the remaining 2×2
//      grid slots.
//   3. Hold, then reverse content + layout for a seamless loop.

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { CV } from '../theme';

export const FPS = 30;
export const STAGE = 1080; // viewport is square  -  1080×1080 source resolution
// Brand accent. Read via a CSS variable so the library wrapper at
// apps/web/app/projects/library/_components/presets/components/stats-grid.tsx
// can swap the orange to a derived shade of the global library `primary`
// without forking this file. The fallback keeps the LP tile identical when
// no ancestor sets the var.
const ACCENT = 'var(--cv-stack-accent, #F04E23)';

function clamp01(x: number): number { return x < 0 ? 0 : x > 1 ? 1 : x; }
function smoothstep(x: number): number {
  const u = clamp01(x);
  return u * u * (3 - 2 * u);
}
// Steeper S-curve than smoothstep  -  flatter at the edges (slower
// start and end) and faster in the middle. Used for the hero-to-grid
// transition so the morph reads slow → fast → slow.
function smootherstep(x: number): number {
  const u = clamp01(x);
  return u * u * u * (u * (u * 6 - 15) + 10);
}

// Renders a stat string like "247" / "8s" / "96%" partway through its
// final value. `progress` ∈ [0, 1]. The leading numeric prefix counts
// up; any trailing suffix (e.g. "%", "s") appears once progress > 0.
function CountUp({ text, progress }: { text: string; progress: number }) {
  const match = /^(-?\d+)(.*)$/.exec(text);
  if (!match) return <>{text}</>;
  const target = parseInt(match[1]!, 10);
  const suffix = match[2] ?? '';
  const t = clamp01(progress);
  const current = Math.round(target * t);
  // Suffix is always visible  -  at t=0 the value reads "0s" / "0%"
  // rather than just "0", so the multi-stats row never looks like a
  // raw integer dump before the count-up starts.
  return <>{current}{suffix}</>;
}

// ---------------------------------------------------------------------------
// Beats.
// ---------------------------------------------------------------------------
export type Beats = {
  totalFrames: number;
  heroAppearFrame: number;
  heroInDuration: number;
  heroHoldDuration: number;
  // Layout transition: hero shrinks toward its grid slot AND the other
  // three cards fade their SHELL in alongside it. Duration controls
  // how slow the shrink+expand reads.
  layoutTransitionDuration: number;
  // Stagger between successive non-hero card SHELLS appearing.
  layoutStagger: number;
  // Once a non-hero card shell has appeared, its content (pills,
  // numbers, donut arc) animates in over this many frames. Lower =
  // snappier reveal.
  contentRevealDuration: number;
  // Idle hold once all four cards are fully revealed.
  holdAllDuration: number;
  // Reverse phase A: text + pills + chart guts fade out and slide
  // *down* by a few px on cards 2/3/4. Cards still occupy their slots.
  exitContentDuration: number;
  // Reverse phase B: cards 2/3/4 shrink back toward the hero anchors
  // while the hero grows back to its original centred size  -  mirror
  // of layoutTransitionDuration so the loop is reversible.
  exitLayoutDuration: number;
  // 3D camera applied to the whole stage. All four cards live on the
  // same tilted plane.
  perspective: number;   // CSS perspective in px (smaller = stronger 3D)
  rotateX: number;       // tilt forward/back in degrees
  rotateY: number;       // tilt left/right in degrees
  // Whole-grid offset + scale  -  applied to the entire group of four
  // cards as a single CSS transform on the 3D plane. Lets you nudge
  // and scale the composition without retuning slot maths.
  cardsOffset: { x: number; y: number; scale: number };
  // Idle float  -  once the cards are settled, every chart bobs on a
  // sine wave with a per-card phase offset. amplitude in px, period
  // in seconds. Set amplitude to 0 to disable.
  floatAmplitude: number;
  floatPeriod: number;
  floatPhaseStagger: number; // fraction of period offset per card index
};

// Seamless-loop schedule. State at frame 0 (hero alone, centred, full
// size) matches state at frame totalFrames after the reverse phases
// run, so wrap is invisible. heroIn is collapsed to a single-frame
// stub so the entrance fade doesn't fight the loop boundary.
export const DEFAULT_BEATS: Beats = {
  totalFrames: 270,
  heroAppearFrame: -1,
  heroInDuration: 1,
  heroHoldDuration: 20,
  layoutTransitionDuration: 48,
  layoutStagger: 6,
  contentRevealDuration: 55,
  holdAllDuration: 60,
  exitContentDuration: 30,
  exitLayoutDuration: 48,
  cardsOffset: { x: 52, y: -24, scale: 0.81 },
  perspective: 1150,
  rotateX: 11,
  rotateY: 13.5,
  floatAmplitude: 12,
  floatPeriod: 5,
  floatPhaseStagger: 0.18,
};

// ---------------------------------------------------------------------------
// Card data  -  slot-specific renderers below pick the right layout per
// `kind`. Slot order matches the SLOTS layout (idx 0 = TL, 1 = TR,
// 2 = BL, 3 = BR).
// ---------------------------------------------------------------------------
type Card =
  | { id: string; kind: 'line';        label: string; stat: string; delta: string; series: number[] }
  | { id: string; kind: 'pill-bar';    label: string; stat: string; delta: string; pillCount: number; filledCount: number }
  | { id: string; kind: 'multi-stats'; stats: { value: string; label: string; deltaPct: number }[] }
  | { id: string; kind: 'donut';       label: string; value: number; delta: string };

const CARDS: readonly Card[] = [
  // Card 1 (TL, tall, hero)  -  smooth line, rounded ends, no dot.
  {
    id: 'mrr',
    kind: 'line',
    label: 'MRR',
    stat: '$48.2k',
    delta: '+47%',
    series: [10, 14, 11, 18, 22, 19, 28, 26, 36, 44, 41, 56, 62, 68, 74],
  },
  // Card 2 (TR, short)  -  pill bar reads as a "score" (9/10 stops
  // filled = customer satisfaction).
  {
    id: 'satisfaction',
    kind: 'pill-bar',
    label: 'Satisfaction',
    stat: '92%',
    delta: '+6%',
    pillCount: 10,
    filledCount: 9,
  },
  // Card 3 (BL, short)  -  three small Curvable-relevant stats with
  // orange ▲ deltas.
  {
    id: 'multi',
    kind: 'multi-stats',
    stats: [
      { value: '247', label: 'Videos',  deltaPct: 47 },
      { value: '8s',  label: 'Render',  deltaPct: 24 },
      { value: '96%', label: 'Branded', deltaPct: 6 },
    ],
  },
  // Card 4 (BR, tall)  -  donut / gauge with pilled stroke ends.
  {
    id: 'retention',
    kind: 'donut',
    label: 'Retention',
    value: 94,
    delta: '+3pt',
  },
];

// 2×2 grid layout  -  pinwheel staggered.
//
// Constraint the layout satisfies: in each column the two card heights
// SUM TO the column's inner height, which equals the sum of widths of
// the two cards in any row. Concretely:
//
//   tall_h + short_h = COLUMN_HEIGHT
//                    = STAGE − 2·GRID_PAD − GRID_GAP   (≈ 932)
//                    = 2 · SLOT_WIDTH                  (≈ 932)
//                    = sum of widths in a row
//
// Both columns therefore reach the bottom-pad cleanly with no empty
// band. Tall cards sit on the main diagonal (TL / BR), short cards on
// the anti-diagonal (TR / BL)  -  pinwheel feel.
const GRID_GAP = 36;
const GRID_PAD = 56;
const COLUMN_HEIGHT = STAGE - GRID_PAD * 2 - GRID_GAP; // 932
const SLOT_WIDTH = COLUMN_HEIGHT / 2; // 466  -  keeps row-width-sum == column-height
const TALL_RATIO = 0.64; // tall card takes ~64% of column height
const SLOT_HEIGHT_TALL = Math.round(COLUMN_HEIGHT * TALL_RATIO); // ≈ 597
const SLOT_HEIGHT_SHORT = COLUMN_HEIGHT - SLOT_HEIGHT_TALL;     // ≈ 335

type Slot = { x: number; y: number; w: number; h: number };

// Layout (changed from pinwheel to "L-shape fill"):
//   TL tall (hero)         TR tall
//   BL short               BR short
//
// This lets the non-hero cards' final positions match the L-shaped
// space the hero leaves as it shrinks toward TL. Each non-hero card
// is anchored to the hero's edge during the transition, so they
// literally grow into the void the hero creates.
const SLOTS: Slot[] = [
  // idx 0  -  TL  (tall, hero)
  { x: GRID_PAD,                          y: GRID_PAD,                                       w: SLOT_WIDTH, h: SLOT_HEIGHT_TALL },
  // idx 1  -  TR  (tall, anchored to hero's right edge)
  { x: GRID_PAD + SLOT_WIDTH + GRID_GAP,  y: GRID_PAD,                                       w: SLOT_WIDTH, h: SLOT_HEIGHT_TALL },
  // idx 2  -  BL  (short, anchored to hero's bottom edge)
  { x: GRID_PAD,                          y: GRID_PAD + SLOT_HEIGHT_TALL + GRID_GAP,         w: SLOT_WIDTH, h: SLOT_HEIGHT_SHORT },
  // idx 3  -  BR  (short, anchored to hero's bottom-right corner)
  { x: GRID_PAD + SLOT_WIDTH + GRID_GAP,  y: GRID_PAD + SLOT_HEIGHT_TALL + GRID_GAP,         w: SLOT_WIDTH, h: SLOT_HEIGHT_SHORT },
];

// Hero (full-size) bounds.
const HERO_PAD = 56;
const HERO_X = HERO_PAD;
const HERO_Y = HERO_PAD;
const HERO_SIZE = STAGE - HERO_PAD * 2; // ≈ 968
// ---------------------------------------------------------------------------
// Stage  -  renders the 4 cards with frame-driven positions.
// ---------------------------------------------------------------------------
export function Stage({
  playhead,
  beats,
  tSecOverride,
}: {
  playhead: number;
  beats: Beats;
  // Optional external clock  -  when set, the rAF loop is bypassed.
  // Used by the Remotion render pipeline to produce deterministic
  // frames (frame / fps).
  tSecOverride?: number;
}) {
  // Continuous-time clock for the idle-float sine wave. Uses
  // performance.now() so the bob is smooth regardless of frame
  // stepping and independent of playback. Float kicks in only after
  // the content reveal completes (otherwise it fights the slide-down).
  const [tSecState, setTSec] = useState(0);
  useEffect(() => {
    if (tSecOverride !== undefined) return;
    let raf = 0;
    const loop = () => {
      setTSec(performance.now() / 1000);
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [tSecOverride]);
  const tSec = tSecOverride !== undefined ? tSecOverride : tSecState;

  // Phase timings derived from beats. Schedule:
  //   [0, transitionStart)               -  hero alone, hold
  //   [transitionStart, +layoutT)        -  forward layout transition
  //   [contentStart, +contentReveal)     -  content slides + fades in
  //   [holdAllStart, +holdAll)           -  4-card composition hold
  //   [exitContentStart, +exitContent)   -  content fades + slides down
  //   [exitLayoutStart, +exitLayout)     -  reverse layout, hero grows back
  //   [exitLayoutEnd, totalFrames)       -  hero alone, hold → wraps clean
  const heroIn = (f: number) => smoothstep(clamp01((f - beats.heroAppearFrame) / Math.max(1, beats.heroInDuration)));
  const transitionStart = beats.heroAppearFrame + beats.heroInDuration + beats.heroHoldDuration;
  const contentStart = transitionStart + beats.layoutTransitionDuration * 0.7;
  const contentEnd = contentStart + beats.contentRevealDuration;
  const holdAllStart = contentEnd;
  const exitContentStart = holdAllStart + beats.holdAllDuration;
  const exitLayoutStart = exitContentStart + beats.exitContentDuration;

  // Forward layout T (0 → 1) over the entrance transition.
  const forwardLayoutT = (f: number) =>
    smootherstep(clamp01((f - transitionStart) / Math.max(1, beats.layoutTransitionDuration)));
  // Reverse layout T (0 → 1) over the exit transition.
  const reverseLayoutT = (f: number) =>
    smootherstep(clamp01((f - exitLayoutStart) / Math.max(1, beats.exitLayoutDuration)));
  // Combined transition T (0 while hero solo, 1 while 4-cards, 0 again
  // after reverse). Used for hero/non-hero dimensions and float amplitude.
  const transitionT = (f: number) => forwardLayoutT(f) * (1 - reverseLayoutT(f));

  // Float runs continuously on wall-clock (tSec)  -  no playhead-derived
  // gate, so the bob never resets at the loop boundary. Amplitude lerps
  // between 20px (hero solo) and 10px (4-card grid) via transitionT.
  const period = Math.max(0.1, beats.floatPeriod);
  const ampLerp = 20 + (10 - 20) * transitionT(playhead);
  const floatYForIdx = (idx: number) => {
    if (beats.floatAmplitude <= 0) return 0;
    const phase = idx * beats.floatPhaseStagger;
    return Math.sin((tSec / period + phase) * 2 * Math.PI) * ampLerp;
  };

  // Content exit T (0 → 1)  -  drives the slide-down + fade-out of text /
  // pills / chart guts on cards 2-4 at the end of the loop.
  const exitContentT = smoothstep(
    clamp01((playhead - exitContentStart) / Math.max(1, beats.exitContentDuration)),
  );

  // Hero animated dimensions at the current playhead. Computed ONCE
  // so every non-hero card can read the same hero state when anchoring
  // its own edges (cards "grow into the space the hero leaves").
  const heroT = transitionT(playhead);
  const heroSlot = SLOTS[0]!;
  const heroDims = {
    w: HERO_SIZE + (heroSlot.w - HERO_SIZE) * heroT,
    h: HERO_SIZE + (heroSlot.h - HERO_SIZE) * heroT,
  };

  // Per-card render state.
  const cards = CARDS.map((card, idx) => {
    const t = transitionT(playhead);
    // Hero card (idx=0) interpolates from full-size centered to slot 0.
    // Others (idx 1-3) start hidden, fade/scale in during the transition,
    // each offset by layoutStagger.
    if (idx === 0) {
      const heroFade = heroIn(playhead);
      const slot = SLOTS[0]!;
      const x = HERO_X + (slot.x - HERO_X) * t;
      const y = HERO_Y + (slot.y - HERO_Y) * t;
      const w = HERO_SIZE + (slot.w - HERO_SIZE) * t;
      const h = HERO_SIZE + (slot.h - HERO_SIZE) * t;
      // Hero opacity is the entrance fade only (heroIn 0→1 during the
      // intro). Once it's in, it stays at 1 through the shrink  -  no
      // opacity dip during the transition.
      return { card, x, y, w, h, opacity: heroFade, contentT: 1, exitT: 0, isHero: true, heroProgress: 1 - t };
    } else {
      // Non-hero cards are ANCHORED to the hero's current edges with
      // a fixed gap. As the hero shrinks, each card grows from that
      // anchor into its final slot bounds  -  no uniform CSS scale, no
      // zoom-in. The card's free edges stay at the slot's outer
      // bounds, so at t=1 every card lands exactly on its slot.
      //
      //   Card 2 (TR, vertical pill):  left tracks hero right;
      //                                top/bottom/right are fixed.
      //   Card 3 (BL, horizontal pill): top tracks hero bottom;
      //                                left/right/bottom are fixed.
      //   Card 4 (BR, ball):           left tracks hero right, top
      //                                tracks hero bottom; right +
      //                                bottom are fixed.
      const slot = SLOTS[idx]!;
      const heroRight  = HERO_X    + heroDims.w;
      const heroBottom = HERO_Y    + heroDims.h;
      const slotRight  = slot.x    + slot.w;
      const slotBottom = slot.y    + slot.h;

      let x = slot.x;
      let y = slot.y;
      let w = slot.w;
      let h = slot.h;

      if (idx === 1) {
        x = heroRight + GRID_GAP;
        w = slotRight - x;
        // y + h stay at slot defaults.
      } else if (idx === 2) {
        y = heroBottom + GRID_GAP;
        h = slotBottom - y;
        // x + w stay at slot defaults.
      } else {
        x = heroRight + GRID_GAP;
        w = slotRight - x;
        y = heroBottom + GRID_GAP;
        h = slotBottom - y;
      }

      // Fade in fast as soon as the card's slimmer dimension is
      // visible (≈ 2 frames worth of "thin pill" appearing).
      const minDim = Math.min(w, h);
      const opacity = clamp01(minDim / 6);

      // Content starts BEFORE the shell finishes growing  -  at 70% of the
      // layout transition  -  so the text fade/slide-in overlaps the final
      // stretch of card growth. exitContentT later fades it back out.
      const entryT = smoothstep(
        clamp01((playhead - contentStart) / Math.max(1, beats.contentRevealDuration)),
      );
      const contentT = entryT * (1 - exitContentT);
      return { card, x, y, w, h, opacity, contentT, exitT: exitContentT, isHero: false, heroProgress: 0 };
    }
  });

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: 'transparent',
        overflow: 'hidden',
        // 3D camera lives on the stage. The inner wrapper carries the
        // rotateX/Y so every card sits on the same tilted plane.
        perspective: `${beats.perspective}px`,
        perspectiveOrigin: '50% 50%',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: 0,
          // Combined transform  -  3D camera plus the whole-composition
          // nudge/scale. The whole cards group moves as one.
          transform: `rotateX(${beats.rotateX}deg) rotateY(${beats.rotateY}deg) translate(${beats.cardsOffset.x}px, ${beats.cardsOffset.y}px) scale(${beats.cardsOffset.scale})`,
          transformStyle: 'preserve-3d',
          transformOrigin: '50% 50%',
        }}
      >
        {cards.map((c, i) => (
          <div
            key={c.card.id}
            style={{
              position: 'absolute',
              left: 0,
              top: 0,
              // Per-card idle float  -  sine-wave translateY with a
              // phase offset per card index so every chart bobs at
              // its own beat. Gated by `floatGate` so it only kicks in
              // after the reveal animation completes.
              transform: `translateY(${floatYForIdx(i)}px)`,
              // Hero sits on top while shrinking so the non-hero pills
              // emerge from BEHIND it. Once the hero settles, every
              // card shares the same plane (z-index 1).
              zIndex: c.isHero ? 3 : 1,
              pointerEvents: 'none',
              willChange: 'transform',
            }}
          >
            <CardRenderer
              card={c.card}
              x={c.x}
              y={c.y}
              w={c.w}
              h={c.h}
              opacity={c.opacity}
              contentT={c.contentT}
              exitT={c.exitT}
              isHero={c.isHero}
              heroProgress={c.heroProgress}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared typography for every card. Three sizes total. All number /
// stat elements share the Curvable Geist font via the global CSS var
// the root layout exposes.
// ---------------------------------------------------------------------------
const CV_FONT = 'var(--font-cv-sans), system-ui, sans-serif';
// Card name (top-left) + delta pill (top-right)  -  uniform across
// every card. Pulled back 20% from the prior double-size pass so the
// hierarchy is strong without overwhelming the chart.
const FONT_LABEL = 29;
const FONT_DELTA = 21;
// Big chart stat for cards 1 + 2 (the line + pill-bar). Also 20%
// down from 88 → 70.
const FONT_HERO  = 70;
// Donut centre value (card 4)  -  kept at the prior big-stat size; the
// donut already reads as the headline visual without a giant centre.
const FONT_DONUT = 44;
// Card 3 (multi-stats) is the only one with deliberately smaller
// text. The three numbers share the row, so they sit between FONT_HERO
// and the tiny sub-labels.
const FONT_MULTI_VALUE = 36;
const FONT_MULTI_LABEL = 12;
// Tooltip caption (small caps line above the value) is decoupled from
// FONT_DELTA so the tooltip doesn't blow up when the delta pill does.
const FONT_TIP_CAPTION = 13;

// ---------------------------------------------------------------------------
// HoverTooltip  -  black floating card with text, used by every chart's
// hover. Positions absolutely within its container (relative parent).
// ---------------------------------------------------------------------------
function HoverTooltip({
  visible,
  x,
  y,
  children,
  // If true, the tooltip's horizontal origin is its center (used by
  // tooltips that track the cursor X). Otherwise the tooltip uses
  // (x, y) as the top-left corner.
  centered = true,
}: {
  visible: boolean;
  x: number | string;
  y: number | string;
  children: React.ReactNode;
  centered?: boolean;
}) {
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        transform: centered
          ? `translate(-50%, calc(-100% - 14px)) ${visible ? '' : 'translateY(6px)'}`
          : `translate(0, calc(-100% - 14px)) ${visible ? '' : 'translateY(6px)'}`,
        background: '#0a0a0a',
        border: `1px solid #2a2a2a`,
        borderRadius: 14,
        padding: '14px 20px',
        color: CV.darkText,
        fontFamily: CV_FONT,
        whiteSpace: 'nowrap',
        pointerEvents: 'none',
        opacity: visible ? 1 : 0,
        transition: 'opacity 180ms ease, transform 180ms ease',
        zIndex: 50,
        boxShadow: '0 14px 32px -10px rgba(0,0,0,0.7)',
      }}
    >
      {children}
    </div>
  );
}

// Standardised tooltip body  -  every card uses the same upper caption +
// value typography so the hover panels read identically.
function TooltipBody({ caption, value }: { caption: string; value: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span
        style={{
          color: CV.darkMutedSubtle,
          fontSize: FONT_TIP_CAPTION,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          fontWeight: 500,
        }}
      >
        {caption}
      </span>
      <span
        style={{
          fontSize: 24,
          fontWeight: 600,
          letterSpacing: '-0.02em',
          fontFamily: CV_FONT,
        }}
      >
        {value}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CardShell  -  outer frosted-glass shell + double-border ring. The four
// card kinds plug their own content in as children.
// ---------------------------------------------------------------------------
function CardShell({
  x, y, w, h, opacity,
  hovered,
  onMouseEnter,
  onMouseLeave,
  exitT = 0,
  children,
}: {
  x: number;
  y: number;
  w: number;
  h: number;
  opacity: number;
  hovered: boolean;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  // 0 → 1 across the exitContent phase. Drives a uniform fade + 10px
  // slide-down on the inner content (text / pills / chart guts) so
  // the cards visibly "empty out" before the reverse layout kicks in.
  exitT?: number;
  children: (innerW: number, innerH: number) => React.ReactNode;
}) {
  const minDim = Math.min(w, h);
  // Pill-aware radius: when one dimension is tiny, the radius is
  // half that dimension → fully rounded ends (pill / ball). At full
  // size it caps at MAX_OUTER_RADIUS for the normal card look.
  const MAX_OUTER_RADIUS = 46;
  const outerRadius = Math.min(minDim / 2, MAX_OUTER_RADIUS);
  // Inset + inner border only kick in once the card is big enough to
  // host them. Below the threshold we render just the outer pill.
  const SHELL_THRESHOLD = 50;
  const borderInset = minDim < SHELL_THRESHOLD ? 0 : Math.max(18, minDim * 0.05);
  const innerRadius = Math.max(0, outerRadius - borderInset);
  const innerPad = minDim < SHELL_THRESHOLD ? 0 : minDim * 0.06;
  const innerW = Math.max(0, w - 2 * borderInset - 2 * innerPad);
  const innerH = Math.max(0, h - 2 * borderInset - 2 * innerPad);
  const showInnerRing = minDim >= SHELL_THRESHOLD;

  return (
    <div
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: w,
        height: h,
        opacity,
        background: hovered ? CV.darkSurface : CV.darkBg,
        border: 'none',
        borderRadius: outerRadius,
        // Symmetric "0 0" glow dropped entirely  -  that's what was
        // bleeding above the top cards. Only a soft downward drop
        // remains on hover, plus the always-on black drop.
        boxShadow: hovered
          ? '0 22px 50px -18px rgba(240,78,35,0.12), 0 10px 30px -12px rgba(0,0,0,0.6)'
          : '0 10px 30px -12px rgba(0,0,0,0.6)',
        transition: 'background 280ms ease, border-color 280ms ease, box-shadow 280ms ease',
        willChange: 'left, top, width, height, opacity',
        overflow: 'hidden',
      }}
    >
      {showInnerRing ? (
        <div
          style={{
            position: 'absolute',
            top: borderInset,
            left: borderInset,
            right: borderInset,
            bottom: borderInset,
            borderRadius: innerRadius,
            padding: innerPad,
            display: 'flex',
            flexDirection: 'column',
            opacity: 1 - exitT,
            transform: `translateY(${exitT * 10}px)`,
          }}
        >
          {children(innerW, innerH)}
        </div>
      ) : null}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Header: label + delta pill  -  shared across the line/pill-bar cards.
// ---------------------------------------------------------------------------
// Unified card header  -  same label / delta typography across every
// card that uses it (LineCard, PillBarCard, DonutCard).
function CardHeader({ label, delta }: { label: string; delta: string }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <span
        style={{
          fontSize: FONT_LABEL,
          color: CV.darkText,
          letterSpacing: '-0.01em',
          fontWeight: 500,
          fontFamily: CV_FONT,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: FONT_DELTA,
          color: ACCENT,
          background: 'rgba(240,78,35,0.12)',
          padding: '4px 10px',
          borderRadius: 999,
          fontWeight: 600,
          letterSpacing: '-0.01em',
          fontFamily: CV_FONT,
        }}
      >
        {delta}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// LineCard  -  TL, tall, hero. Smooth bezier line, rounded caps, no dot.
// Hover: line traces from left to right (stroke-dashoffset) and the
// gradient fill brightens.
// ---------------------------------------------------------------------------
function LineCard({
  card, x, y, w, h, opacity, contentT, exitT, isHero, heroProgress,
}: {
  card: Extract<Card, { kind: 'line' }>;
  x: number; y: number; w: number; h: number;
  opacity: number; contentT: number; exitT: number; isHero: boolean; heroProgress: number;
}) {
  const [hovered, setHovered] = useState(false);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  // Hero content visible from the start  -  contentT runs alongside the
  // shell fade for this card.
  void isHero; void heroProgress; void contentT;

  return (
    <CardShell
      x={x} y={y} w={w} h={h} opacity={opacity}
      hovered={hovered}
      exitT={exitT}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setHoverIdx(null);
      }}
    >
      {(innerW, innerH) => (
        <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <CardHeader label={card.label} delta={card.delta} />
            <div
              style={{
                fontSize: FONT_HERO,
                fontWeight: 600,
                letterSpacing: '-0.03em',
                lineHeight: 1,
                color: CV.darkText,
                fontFamily: CV_FONT,
              }}
            >
              {card.stat}
            </div>
          </div>
          <SmoothLineChart
            series={card.series}
            width={innerW}
            height={innerH * 0.42}
            hoverIdx={hoverIdx}
            onHoverIdx={setHoverIdx}
          />
        </div>
      )}
    </CardShell>
  );
}

// MRR series in dollars (thousands). One entry per "week"  -  used both
// for the chart shape and the tooltip's value/label readout.
function formatLineValue(weekIdx: number, scaledValue: number): { label: string; value: string } {
  return {
    label: `Week ${weekIdx + 1}`,
    value: `$${scaledValue.toFixed(1)}k`,
  };
}

function SmoothLineChart({
  series,
  width,
  height,
  hoverIdx,
  onHoverIdx,
}: {
  series: number[];
  width: number;
  height: number;
  hoverIdx: number | null;
  onHoverIdx: (idx: number | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const h = Math.max(60, height);
  const w = Math.max(120, width);
  const pad = 6;
  const max = Math.max(...series);
  const min = Math.min(...series);
  const range = Math.max(1, max - min);
  const stepX = (w - pad * 2) / Math.max(1, series.length - 1);

  const pts = series.map((v, i) => ({
    x: pad + i * stepX,
    y: pad + (1 - (v - min) / range) * (h - pad * 2),
  }));

  // Smooth bezier  -  same midpoint-control technique nw-site uses.
  let d = `M ${pts[0]!.x} ${pts[0]!.y}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i]!;
    const p1 = pts[i + 1]!;
    const cx = (p0.x + p1.x) / 2;
    d += ` C ${cx},${p0.y} ${cx},${p1.y} ${p1.x},${p1.y}`;
  }
  const dArea = `${d} L ${pts[pts.length - 1]!.x} ${h} L ${pts[0]!.x} ${h} Z`;

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const localX = ((e.clientX - rect.left) / rect.width) * w;
    const idx = Math.max(0, Math.min(series.length - 1, Math.round((localX - pad) / stepX)));
    onHoverIdx(idx);
  };

  const tip = hoverIdx != null
    ? formatLineValue(hoverIdx, series[hoverIdx]!)
    : null;
  const tipPt = hoverIdx != null ? pts[hoverIdx]! : null;
  const tipXPct = tipPt ? (tipPt.x / w) * 100 : 0;

  return (
    <div
      ref={containerRef}
      style={{ position: 'relative', width: '100%', height: h }}
      onMouseMove={onMove}
      onMouseLeave={() => onHoverIdx(null)}
    >
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ display: 'block', width: '100%', height: '100%' }}>
        <defs>
          <linearGradient id="line-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={ACCENT} stopOpacity="0.28" />
            <stop offset="100%" stopColor={ACCENT} stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={dArea} fill="url(#line-fill)" />
        <path
          d={d}
          fill="none"
          stroke={ACCENT}
          strokeWidth={2.2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* Dashed vertical guide at the hovered week. */}
        {tipPt && (
          <line
            x1={tipPt.x}
            x2={tipPt.x}
            y1={pad}
            y2={h - pad}
            stroke="rgba(255,255,255,0.45)"
            strokeWidth={1}
            strokeDasharray="4 4"
            pointerEvents="none"
          />
        )}
      </svg>
      <HoverTooltip visible={tip !== null} x={`${tipXPct}%`} y={0}>
        {tip && <TooltipBody caption={tip.label} value={tip.value} />}
      </HoverTooltip>
    </div>
  );
}

// ---------------------------------------------------------------------------
// PillBarCard  -  TR, short. Row of horizontal pill outlines, leading
// ones filled with orange (visual "score"  -  n/total). Hover: card glow
// strengthens + a tooltip card shows the percentage (the pills
// themselves stay static  -  they ARE the score, no need to animate).
// ---------------------------------------------------------------------------
function PillBarCard({
  card, x, y, w, h, opacity, contentT, exitT,
}: {
  card: Extract<Card, { kind: 'pill-bar' }>;
  x: number; y: number; w: number; h: number; opacity: number; contentT: number; exitT: number;
}) {
  const [hovered, setHovered] = useState(false);
  const [cursor, setCursor] = useState<{ xPct: number } | null>(null);
  const pct = Math.round((card.filledCount / card.pillCount) * 100);
  // Content reveal: orange pills appear one-by-one as contentT goes 0→1.
  // The white outlines are already there (PillBar's base style).
  const filledReveal = Math.min(card.filledCount, Math.floor(contentT * card.filledCount + 0.0001));
  // Header + stat slide down + fade in once contentT > 0.
  const headerT = smoothstep(clamp01(contentT * 1.4));

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setCursor({ xPct: ((e.clientX - rect.left) / rect.width) * 100 });
  };

  return (
    <CardShell
      x={x} y={y} w={w} h={h} opacity={opacity}
      hovered={hovered}
      exitT={exitT}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setCursor(null);
      }}
    >
      {(innerW) => (
        <div
          style={{ position: 'relative', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%' }}
          onMouseMove={onMove}
        >
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 16,
              opacity: headerT,
              transform: `translateY(${(1 - headerT) * -10}px)`,
              transition: 'opacity 240ms ease, transform 240ms ease',
            }}
          >
            <CardHeader label={card.label} delta={card.delta} />
            <div
              style={{
                fontSize: FONT_HERO,
                fontWeight: 600,
                letterSpacing: '-0.03em',
                lineHeight: 1,
                color: CV.darkText,
                fontFamily: CV_FONT,
              }}
            >
              {card.stat}
            </div>
          </div>
          <div
            style={{
              opacity: headerT,
              transform: `translateY(${(1 - headerT) * -10}px)`,
              transition: 'opacity 240ms ease, transform 240ms ease',
            }}
          >
            <PillBar count={card.pillCount} filled={filledReveal} width={innerW} />
          </div>
          <HoverTooltip visible={hovered} x={`${cursor?.xPct ?? 50}%`} y="60%">
            <TooltipBody caption="Satisfaction" value={`${pct}% · ${card.filledCount} / ${card.pillCount}`} />
          </HoverTooltip>
        </div>
      )}
    </CardShell>
  );
}

function PillBar({ count, filled, width }: { count: number; filled: number; width: number }) {
  const gap = 8;
  const pillW = (width - gap * (count - 1)) / count;
  const pillH = Math.max(14, pillW * 0.45);
  return (
    <div style={{ display: 'flex', gap, alignItems: 'center' }}>
      {Array.from({ length: count }).map((_, i) => {
        const isFilled = i < filled;
        return (
          <div
            key={i}
            style={{
              width: pillW,
              height: pillH,
              borderRadius: 999,
              background: isFilled ? ACCENT : 'transparent',
              border: `1.5px solid ${isFilled ? ACCENT : 'rgba(255,255,255,0.45)'}`,
            }}
          />
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MultiStatsCard  -  BL, short. Three stats side by side with green
// delta arrows. Hover: each stat scales up subtly + the delta arrow
// nudges up.
// ---------------------------------------------------------------------------
function MultiStatsCard({
  card, x, y, w, h, opacity, contentT, exitT,
}: {
  card: Extract<Card, { kind: 'multi-stats' }>;
  x: number; y: number; w: number; h: number; opacity: number; contentT: number; exitT: number;
}) {
  const [hovered, setHovered] = useState<number | null>(null);
  const size = Math.min(w, h);
  // Two-phase reveal:
  //   slideT  -  whole row slides down + fades in over the first 35% of
  //            contentT. While it slides in the values read "0 0s 0%".
  //   countT  -  numbers count up to target over the back 65%.
  //   arrowT  -  delta arrows slide up from below in the back half.
  const slideT = smoothstep(clamp01(contentT / 0.35));
  const countT = smoothstep(clamp01((contentT - 0.35) / 0.65));
  const arrowT = smoothstep(clamp01((contentT - 0.5) / 0.5));
  // Card 3 is the "smaller text" card  -  uses its own scale so the
  // three stats fit comfortably in the short row.
  const valueFont = FONT_MULTI_VALUE;
  const labelFont = FONT_MULTI_LABEL;
  const deltaFont = FONT_MULTI_LABEL;

  return (
    <CardShell
      x={x} y={y} w={w} h={h} opacity={opacity}
      hovered={hovered !== null}
      exitT={exitT}
      onMouseEnter={() => {}}
      onMouseLeave={() => setHovered(null)}
    >
      {() => (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr 1fr',
            gap: size * 0.08,
            alignItems: 'center',
            // Centre each stat block within its column so the left
            // padding to the first value matches the right padding
            // from the last value. Without this, the columns sit at
            // their grid-cell left edge → empty space accumulates on
            // the right of the row.
            justifyItems: 'center',
            height: '100%',
            opacity: slideT,
            transform: `translateY(${(1 - slideT) * -18}px)`,
            transition: 'none',
          }}
        >
          {card.stats.map((s, i) => {
            const isHovered = hovered === i;
            return (
              <div
                key={s.label}
                onMouseEnter={() => setHovered(i)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: size * 0.012,
                  transform: isHovered ? 'translateY(-4px)' : 'translateY(0)',
                  transition: 'transform 280ms cubic-bezier(0.4, 0, 0.2, 1)',
                  cursor: 'pointer',
                }}
              >
                <span
                  style={{
                    fontSize: valueFont,
                    fontWeight: 600,
                    letterSpacing: '-0.03em',
                    lineHeight: 1,
                    color: CV.darkText,
                    fontVariantNumeric: 'tabular-nums',
                    fontFamily: CV_FONT,
                  }}
                >
                  <CountUp text={s.value} progress={countT} />
                </span>
                <span
                  style={{
                    fontSize: labelFont,
                    color: isHovered ? CV.darkText : 'rgba(252,251,248,0.50)',
                    letterSpacing: '0.16em',
                    textTransform: 'uppercase',
                    transition: 'color 220ms ease',
                    opacity: arrowT,
                    transform: `translateY(${(1 - arrowT) * 8}px)`,
                  }}
                >
                  {s.label}
                </span>
                <span
                  style={{
                    fontSize: deltaFont,
                    color: ACCENT,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 4,
                    // Arrow + delta slide up from below as contentT
                    // crosses into its back half.
                    opacity: arrowT,
                    transform: `translateY(${(1 - arrowT) * 14}px)`,
                  }}
                >
                  <span
                    style={{
                      display: 'inline-block',
                      transform: isHovered ? 'translateY(-2px)' : 'translateY(0)',
                      transition: 'transform 280ms cubic-bezier(0.4, 0, 0.2, 1)',
                    }}
                  >
                    ▲
                  </span>
                  {s.deltaPct}%
                </span>
              </div>
            );
          })}
        </div>
      )}
    </CardShell>
  );
}

// ---------------------------------------------------------------------------
// DonutCard  -  BR, tall. Gauge with pilled stroke ends (both the
// coloured arc and the grey unfilled arc), big % in the centre.
// Hover: arc grows from 0 to value with a glow.
// ---------------------------------------------------------------------------
function DonutCard({
  card, x, y, w, h, opacity, contentT, exitT,
}: {
  card: Extract<Card, { kind: 'donut' }>;
  x: number; y: number; w: number; h: number; opacity: number; contentT: number; exitT: number;
}) {
  const [hovered, setHovered] = useState(false);
  const [cursor, setCursor] = useState<{ xPct: number; yPct: number } | null>(null);
  const size = Math.min(w, h);
  // Two-phase reveal:
  //   slideT  -  title + gauge wrapper slide down + fade in over the
  //            first 35% of contentT.
  //   arcT    -  donut percentage animates 0 → target over the back 65%.
  //            Gauge's rounded stroke cap means it starts as a single
  //            orange dot ("ball") and grows from there.
  const slideT = smoothstep(clamp01(contentT / 0.35));
  const arcT = smoothstep(clamp01((contentT - 0.35) / 0.65));
  const animatedValue = card.value * arcT;

  const onMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setCursor({
      xPct: ((e.clientX - rect.left) / rect.width) * 100,
      yPct: ((e.clientY - rect.top) / rect.height) * 100,
    });
  };

  return (
    <CardShell
      x={x} y={y} w={w} h={h} opacity={opacity}
      hovered={hovered}
      exitT={exitT}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => {
        setHovered(false);
        setCursor(null);
      }}
    >
      {() => (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            height: '100%',
            // Whole content slides down + fades in. Same slide pattern
            // the top-right pill card uses on its header, applied to
            // the entire donut card (title + gauge + centre value
            // travel together).
            opacity: slideT,
            transform: `translateY(${(1 - slideT) * -18}px)`,
          }}
        >
          <CardHeader label={card.label} delta={card.delta} />
          <div
            style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1 }}
            onMouseMove={onMove}
          >
            <Gauge value={animatedValue} size={size * 0.55} hovered={hovered} />
            <HoverTooltip
              visible={hovered}
              x={`${cursor?.xPct ?? 50}%`}
              y={`${cursor?.yPct ?? 50}%`}
            >
              <TooltipBody caption={card.label} value={`${card.value}% · ${card.delta}`} />
            </HoverTooltip>
          </div>
        </div>
      )}
    </CardShell>
  );
}

function Gauge({ value, size, hovered }: { value: number; size: number; hovered: boolean }) {
  const r = 34;
  const c = 2 * Math.PI * r;
  const v = Math.max(0, Math.min(100, value));

  // Leave a 20° gap between filled and unfilled arc ends so the two
  // rounded caps don't overlap. Ported from nw-site/Gauge.
  const gapDeg = 20;
  const gapPortion = (gapDeg / 360) * c;
  const hasGap = v > 0 && v < 100;
  const usableC = hasGap ? c - 2 * gapPortion : c;

  const filledLen = Math.max(0, (usableC * v) / 100);
  const unfilledLen = Math.max(0, (usableC * (100 - v)) / 100);
  const unfilledRotation = hasGap ? -90 + ((filledLen + gapPortion) / c) * 360 : 0;

  const stroke = 9;
  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      {/* Halo glow  -  radial gradient centred on the donut. Bleeds
          INWARD into the donut centre AND outward past the arc so the
          orange isn't clipped on either side. Sized 1.8× the gauge so
          the soft edge has room. */}
      <div
        aria-hidden
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: size * 1.8,
          height: size * 1.8,
          transform: 'translate(-50%, -50%)',
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(240,78,35,0.12) 0%, rgba(240,78,35,0.05) 30%, rgba(240,78,35,0) 60%)',
          opacity: hovered ? 1 : 0,
          transition: 'opacity 320ms ease',
          pointerEvents: 'none',
          filter: 'blur(8px)',
        }}
      />
      <svg viewBox="0 0 80 80" width={size} height={size} style={{ position: 'relative', zIndex: 1 }}>
        {v < 100 && (
          <circle
            cx="40"
            cy="40"
            r={r}
            fill="none"
            stroke="rgba(255,255,255,0.18)"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${unfilledLen} ${c}`}
            transform={`rotate(${unfilledRotation} 40 40)`}
          />
        )}
        {v > 0 && (
          <circle
            cx="40"
            cy="40"
            r={r}
            fill="none"
            stroke={ACCENT}
            strokeWidth={hovered ? stroke + 1.5 : stroke}
            strokeLinecap="round"
            // Arc is always fully extended  -  no grow-from-zero on
            // hover. The orange ring is the resting visual; hover just
            // thickens the stroke and lights up the surrounding glow.
            strokeDasharray={`${filledLen} ${c}`}
            transform="rotate(-90 40 40)"
            style={{ transition: 'stroke-width 280ms ease' }}
          />
        )}
      </svg>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: CV.darkText,
          fontSize: FONT_DONUT,
          fontFamily: CV_FONT,
          fontWeight: 600,
          letterSpacing: '-0.03em',
          transform: hovered ? 'scale(1.04)' : 'scale(1)',
          transition: 'transform 280ms cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        {Math.round(value)}%
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CardRenderer  -  picks the right card component based on `kind`.
// ---------------------------------------------------------------------------
function CardRenderer(props: {
  card: Card;
  x: number; y: number; w: number; h: number;
  opacity: number; contentT: number; exitT: number; isHero: boolean; heroProgress: number;
}) {
  if (props.card.kind === 'line')        return <LineCard       {...props} card={props.card} />;
  if (props.card.kind === 'pill-bar')    return <PillBarCard    {...props} card={props.card} />;
  if (props.card.kind === 'multi-stats') return <MultiStatsCard {...props} card={props.card} />;
  return <DonutCard {...props} card={props.card} />;
}

// ---------------------------------------------------------------------------
// StageWrapper  -  scales 1080×1080 stage to fit the container width.
// ---------------------------------------------------------------------------
export function StageWrapper({ children }: { children: React.ReactNode }) {
  const outerRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const el = outerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setScale(el.clientWidth / STAGE));
    ro.observe(el);
    setScale(el.clientWidth / STAGE);
    return () => ro.disconnect();
  }, []);
  return (
    <div ref={outerRef} style={{ position: 'absolute', inset: 0, overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: STAGE,
          height: STAGE,
          transformOrigin: 'top left',
          transform: `scale(${scale})`,
        }}
      >
        {children}
      </div>
    </div>
  );
}

