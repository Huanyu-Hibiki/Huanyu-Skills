'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library's own copy of the text-hover composition. Per-project agents must
// NOT edit this file. They work on per-project compositions only.
//
// Two variants ported from /sandbox/text-hover (v1) and /sandbox/text-hover-v2
// (v2). Defaults and baked constants come from the user-signed-off JSON for
// each variant. Knobs exposed at the library level: text, variant (v1|v2),
// lightMode (wires to the global theme toggle), colorCount, and 5 color
// slots  -  only the first `colorCount` are used so the gradient can be 2..5
// stops wide.
// ============================================================================

import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';

// Variant names describe behaviour, not version numbers, so a future preset
// author can read the registry and know what each one does without context.
//   'always-rainbow'  -  the rainbow border + glow are always on; the sweep
//                      reveals a coloured FILL inside the letters.
//   'sweep-to-mono'   -  the rainbow is only visible inside the sweep, then
//                      the text resolves to a clean monochrome at the end of
//                      each loop.
export type TextHoverVariant = 'always-rainbow' | 'sweep-to-mono';

export type TextHoverProps = {
  text: string;
  variant: TextHoverVariant;
  lightMode: boolean;
  colorCount: number; // 1..5; only the first N colors are used in the gradient
  color1: string;
  color2: string;
  color3: string;
  color4: string;
  color5: string;
};

export const TextHoverDefaults: TextHoverProps = {
  text: 'CURVABLE.AI',
  variant: 'always-rainbow',
  lightMode: false,
  colorCount: 2,
  color1: '#f04e23',
  color2: '#ff3300',
  color3: '#afcdfd',
  color4: '#d56307',
  color5: '#f75f5f',
};

const FPS = 30;
const STAGE_W = 1920;
const STAGE_H = 1080;

// Internal SVG canvas  -  the text and sweep math live in viewBox coords.
const VIEWBOX_W = 300;
const VIEWBOX_H = 100;
const TEXT_CX = VIEWBOX_W / 2;
const TEXT_CY = VIEWBOX_H / 2;
// Horizontal padding kept clear of glyph + caret so long strings shrink to
// fit the canvas instead of running off the edge. Expressed as a fraction of
// VIEWBOX_W so the visible margin reads as roughly 10% per side at any
// preview size  -  keeps the text centred with breathing room in the grid
// card the same way it does in the full-size dashboard preview.
const SAFE_INNER_WIDTH = VIEWBOX_W - 60;

// Baked from the user-signed-off v2 JSON. v1 inherits the same shared values
// (sweep + bezier + font); only the glow stack differs.
const SWEEP_DURATION_S = 4;
const SWEEP_WIDTH = 172;
const SWEEP_FADE_PCT = 50;
const SWEEP_ANGLE = 6;
const FONT_SIZE = 70;
const STROKE_WIDTH = 0.15;
const BEZIER = { p1x: 0.76, p1y: 0, p2x: 0.24, p2y: 1 };

// V2 glow (always-on, opacity-light). From the v2 sandbox sign-off.
const GLOW_STACK_V2: { id: number; spread: number; blur: number; opacity: number }[] = [
  { id: 1, spread: 0.9,  blur: 1.95, opacity: 0 },
  { id: 2, spread: 2.1,  blur: 2.25, opacity: 0.29 },
  { id: 3, spread: 9.65, blur: 2.5,  opacity: 0 },
];

// V1 glow (sweep-masked, fades during the settle). From the v1 sandbox sign-off.
const GLOW_STACK_V1: { id: number; spread: number; blur: number; opacity: number }[] = [
  { id: 1, spread: 0.7,  blur: 1.6, opacity: 1 },
  { id: 2, spread: 2.7,  blur: 1.7, opacity: 0.31 },
  { id: 3, spread: 9.65, blur: 2.5, opacity: 0.14 },
];

const TOTAL_FRAMES = Math.max(1, Math.round(SWEEP_DURATION_S * FPS));

