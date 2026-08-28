'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library's own copy of the "paste pill" beat. WordSpring text reveal with a
// shining orange pill on the matched word, a 3D cursor that flies up from
// below, dips on the click, and the pill swaps to a grey "Pasted" label.
// Tuned in /sandbox/paste-pill; all motion + timing values baked here.
//
// Imports: react, remotion. NO @curvable/shared, NO per-project paths.
// Cursor3D is inlined below (originally lived in
// projects-v2/.../curvable-launch/Cursor3D.tsx) so the library is fully
// self-contained per hard rule #18.
// ============================================================================

import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from 'remotion';

const STAGE_W = 1920;
const STAGE_H = 1080;
const FPS = 30;

const BEZIER = Easing.bezier(0.4, 0.0, 0.2, 1);
const WORD_SPRING_X_EASING = Easing.bezier(0.33, 0, 0.67, 1);
const WORD_SPRING_Y_EASING = Easing.bezier(0.45, 0, 0.55, 1);

// Light/dark palette. Only bg + text colour swap with lightMode; every pill
// colour is derived from `primary` and is identical in both modes.
const DARK_BG = '#0a0a0a';
const DARK_TEXT = '#fcfbf8';
const LIGHT_BG = '#f6f4ef';
const LIGHT_TEXT = '#101010';

// Baked motion + timing (from sandbox JSON).
const LEAD_IN_FRAMES = 5;
const WINDOW_IN_DURATION = 30;
const WINDOW_OUT_START_OFFSET = 113;
const WINDOW_OUT_DURATION = 15;
const SWEEP_START_OFFSET = 23;
const SWEEP_DURATION_FRAMES = 80;
const CURSOR_ENTER_OFFSET = 48;
const CURSOR_TRAVEL_FRAMES = 26;
const CLICK_FRAME_OFFSET = 81;
const CURSOR_END_X = 979;
const CURSOR_END_Y = 579;
const CURSOR_START_Y_OFFSET = 177;
const CURSOR_SCALE = 1.65;

// WordSpring motion.
const FONT_SIZE = 76;
const FONT_WEIGHT = 600;
const START_X = 0;
const START_Y = 132;
const ARC_HEIGHT_Y = 41;
const OVERSHOOT_X = 0;
const BOUNCE_Y = 27;
const ARC_PEAK_T = 0.5;
const BOUNCE_FRAMES = 10;
const SETTLE_T = 0.5;
const BOUNCE_RETURN = 0;
const WORD_STAGGER = 4;
const FADE_IN_FRAMES = 6;
const BLUR_DOWN = 0;
const COMMA_PAUSE_FRAMES = 18;
const ANIM_FRAMES = 31;

// Pill geometry.
const PILL_FONT_SIZE = 51;
const PILL_FONT_WEIGHT = 700;
const PILL_BORDER_RADIUS = 999;
const PILL_PADDING_X = 0.8;
const PILL_PADDING_Y = 0.3;
const PILL_MARGIN_X = 0.2;
const PILL_ACTIVE_BACKGROUND = '#3F3F3F';
const PILL_ACTIVE_COLOR = '#ffffff';
const PILL_COLOR = '#ffffff';

export type PastePillProps = {
  primary: string;
  text: string;
  pillWord: string;
  activeLabel: string;
  lightMode: boolean;
};

export const PastePillDefaults: PastePillProps = {
  primary: '#F04E23',
  text: "That's it, Paste the URL",
  pillWord: 'Paste',
  activeLabel: 'Pasted',
  lightMode: false,
};

export const PastePillMeta = {
  width: STAGE_W,
  height: STAGE_H,
  fps: FPS,
};

export const computePastePillDuration = (): number =>
  LEAD_IN_FRAMES + WINDOW_OUT_START_OFFSET + WINDOW_OUT_DURATION;

// ---------------------------------------------------------------------------
// Color helpers  -  derive the pill's plastic gradient stops from primary so
// any user-chosen highlight keeps the brand-coherent triple.
// ---------------------------------------------------------------------------

