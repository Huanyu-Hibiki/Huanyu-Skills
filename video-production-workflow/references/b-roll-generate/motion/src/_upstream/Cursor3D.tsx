'use client';

// LP-OWNED COPY of the 3D cursor. Forked from
// apps/web/app/projects/[id]/_components/compositions/curvable-launch/Cursor3D.tsx
// so the LP can iterate on cursor render quality without touching the per-
// project seed.
//
// Local change vs. seed: the cursor SVG layers now render at 4× their native
// pixel size and the container is counter-scaled by 0.25 to keep the visual
// size identical. Reason: when the parent applies 3D rotations + scale (the
// MiniDashboard wrapper does), browsers rasterize each SVG at its CSS size
// BEFORE applying the 3D transform  -  so a 96px cursor under scale(1.65) +
// rotateX/Y looks pixelated. Rendering at 4× then compositing through the
// 0.25 scale gives the GPU a 384px backing store to transform from.

import React from 'react';

const CURSOR_PATH =
  'M42.6817 41.1495L27.5103 6.79925C26.7269 5.02557 24.2082 5.02558 23.3927 6.79925L7.59814 41.1495C6.75833 42.9759 8.52712 44.8902 10.4125 44.1954L24.3757 39.0496C24.8829 38.8627 25.4385 38.8627 25.9422 39.0496L39.8121 44.1954C41.6849 44.8902 43.4884 42.9759 42.6817 41.1495Z';
const CURSOR_VIEWBOX = '-23 -21 96 96';

// High-DPI render size  -  backing store the GPU uses when 3D-transforming.
// 4× the 96px logical size gives crisp edges through scale(1.65) + rotate.
const NATIVE_SIZE = 384;
const COUNTER_SCALE = 96 / NATIVE_SIZE; // 0.25

// Z offsets are in the rendered-pixel coordinate space, so they must scale
// with NATIVE_SIZE too  -  otherwise the extrusion gets thinner as we upscale.
const Z_SCALE = NATIVE_SIZE / 96;

// Z offsets in the cursor's own (1× = 96px) coordinate space; multiplied by
// (Z_SCALE × depth) at render time so we get a high-DPI backing store AND a
// dial-in depth multiplier.
// 7-layer extrusion stack. Each layer reads its colour from a CSS variable
// so the library Prompt-input wrapper can recolour the whole cursor by
// derivation from the global brand `primary`. The fallback hexes are the
// signoff orange shades  -  LP and per-project copies stay identical when
// no ancestor sets the vars.
const STACK_BASE = [
  { zBase: 0,  fill: 'var(--cv-cursor-l0, #5C1808)' },
  { zBase: 2,  fill: 'var(--cv-cursor-l1, #73210C)' },
  { zBase: 4,  fill: 'var(--cv-cursor-l2, #8A2A10)' },
  { zBase: 6,  fill: 'var(--cv-cursor-l3, #A03414)' },
  { zBase: 8,  fill: 'var(--cv-cursor-l4, #B53D17)' },
  { zBase: 10, fill: 'var(--cv-cursor-l5, #C8451A)' },
  { zBase: 12, fill: 'var(--cv-cursor-l6, #DD4D1F)' },
];
const TOP_Z_BASE = 14;

export const Cursor3D: React.FC<{
  x: number;
  y: number;
  scale: number;
  tiltX?: number;
  tiltY?: number;
  // In-plane rotation, applied on top of the cursor's intrinsic -25° pose
  // (so 0 means "default arrow direction", +/- rotates from there).
  tiltZ?: number;
  // Multiplier on the Z extrusion stack  -  1 = the seed's depth, 2 = twice as
  // thick. Visible only when the cursor is rotated off-axis (tiltX/Y != 0).
  depth?: number;
  opacity?: number;
}> = ({ x, y, scale, tiltX = 0, tiltY = 0, tiltZ = 0, depth = 1, opacity = 1 }) => {
  const depthScale = depth * Z_SCALE;
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: NATIVE_SIZE,
        height: NATIVE_SIZE,
        transformOrigin: '50% 50%',
        transform: [
          // Centre the larger cursor on (x, y).
          `translate(-${NATIVE_SIZE / 2}px, -${NATIVE_SIZE / 2}px)`,
          // Counter-scale back to the original visual size.
          `scale(${COUNTER_SCALE})`,
          // Float in front of the dashboard plane in the preserve-3d stack.
          `translateZ(${60 * Z_SCALE}px)`,
          `rotateX(${tiltX}deg)`,
          `rotateY(${tiltY}deg)`,
          `rotateZ(${-25 + tiltZ}deg)`,
          `scale(${scale})`,
        ].join(' '),
        transformStyle: 'preserve-3d',
        opacity,
        pointerEvents: 'none',
        filter: `drop-shadow(0 ${6 * Z_SCALE}px ${14 * Z_SCALE}px rgba(0,0,0,0.45))`,
        willChange: 'transform',
      }}
    >
      {STACK_BASE.map((layer, i) => (
        <svg
          key={i}
          xmlns="http://www.w3.org/2000/svg"
          width={NATIVE_SIZE}
          height={NATIVE_SIZE}
          viewBox={CURSOR_VIEWBOX}
          fill="none"
          style={{
            position: 'absolute',
            inset: 0,
            transform: `translateZ(${layer.zBase * depthScale}px)`,
          }}
        >
          <path d={CURSOR_PATH} fill={layer.fill} />
        </svg>
      ))}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width={NATIVE_SIZE}
        height={NATIVE_SIZE}
        viewBox={CURSOR_VIEWBOX}
        fill="none"
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translateZ(${TOP_Z_BASE * depthScale}px)`,
        }}
      >
        <defs>
          <linearGradient id="cv-lp-cursor-fill" x1="0" y1="0" x2="0" y2="1">
            {/* Same CSS-var pattern as STACK_BASE: the visible front face's
                top → middle → bottom gradient stops follow the brand. */}
            <stop offset="0" stopColor="var(--cv-cursor-top, #FF7A52)" />
            <stop offset="0.55" stopColor="var(--cv-cursor-mid, #F04E23)" />
            <stop offset="1" stopColor="var(--cv-cursor-bot, #B23914)" />
          </linearGradient>
          <linearGradient id="cv-lp-cursor-highlight" x1="0" y1="0" x2="0.4" y2="1">
            <stop offset="0" stopColor="rgba(255,255,255,0.75)" />
            <stop offset="0.45" stopColor="rgba(255,255,255,0)" />
          </linearGradient>
        </defs>
        <path
          d={CURSOR_PATH}
          fill="url(#cv-lp-cursor-fill)"
          stroke="white"
          strokeWidth={2.25825}
          strokeLinejoin="round"
        />
        <path
          d="M27.5103 6.79925C26.7269 5.02557 24.2082 5.02558 23.3927 6.79925L7.59814 41.1495C7.0 42.3 7.6 43.3 8.6 43.3L25 23 Z"
          fill="url(#cv-lp-cursor-highlight)"
          opacity={0.6}
        />
      </svg>
    </div>
  );
};