// Global fade-in/out envelope wrapped around the whole composition. Both
// variants use it: text starts invisible, fades up over FADE_FRAMES, holds
// at full opacity, then fades back down before the loop wraps. Applied to
// the SVG element only  -  the background stays opaque so loop boundaries
// don't flash.
const FADE_FRAMES = Math.max(1, Math.round(0.4 * FPS)); // 0.4 s in/out

export const TextHoverMeta = {
  width: STAGE_W,
  height: STAGE_H,
  fps: FPS,
  durationFrames: TOTAL_FRAMES,
};

export const computeTextHoverDuration = (): number => TOTAL_FRAMES;

// ----------------------------------------------------------------------------
// Internal helpers.
// ----------------------------------------------------------------------------

function bezierXY(t: number, p1x: number, p1y: number, p2x: number, p2y: number): [number, number] {
  const u = 1 - t;
  const x = 3 * u * u * t * p1x + 3 * u * t * t * p2x + t * t * t;
  const y = 3 * u * u * t * p1y + 3 * u * t * t * p2y + t * t * t;
  return [x, y];
}

function bezierEase(progress: number): number {
  let lo = 0;
  let hi = 1;
  for (let i = 0; i < 24; i++) {
    const mid = (lo + hi) / 2;
    const [x] = bezierXY(mid, BEZIER.p1x, BEZIER.p1y, BEZIER.p2x, BEZIER.p2y);
    if (x < progress) lo = mid;
    else hi = mid;
  }
  const [, y] = bezierXY((lo + hi) / 2, BEZIER.p1x, BEZIER.p1y, BEZIER.p2x, BEZIER.p2y);
  return y;
}

// SSR-safe text width measurement with a fallback that errs on the side of
// "this string is wider than you think". Canvas measureText uses whatever
// font is currently resolved  -  if helvetica hasn't loaded yet, it falls back
// to the system font (often narrower) and we'd auto-clamp the font size to
// a value that overflows once helvetica eventually paints. The 1.18 fudge
// factor covers most realistic system→helvetica width gaps so the text
// always fits the SAFE_INNER_WIDTH band on the first paint.
const WIDTH_SAFETY_FACTOR = 1.18;

function measureText(text: string, fontSize: number): number {
  // SSR / no-text path: estimate from char count so the SSR snapshot already
  // picks a font size that fits, instead of trusting "fits by default" and
  // overflowing on the client.
  if (typeof document === 'undefined' || !text) {
    return text.length * fontSize * 0.6;
  }
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return text.length * fontSize * 0.6;
  ctx.font = `700 ${fontSize}px helvetica, system-ui, sans-serif`;
  return ctx.measureText(text).width * WIDTH_SAFETY_FACTOR;
}

const textStyle = (fontSize: number): React.CSSProperties => ({
  fontFamily: 'helvetica, system-ui, sans-serif',
  fontWeight: 700,
  fontSize,
});

// ----------------------------------------------------------------------------
// Component.
// ----------------------------------------------------------------------------