function shadeHex(hex: string, delta: number): string {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return hex;
  const r = parseInt(m[1]!, 16) / 255;
  const g = parseInt(m[2]!, 16) / 255;
  const b = parseInt(m[3]!, 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l0 = (max + min) / 2;
  const d = max - min;
  let h = 0;
  let s = 0;
  if (d !== 0) {
    s = l0 > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)); break;
      case g: h = ((b - r) / d + 2); break;
      case b: h = ((r - g) / d + 4); break;
    }
    h /= 6;
  }
  const l = Math.max(0, Math.min(1, l0 + delta));
  const hue2rgb = (p: number, q: number, t: number): number => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  let rr: number;
  let gg: number;
  let bb: number;
  if (s === 0) {
    rr = gg = bb = l;
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    rr = hue2rgb(p, q, h + 1 / 3);
    gg = hue2rgb(p, q, h);
    bb = hue2rgb(p, q, h - 1 / 3);
  }
  const to = (v: number) =>
    Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0');
  return `#${to(rr)}${to(gg)}${to(bb)}`;
}

function hexToRgba(hex: string, alpha: number): string {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const r = parseInt(full.substring(0, 2), 16) || 0;
  const g = parseInt(full.substring(2, 4), 16) || 0;
  const b = parseInt(full.substring(4, 6), 16) || 0;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export const PastePill: React.FC<PastePillProps> = ({ primary, text, pillWord, activeLabel, lightMode }) => {
  const frame = useCurrentFrame();
  const bg = lightMode ? LIGHT_BG : DARK_BG;
  const textColor = lightMode ? LIGHT_TEXT : DARK_TEXT;

  const gradientFrom = shadeHex(primary, 0.18);
  const gradientVia = primary;
  const gradientTo = shadeHex(primary, -0.18);

  const lineStart = LEAD_IN_FRAMES;
  const windowIn: readonly [number, number] = [lineStart, lineStart + WINDOW_IN_DURATION];
  const windowOut: readonly [number, number] = [
    lineStart + WINDOW_OUT_START_OFFSET,
    lineStart + WINDOW_OUT_START_OFFSET + WINDOW_OUT_DURATION,
  ];
  const inRange = frame >= windowIn[0] && frame < windowOut[1];
  const beatIn = interpolate(frame, windowIn, [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const beatOut = interpolate(frame, windowOut, [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const beatT = beatIn * beatOut;
  const pillClickFrame = lineStart + CLICK_FRAME_OFFSET;
  const pillSweepStartFrame = lineStart + SWEEP_START_OFFSET;
  const cursorEnterFrame = lineStart + CURSOR_ENTER_OFFSET;

  return (
    <AbsoluteFill style={{ background: bg, overflow: 'hidden' }}>
      {inRange ? (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: textColor,
            opacity: beatT,
          }}
        >
          <WordSpringLine
            frame={frame}
            copy={text}
            pillWord={pillWord}
            startFrame={lineStart}
            pillClickFrame={pillClickFrame}
            pillSweepStartFrame={pillSweepStartFrame}
            pillGradientFrom={gradientFrom}
            pillGradientVia={gradientVia}
            pillGradientTo={gradientTo}
            activeLabel={activeLabel}
          />
          <PillCursor
            frame={frame}
            beatWindowIn={windowIn}
            beatWindowOut={windowOut}
            cursorEnterFrame={cursorEnterFrame}
            clickFrame={pillClickFrame}
            tint={primary}
          />
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// WordSpringLine  -  per-word arc + bounce. The pill word matched
// case-insensitively renders as the gradient pill; everything else is a plain
// inline span.
// ---------------------------------------------------------------------------

function WordSpringLine({
  frame, copy, pillWord, startFrame, pillClickFrame, pillSweepStartFrame,
  pillGradientFrom, pillGradientVia, pillGradientTo, activeLabel,
}: {
  frame: number;
  copy: string;
  pillWord: string;
  startFrame: number;
  pillClickFrame: number;
  pillSweepStartFrame: number;
  pillGradientFrom: string;
  pillGradientVia: string;
  pillGradientTo: string;
  activeLabel: string;
}) {
  const words = copy.split(/\s+/).filter(Boolean);
  const pillTargets = new Set(pillWord.split(',').map((w) => w.trim().toLowerCase()).filter(Boolean));
  const travelFrames = Math.max(1, ANIM_FRAMES);

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'nowrap',
        justifyContent: 'center',
        alignItems: 'baseline',
        gap: '0.28em',
        fontSize: FONT_SIZE,
        fontWeight: FONT_WEIGHT,
        whiteSpace: 'nowrap',
      }}
    >
      {words.map((word, wi) => {
        let commaShift = 0;
        for (let j = 0; j < wi; j++) {
          if (/,$/.test(words[j]!)) commaShift += COMMA_PAUSE_FRAMES;
        }
        const wordStart = startFrame + wi * WORD_STAGGER + commaShift;
        const f = frame - wordStart;
        let x: number;
        let y: number;
        if (f <= travelFrames) {
          const tt = Math.max(0, Math.min(1, f / travelFrames));
          x = interpolate(tt, [0, 1], [START_X, -OVERSHOOT_X], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_SPRING_X_EASING,
          });
          y = interpolate(tt, [0, ARC_PEAK_T, 1], [START_Y, -ARC_HEIGHT_Y, BOUNCE_Y], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_SPRING_Y_EASING,
          });
        } else {
          const bt = Math.max(0, Math.min(1, (f - travelFrames) / BOUNCE_FRAMES));
          x = interpolate(bt, [0, 1], [-OVERSHOOT_X, 0], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_SPRING_X_EASING,
          });
          if (BOUNCE_RETURN === 0) {
            y = interpolate(bt, [0, 1], [BOUNCE_Y, 0], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_SPRING_Y_EASING,
            });
          } else {
            y = interpolate(bt, [0, SETTLE_T, 1], [BOUNCE_Y, -BOUNCE_Y * BOUNCE_RETURN, 0], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_SPRING_Y_EASING,
            });
          }
        }
        const fadeT = interpolate(frame, [wordStart, wordStart + FADE_IN_FRAMES], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const blurAmount = BLUR_DOWN * (1 - fadeT);
        const isPill = pillTargets.has(word.toLowerCase().replace(/[,.!?;:]+$/, ''));

        if (isPill) {
          const active = frame >= pillClickFrame;
          const baseBackground = `linear-gradient(to bottom, ${pillGradientFrom}, ${pillGradientVia}, ${pillGradientTo})`;
          const clickDip = interpolate(
            frame,
            [pillClickFrame - 2, pillClickFrame, pillClickFrame + 6],
            [1, 0.92, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: BEZIER },
          );
          const sweepT = interpolate(
            frame,
            [pillSweepStartFrame, pillSweepStartFrame + SWEEP_DURATION_FRAMES],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: BEZIER },
          );
          const sweepVisible =
            !active &&
            frame >= pillSweepStartFrame &&
            frame < pillSweepStartFrame + SWEEP_DURATION_FRAMES;
          const sweepX = -8 + sweepT * 15;
          const tintHex = active ? PILL_ACTIVE_BACKGROUND : pillGradientTo;
          const fillBackground = active ? PILL_ACTIVE_BACKGROUND : baseBackground;
          return (
            <span
              key={wi}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                verticalAlign: 'middle',
                transform: `translate(${x}px, ${y}px) scale(${clickDip})`,
                opacity: fadeT,
                filter: blurAmount > 0.01 ? `blur(${blurAmount}px)` : undefined,
                willChange: 'transform, opacity, filter',
                marginLeft: `${PILL_MARGIN_X}em`,
                marginRight: `${PILL_MARGIN_X}em`,
                position: 'relative',
                overflow: 'hidden',
                borderRadius: PILL_BORDER_RADIUS,
                fontSize: `${PILL_FONT_SIZE}px`,
                fontWeight: PILL_FONT_WEIGHT,
                lineHeight: 1,
                padding: `${PILL_PADDING_Y}em ${PILL_PADDING_X}em`,
                background: fillBackground,
                color: active ? PILL_ACTIVE_COLOR : PILL_COLOR,
                boxShadow: [
                  `0 2px 8px 0 ${hexToRgba(tintHex, 0.35)}`,
                  `0 1.5px 0 0 rgba(255,255,255,0.25) inset`,
                  `0 -2px 8px 0 ${hexToRgba(tintHex, 0.5)} inset`,
                ].join(', '),
                transition: 'background 80ms linear, color 80ms linear',
              }}
            >
              <span style={{ position: 'relative', zIndex: 10 }}>
                {active ? activeLabel : word}
              </span>
              {sweepVisible && (
                <span
                  aria-hidden
                  style={{
                    position: 'absolute',
                    top: '50%',
                    left: 0,
                    width: '0.4em',
                    height: '20em',
                    background: '#ffffff',
                    transform: `translate(${sweepX}em, -50%) skewX(-10deg)`,
                    filter: 'blur(8px)',
                    pointerEvents: 'none',
                    zIndex: 5,
                  }}
                />
              )}
              <span
                aria-hidden
                style={{
                  position: 'absolute',
                  left: '50%',
                  top: 0,
                  transform: 'translateX(-50%)',
                  width: '80%',
                  height: '40%',
                  borderTopLeftRadius: 9999,
                  borderTopRightRadius: 9999,
                  background:
                    'linear-gradient(180deg, rgba(255,255,255,0.25) 0%, rgba(255,255,255,0) 80%, transparent 100%)',
                  filter: 'blur(1.5px)',
                  pointerEvents: 'none',
                  zIndex: 20,
                }}
              />
              <span
                aria-hidden
                style={{
                  position: 'absolute',
                  inset: 0,
                  borderRadius: PILL_BORDER_RADIUS,
                  boxShadow: [
                    `0 0 0 3px rgba(255,255,255,0.10) inset`,
                    `0 1.5px 0 0 rgba(255,255,255,0.18) inset`,
                    `0 -2px 8px 0 ${hexToRgba(tintHex, 0.18)} inset`,
                  ].join(', '),
                  pointerEvents: 'none',
                  zIndex: 1,
                }}
              />
            </span>
          );
        }
        return (
          <span
            key={wi}
            style={{
              display: 'inline-block',
              transform: `translate(${x}px, ${y}px)`,
              opacity: fadeT,
              filter: blurAmount > 0.01 ? `blur(${blurAmount}px)` : undefined,
              willChange: 'transform, opacity, filter',
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// PillCursor  -  flies up from below stage, settles on the pill, dips on click.
// ---------------------------------------------------------------------------

function PillCursor({
  frame, beatWindowIn, beatWindowOut, cursorEnterFrame, clickFrame, tint,
}: {
  frame: number;
  beatWindowIn: readonly [number, number];
  beatWindowOut: readonly [number, number];
  cursorEnterFrame: number;
  clickFrame: number;
  tint: string;
}) {
  if (frame < beatWindowIn[0] || frame >= beatWindowOut[1]) return null;
  const beatIn = interpolate(frame, beatWindowIn, [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const beatOut = interpolate(frame, beatWindowOut, [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const beatT = beatIn * beatOut;
  const cursorIn = interpolate(frame, [cursorEnterFrame, cursorEnterFrame + 6], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const travelT = interpolate(
    frame,
    [cursorEnterFrame, cursorEnterFrame + CURSOR_TRAVEL_FRAMES],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: BEZIER },
  );
  const startY = STAGE_H + CURSOR_START_Y_OFFSET;
  const x = CURSOR_END_X;
  const y = startY + (CURSOR_END_Y - startY) * travelT;
  const clickDip = interpolate(
    frame,
    [clickFrame - 2, clickFrame, clickFrame + 6],
    [1, 0.7, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: BEZIER },
  );
  const scale = CURSOR_SCALE * clickDip;
  const opacity = beatT * cursorIn;
  return <Cursor3D x={x} y={y} scale={scale} opacity={opacity} tint={tint} />;
}

// ---------------------------------------------------------------------------
// Cursor3D  -  inlined here (originally in projects-v2/.../Cursor3D.tsx) so
// the library has no cross-project imports. Pure SVG, no state.
// ---------------------------------------------------------------------------

const CURSOR_PATH =
  'M42.6817 41.1495L27.5103 6.79925C26.7269 5.02557 24.2082 5.02558 23.3927 6.79925L7.59814 41.1495C6.75833 42.9759 8.52712 44.8902 10.4125 44.1954L24.3757 39.0496C24.8829 38.8627 25.4385 38.8627 25.9422 39.0496L39.8121 44.1954C41.6849 44.8902 43.4884 42.9759 42.6817 41.1495Z';
const CURSOR_VIEWBOX = '-23 -21 96 96';
const CURSOR_TOP_Z = 14;

// Lightness deltas (relative to `tint`) that reproduce the original brand
// orange cursor when tint = #F04E23. Stack runs darkest → lightest along Z;
// top face is a 3-stop gradient (light highlight → tint → darker shadow).
const CURSOR_STACK_DELTAS = [-0.42, -0.36, -0.30, -0.24, -0.18, -0.12, -0.06];
const CURSOR_TOP_GRADIENT_DELTAS: [number, number, number] = [0.12, 0, -0.18];

const Cursor3D: React.FC<{
  x: number;
  y: number;
  scale: number;
  opacity?: number;
  tint: string;
}> = ({ x, y, scale, opacity = 1, tint }) => {
  // Each instance gets a unique gradient id so a paste-pill rendered alongside
  // another tinted cursor in the same DOM doesn't share a fill definition.
  const gradId = React.useId();
  const stackFills = CURSOR_STACK_DELTAS.map((d, i) => ({ z: i * 2, fill: shadeHex(tint, d) }));
  const topStops = CURSOR_TOP_GRADIENT_DELTAS.map((d) => shadeHex(tint, d));
  return (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: 96,
        height: 96,
        transformOrigin: '50% 50%',
        transform: [
          `translate(-48px, -48px)`,
          `translateZ(60px)`,
          `rotateZ(-25deg)`,
          `scale(${scale})`,
        ].join(' '),
        transformStyle: 'preserve-3d',
        opacity,
        pointerEvents: 'none',
        zIndex: 100,
        filter: 'drop-shadow(0 6px 14px rgba(0,0,0,0.45))',
        willChange: 'transform',
      }}
    >
      {stackFills.map((layer, i) => (
        <svg
          key={i}
          xmlns="http://www.w3.org/2000/svg"
          width={96}
          height={96}
          viewBox={CURSOR_VIEWBOX}
          fill="none"
          style={{ position: 'absolute', inset: 0, transform: `translateZ(${layer.z}px)` }}
        >
          <path d={CURSOR_PATH} fill={layer.fill} />
        </svg>
      ))}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width={96}
        height={96}
        viewBox={CURSOR_VIEWBOX}
        fill="none"
        style={{ position: 'absolute', inset: 0, transform: `translateZ(${CURSOR_TOP_Z}px)` }}
      >
        <defs>
          <linearGradient id={`cv-paste-cursor-fill-${gradId}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={topStops[0]} />
            <stop offset="0.55" stopColor={topStops[1]} />
            <stop offset="1" stopColor={topStops[2]} />
          </linearGradient>
          <linearGradient id={`cv-paste-cursor-highlight-${gradId}`} x1="0" y1="0" x2="0.4" y2="1">
            <stop offset="0" stopColor="rgba(255,255,255,0.75)" />
            <stop offset="0.45" stopColor="rgba(255,255,255,0)" />
          </linearGradient>
        </defs>
        <path
          d={CURSOR_PATH}
          fill={`url(#cv-paste-cursor-fill-${gradId})`}
          stroke="white"
          strokeWidth={2.25825}
          strokeLinejoin="round"
        />
        <path
          d="M27.5103 6.79925C26.7269 5.02557 24.2082 5.02558 23.3927 6.79925L7.59814 41.1495C7.0 42.3 7.6 43.3 8.6 43.3L25 23 Z"
          fill={`url(#cv-paste-cursor-highlight-${gradId})`}
          opacity={0.6}
        />
      </svg>
    </div>
  );
};
