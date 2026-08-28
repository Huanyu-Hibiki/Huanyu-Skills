'use client';

// LIVE source of truth for the LP "Floating stack" template tile.
// Owns the Stage, Slab geometry, StageWrapper, defaults, types, and
// math helpers. The sandbox at /sandbox/floating-stack imports from
// here and adds editor chrome on top  -  live never imports from
// sandbox (option-B inversion).

import React, { useEffect, useRef, useState } from 'react';
import { Cursor3D } from '../Cursor3D';

export const STAGE = 1080;

// ---------------------------------------------------------------------------
// State.
// ---------------------------------------------------------------------------
export type StackState = {
  // 3D camera.
  perspective: number;
  rotateX: number;
  rotateY: number;
  // Slab geometry  -  same dims applied to all three.
  slabWidth: number;
  slabDepth: number;
  slabThickness: number;
  gap: number;
  // Whole-stack nudge so the user can compose against the tile bounds.
  stackOffsetX: number;
  stackOffsetY: number;
  // Float  -  independent per slab via phase stagger.
  floatAmplitude: number;
  floatPeriod: number;       // seconds for one full bob cycle
  floatPhaseStagger: number; // 0..1 fraction of a period offset between slabs
  // Cursor  -  pose + per-stop anchor positions in stage screen coords.
  // off = entry/exit parking spot. top/mid/bot = hover stop for each slab.
  cursorScale: number;
  cursorTiltX: number;
  cursorTiltY: number;
  cursorTiltZ: number;
  cursorOffX: number; cursorOffY: number;
  cursorTopX: number; cursorTopY: number;
  cursorMidX: number; cursorMidY: number;
  cursorBotX: number; cursorBotY: number;
  // Highlight tints  -  applied to top / sides / bottom faces when a
  // slab is in the hover state (glow lerps from base grey → these).
  glowTop: string;
  glowSide: string;
  glowBottom: string;
  // Per-stop glow timings (seconds within the 10s loop). "On" = the
  // moment glow reaches full 1; "Off" = the moment glow returns to 0.
  // The 0.45s ramps in/out are placed BEFORE / AFTER these values.
  topGlowOnT: number;  topGlowOffT: number;
  midGlowOnT: number;  midGlowOffT: number;
  botGlowOnT: number;  botGlowOffT: number;
};

export const DEFAULT_STATE: StackState = {
  perspective: 1500,
  rotateX: -29.5,
  rotateY: -27.5,
  slabWidth: 540,
  slabDepth: 540,
  slabThickness: 80,
  gap: 80,
  stackOffsetX: 0,
  stackOffsetY: 0,
  floatAmplitude: 20,
  floatPeriod: 3.1,
  floatPhaseStagger: 0.23,
  cursorScale: 2.00,
  cursorTiltX: -16,
  cursorTiltY: -2,
  cursorTiltZ: 7,
  cursorOffX: 540, cursorOffY: 1260,
  cursorTopX: 557, cursorTopY: 584,
  cursorMidX: 602, cursorMidY: 742,
  cursorBotX: 631, cursorBotY: 851,
  glowTop:    '#da3d16',
  glowSide:   '#ae2f19',
  glowBottom: '#3F0F05',
  topGlowOnT: 1.05, topGlowOffT: 3.45,
  midGlowOnT: 3.60, midGlowOffT: 6.15,
  botGlowOnT: 6.35, botGlowOffT: 8.80,
};

export const SLAB_COUNT = 3;