export const TextHover: React.FC<TextHoverProps> = ({
  text,
  variant,
  lightMode,
  colorCount,
  color1,
  color2,
  color3,
  color4,
  color5,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const bgColor = lightMode ? '#FAFAF7' : '#0a0a0a';
  const strokeColor = lightMode ? '#000000' : '#ffffff';

  // 1..5 colors, evenly distributed across the gradient. With one stop the
  // gradient resolves to a single solid colour everywhere.
  const allColors = [color1, color2, color3, color4, color5];
  const n = Math.max(1, Math.min(5, Math.round(colorCount)));
  const colors = allColors.slice(0, n);

  // Auto-clamp font size so the text always fits the safe inner width.
  const measuredAtMax = measureText(text, FONT_SIZE);
  const effectiveFontSize =
    measuredAtMax <= SAFE_INNER_WIDTH ? FONT_SIZE : Math.max(8, FONT_SIZE * (SAFE_INNER_WIDTH / measuredAtMax));
  const textWidth = measureText(text, effectiveFontSize);

  // Sweep travel: starts off the LEFT of the text (text-anchored so we don't
  // burn time over empty space), ends fully off the RIGHT of the SCREEN.
  const SLACK = 4;
  const textHalfW = textWidth / 2;
  const startX = TEXT_CX - textHalfW - SWEEP_WIDTH / 2 - SLACK;
  const endX = VIEWBOX_W + SWEEP_WIDTH / 2 + SLACK;

  const sweepProgress = Math.min(1, frame / Math.max(1, TOTAL_FRAMES * (fps / FPS)));
  const easedProgress = bezierEase(sweepProgress);
  const rectCx = startX + (endX - startX) * easedProgress;

  // V1-only: position-driven fade-to-mono. Triggers once the rect's CENTER
  // crosses the viewport's right edge, completes when the rect is fully off.
  const fadeStartCx = VIEWBOX_W;
  const fadeEndCx = VIEWBOX_W + SWEEP_WIDTH / 2;
  const settleProgress = Math.max(
    0,
    Math.min(1, (rectCx - fadeStartCx) / Math.max(0.0001, fadeEndCx - fadeStartCx)),
  );
  const interiorFillOpacity = settleProgress;
  const glowOpacityMul = 1 - settleProgress;

  const glowStack = variant === 'sweep-to-mono' ? GLOW_STACK_V1 : GLOW_STACK_V2;
  const fadePct = Math.max(0, Math.min(50, SWEEP_FADE_PCT));
  const RECT_H = VIEWBOX_H * 4;

  // Linear fade-in/out envelope  -  opacity 0 at frame 0, ramps to 1 over
  // FADE_FRAMES, holds, then ramps back to 0 over the last FADE_FRAMES.
  const fadeFrames = Math.min(FADE_FRAMES, Math.floor(TOTAL_FRAMES / 2));
  const envelopeOpacity =
    frame < fadeFrames
      ? frame / fadeFrames
      : frame > TOTAL_FRAMES - fadeFrames
        ? Math.max(0, (TOTAL_FRAMES - frame) / fadeFrames)
        : 1;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: bgColor,
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}
        preserveAspectRatio="xMidYMid meet"
        xmlns="http://www.w3.org/2000/svg"
        // overflow: visible so the glow halo extends beyond the 3:1 viewBox
        // into the surrounding 16:9 stage area. Opacity envelope fades the
        // entire text in at start and out at end of every loop.
        style={{ overflow: 'visible', opacity: envelopeOpacity }}
      >
        <defs>
          {/* Rainbow gradient stretched across the viewBox. Stops are
              distributed evenly across however many colours the user has
              configured (2..5). */}
          <linearGradient id="thx-tg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2={VIEWBOX_W} y2="0">
            {colors.map((c, i) => (
              <stop
                key={i}
                offset={`${colors.length === 1 ? 0 : (i / (colors.length - 1)) * 100}%`}
                stopColor={c}
              />
            ))}
          </linearGradient>

          {/* Soft-edged horizontal fade for the sweep rect: black → white → white → black. */}
          <linearGradient id="thx-sf" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="black" />
            <stop offset={`${fadePct}%`} stopColor="white" />
            <stop offset={`${100 - fadePct}%`} stopColor="white" />
            <stop offset="100%" stopColor="black" />
          </linearGradient>

          {/* Sweep mask. Oversized region so the blurred glow halo isn't
              clipped by the mask's default ~120% bounding box. */}
          <mask
            id="thx-sm"
            maskUnits="userSpaceOnUse"
            x={-VIEWBOX_W}
            y={-VIEWBOX_H}
            width={VIEWBOX_W * 3}
            height={VIEWBOX_H * 3}
          >
            <rect x={-VIEWBOX_W} y={-VIEWBOX_H} width={VIEWBOX_W * 3} height={VIEWBOX_H * 3} fill="black" />
            <g transform={`rotate(${SWEEP_ANGLE} ${TEXT_CX} ${TEXT_CY})`}>
              <rect
                x={rectCx - SWEEP_WIDTH / 2}
                y={TEXT_CY - RECT_H / 2}
                width={SWEEP_WIDTH}
                height={RECT_H}
                fill="url(#thx-sf)"
              />
            </g>
          </mask>

          {/* One Gaussian blur filter per glow layer, with a generous filter
              region so the blurred halo doesn't clip at the source bbox. */}
          {glowStack.map((l) => (
            <filter
              key={`g-${l.id}`}
              id={`thx-g-${l.id}`}
              x="-100%"
              y="-100%"
              width="300%"
              height="300%"
            >
              <feGaussianBlur stdDeviation={Math.max(0, l.blur)} />
            </filter>
          ))}
        </defs>

        {variant === 'always-rainbow' ? (
          <>
            {/* V2: always-on rainbow border + always-on glow + sweep-revealed
                interior fill (rainbow). No fade-to-mono. */}
            {glowStack.slice().reverse().map((l) => (
              <text
                key={`g-${l.id}`}
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="middle"
                stroke="url(#thx-tg)"
                strokeWidth={STROKE_WIDTH + l.spread}
                fill="transparent"
                filter={`url(#thx-g-${l.id})`}
                opacity={Math.max(0, Math.min(1, l.opacity))}
                style={textStyle(effectiveFontSize)}
              >
                {text}
              </text>
            ))}
            <text
              x="50%"
              y="50%"
              textAnchor="middle"
              dominantBaseline="middle"
              stroke="url(#thx-tg)"
              strokeWidth={STROKE_WIDTH}
              fill="transparent"
              style={textStyle(effectiveFontSize)}
            >
              {text}
            </text>
            <text
              x="50%"
              y="50%"
              textAnchor="middle"
              dominantBaseline="middle"
              fill="url(#thx-tg)"
              stroke="none"
              mask="url(#thx-sm)"
              style={textStyle(effectiveFontSize)}
            >
              {text}
            </text>
          </>
        ) : (
          <>
            {/* V1: sweep-masked rainbow stroke + fades to mono at the end of
                the loop. Glow is sweep-masked too, fades out during settle. */}
            {glowStack.slice().reverse().map((l) => (
              <text
                key={`g-${l.id}`}
                x="50%"
                y="50%"
                textAnchor="middle"
                dominantBaseline="middle"
                stroke="url(#thx-tg)"
                strokeWidth={STROKE_WIDTH + l.spread}
                fill="transparent"
                mask="url(#thx-sm)"
                filter={`url(#thx-g-${l.id})`}
                opacity={Math.max(0, Math.min(1, l.opacity * glowOpacityMul))}
                style={textStyle(effectiveFontSize)}
              >
                {text}
              </text>
            ))}
            {/* Bg cutout  -  hides any glow that bled inside the letter. */}
            <text
              x="50%"
              y="50%"
              textAnchor="middle"
              dominantBaseline="middle"
              fill={bgColor}
              stroke="none"
              style={textStyle(effectiveFontSize)}
            >
              {text}
            </text>
            {/* Settle interior fill  -  fades in to mono during the rect's exit. */}
            <text
              x="50%"
              y="50%"
              textAnchor="middle"
              dominantBaseline="middle"
              fill={strokeColor}
              stroke="none"
              opacity={Math.max(0, Math.min(1, interiorFillOpacity))}
              style={textStyle(effectiveFontSize)}
            >
              {text}
            </text>
            {/* Static neutral border  -  always visible. */}
            <text
              x="50%"
              y="50%"
              textAnchor="middle"
              dominantBaseline="middle"
              stroke={strokeColor}
              strokeWidth={STROKE_WIDTH}
              fill="transparent"
              style={textStyle(effectiveFontSize)}
            >
              {text}
            </text>
            {/* Rainbow stroke under the sweep mask. */}
            <text
              x="50%"
              y="50%"
              textAnchor="middle"
              dominantBaseline="middle"
              stroke="url(#thx-tg)"
              strokeWidth={STROKE_WIDTH}
              fill="transparent"
              mask="url(#thx-sm)"
              style={textStyle(effectiveFontSize)}
            >
              {text}
            </text>
          </>
        )}
      </svg>
    </AbsoluteFill>
  );
};