// ---------------------------------------------------------------------------
// Stage  -  three slabs + cursor on a tilted plane.
// ---------------------------------------------------------------------------
export function Stage({
  state,
  paused = false,
  tSecOverride,
}: {
  state: StackState;
  paused?: boolean;
  // Optional external clock  -  when set, the rAF loop is bypassed and
  // tSec is driven by this value instead. Used by the Remotion render
  // pipeline to produce deterministic frames (frame / fps).
  tSecOverride?: number;
}) {
  // tSec is the effective animation clock. When paused, it freezes at
  // the moment of pause; on resume it advances from the same value
  // without jumping  -  same trick as the existing stats-cards transport.
  const [tSecState, setTSec] = useState(0);
  const pauseAccumRef = useRef(0);
  const pauseStartRef = useRef<number | null>(null);
  useEffect(() => {
    if (tSecOverride !== undefined) return; // external clock  -  skip rAF
    let raf = 0;
    const loop = () => {
      const now = performance.now() / 1000;
      if (paused) {
        if (pauseStartRef.current == null) pauseStartRef.current = now;
      } else {
        if (pauseStartRef.current != null) {
          pauseAccumRef.current += now - pauseStartRef.current;
          pauseStartRef.current = null;
        }
        setTSec(now - pauseAccumRef.current);
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [paused, tSecOverride]);

  const tSec = tSecOverride !== undefined ? tSecOverride : tSecState;

  const period = Math.max(0.1, state.floatPeriod);
  const floatYFor = (idx: number) => {
    if (state.floatAmplitude <= 0) return 0;
    const phase = idx * state.floatPhaseStagger;
    return Math.sin((tSec / period + phase) * 2 * Math.PI) * state.floatAmplitude;
  };

  const step = state.slabThickness + state.gap;
  const totalH = (SLAB_COUNT - 1) * step;
  const baseY = -totalH / 2;
  const slabBaseWorldY = (visualIdx: number) =>
    baseY + (SLAB_COUNT - 1 - visualIdx) * step;

  const LOOP_TOTAL = 10;
  const OFF = { x: state.cursorOffX, y: state.cursorOffY };
  const TOP = { x: state.cursorTopX, y: state.cursorTopY };
  const MID = { x: state.cursorMidX, y: state.cursorMidY };
  const BOT = { x: state.cursorBotX, y: state.cursorBotY };

  const RAMP = 0.45;

  type PosKey = { t: number; x: number; y: number };
  const cursorKeys: PosKey[] = [
    { t: 0.0,  x: OFF.x, y: OFF.y },
    { t: 0.85, x: TOP.x, y: TOP.y },
    { t: 3.05, x: TOP.x, y: TOP.y },
    { t: 3.60, x: MID.x, y: MID.y },
    { t: 5.75, x: MID.x, y: MID.y },
    { t: 6.30, x: BOT.x, y: BOT.y },
    { t: 8.30, x: BOT.x, y: BOT.y },
    { t: 9.10, x: OFF.x, y: OFF.y },
    { t: LOOP_TOTAL, x: OFF.x, y: OFF.y },
  ];

  const tLoop = ((tSec % LOOP_TOTAL) + LOOP_TOTAL) % LOOP_TOTAL;
  let kIdx = 0;
  for (let i = 0; i < cursorKeys.length - 1; i++) {
    if (tLoop >= cursorKeys[i]!.t && tLoop < cursorKeys[i + 1]!.t) { kIdx = i; break; }
  }
  const k0 = cursorKeys[kIdx]!;
  const k1 = cursorKeys[kIdx + 1]!;
  const span = Math.max(0.0001, k1.t - k0.t);
  const u = smoothstep(clamp01((tLoop - k0.t) / span));
  const cursorX = k0.x + (k1.x - k0.x) * u;
  const cursorY = k0.y + (k1.y - k0.y) * u;

  const computeGlow = (onT: number, offT: number) => {
    if (offT <= onT) return 0;
    const entry = onT - RAMP;
    const exit = offT - RAMP;
    if (tLoop < entry) return 0;
    if (tLoop < onT)   return smoothstep((tLoop - entry) / RAMP);
    if (tLoop < exit)  return 1;
    if (tLoop < offT)  return 1 - smoothstep((tLoop - exit) / RAMP);
    return 0;
  };
  const slabGlow = [
    computeGlow(state.botGlowOnT, state.botGlowOffT),
    computeGlow(state.midGlowOnT, state.midGlowOffT),
    computeGlow(state.topGlowOnT, state.topGlowOffT),
  ];
  const hoverIntensityFor = (visualIdx: number) => slabGlow[visualIdx] ?? 0;

  const PUSH_AMOUNT = 26;
  const slabs = Array.from({ length: SLAB_COUNT }).map((_, i) => {
    const visualIdx = (SLAB_COUNT - 1) - i;
    const baseWY = slabBaseWorldY(visualIdx);
    let pushY = 0;
    for (let h = 0; h < SLAB_COUNT; h++) {
      if (h === visualIdx) continue;
      const intensity = hoverIntensityFor(h);
      if (intensity <= 0) continue;
      const hWY = slabBaseWorldY(h);
      const dir = baseWY < hWY ? -1 : 1;
      pushY += dir * PUSH_AMOUNT * intensity;
    }
    return {
      idx: i,
      visualIdx,
      y: baseWY + floatYFor(i) + pushY,
      glow: hoverIntensityFor(visualIdx),
    };
  });

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          perspective: `${state.perspective}px`,
          perspectiveOrigin: '50% 50%',
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            width: 0,
            height: 0,
            transformStyle: 'preserve-3d',
            transform: `translate(${state.stackOffsetX}px, ${state.stackOffsetY}px) rotateX(${state.rotateX}deg) rotateY(${state.rotateY}deg)`,
          }}
        >
          {slabs.map((slab) => (
            <Slab
              key={slab.idx}
              y={slab.y}
              width={state.slabWidth}
              depth={state.slabDepth}
              thickness={state.slabThickness}
              glow={slab.glow}
              glowTop={state.glowTop}
              glowSide={state.glowSide}
              glowBottom={state.glowBottom}
            />
          ))}
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: cursorX,
          top: cursorY,
          width: 0,
          height: 0,
          perspective: '1500px',
          pointerEvents: 'none',
        }}
      >
        <Cursor3D
          x={0}
          y={0}
          scale={state.cursorScale}
          tiltX={state.cursorTiltX}
          tiltY={state.cursorTiltY}
          tiltZ={state.cursorTiltZ}
        />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers (exported for the sandbox + any future preset library).
// ---------------------------------------------------------------------------
export function clamp01(n: number) {
  return Math.max(0, Math.min(1, n));
}

export function smoothstep(t: number) {
  return t * t * (3 - 2 * t);
}

export function mixHex(a: string, b: string, t: number): string {
  const u = Math.max(0, Math.min(1, t));
  const ah = a.replace('#', '');
  const bh = b.replace('#', '');
  const ar = parseInt(ah.slice(0, 2), 16);
  const ag = parseInt(ah.slice(2, 4), 16);
  const ab = parseInt(ah.slice(4, 6), 16);
  const br = parseInt(bh.slice(0, 2), 16);
  const bg = parseInt(bh.slice(2, 4), 16);
  const bb = parseInt(bh.slice(4, 6), 16);
  const r = Math.round(ar + (br - ar) * u);
  const g = Math.round(ag + (bg - ag) * u);
  const bl = Math.round(ab + (bb - ab) * u);
  return `rgb(${r}, ${g}, ${bl})`;
}

// ---------------------------------------------------------------------------
// Slab  -  a 3D box (W × T × D) built from six CSS-3D faces using the
// canonical cube pattern: container is a zero-size transform anchor
// at the slab's centre; every face is centred on the same origin via
// left:50% / top:50% + negative margin, then rotated and pushed out
// along its own local Z by half the perpendicular box dimension.
// ---------------------------------------------------------------------------
function Slab({
  y, width, depth, thickness, glow = 0,
  glowTop = '#7A1F0A', glowSide = '#5C1808', glowBottom = '#2E0B04',
}: {
  y: number; width: number; depth: number; thickness: number;
  glow?: number;
  glowTop?: string;
  glowSide?: string;
  glowBottom?: string;
}) {
  const TOP    = mixHex('#272725', glowTop,    glow);
  const SIDE   = mixHex('#1c1c1c', glowSide,   glow);
  const BOTTOM = mixHex('#0d0d0d', glowBottom, glow);
  const EDGE   = '1px solid rgba(255,255,255,0.04)';

  const W = width;
  const T = thickness;
  const D = depth;

  const face = (
    faceW: number, faceH: number, transform: string,
    background: string, extra?: React.CSSProperties,
  ): React.CSSProperties => ({
    position: 'absolute',
    left: '50%',
    top: '50%',
    width: faceW,
    height: faceH,
    marginLeft: -faceW / 2,
    marginTop: -faceH / 2,
    background,
    transform,
    backfaceVisibility: 'hidden',
    ...extra,
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        width: 0,
        height: 0,
        transformStyle: 'preserve-3d',
        transform: `translateY(${y}px)`,
        // NOTE: do NOT apply `filter` here. CSS `filter` creates a
        // stacking context that flattens `transform-style: preserve-3d`
        // children  -  the cube collapses into a 2D plane.
      }}
    >
      <div style={face(W, D, `rotateX(90deg) translateZ(${T / 2}px)`, TOP, {
        boxShadow: `inset 0 0 0 1px rgba(255,255,255,${0.05 + glow * 0.15})`,
      })} />
      <div style={face(W, D, `rotateX(-90deg) translateZ(${T / 2}px)`, BOTTOM)} />
      <div style={face(W, T, `translateZ(${D / 2}px)`, SIDE, { borderTop: EDGE, borderBottom: EDGE })} />
      <div style={face(W, T, `rotateY(180deg) translateZ(${D / 2}px)`, SIDE, { borderTop: EDGE, borderBottom: EDGE })} />
      <div style={face(D, T, `rotateY(90deg) translateZ(${W / 2}px)`, SIDE, { borderTop: EDGE, borderBottom: EDGE })} />
      <div style={face(D, T, `rotateY(-90deg) translateZ(${W / 2}px)`, SIDE, { borderTop: EDGE, borderBottom: EDGE })} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// StageWrapper  -  scales the 1080×1080 stage to fit its container width.
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
