'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library's own copy of the typed-reveal beat. The first word zooms in from
// huge (scale 8) + blurred + low, slides right to its resting X, and the
// remaining words slide in word-by-word with per-letter (or per-word)
// orange → resting-text fade and em-blur de-blur.
//
// Tuned in /sandbox/curvable-types. All timing + motion baked here.
//
// Imports: react, remotion. NO @curvable/shared, NO per-project paths.
// ============================================================================

import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from 'remotion';

const STAGE_W = 1920;
const STAGE_H = 1080;
const FPS = 30;

const WORD_EASE = Easing.bezier(0.22, 1, 0.36, 1);

// Light/dark  -  only bg + resting text colour swap.
const DARK_BG = '#0a0a0a';
const DARK_TEXT = '#ffffff';
const LIGHT_BG = '#f6f4ef';
const LIGHT_TEXT = '#101010';

// Baked motion (sandbox-saved defaults).
const LEAD_IN_FRAMES = 5;
const WORD_STAGGER_FRAMES = 4;
const WORD_ENTER_FRAMES = 22;
const WORD_SLIDE_EM = 0.8;
const WORD_BLUR = 0.2;
const CHAR_STAGGER_FRAMES = 2;
const CURVABLE_START_SCALE = 8;
const CURVABLE_START_Y_OFFSET = 0;
const CURVABLE_START_BLUR = 10;
const CURVABLE_ZOOM_FRAMES = 20;
const CURVABLE_SLIDE_EARLY_FRAMES = 10;
// Exit: hold at rest for ~25 frames after the last word lands, then ramp
// out. Total runtime is short enough that the loop feels punchy.
const EXIT_START_OFFSET = 40;
const EXIT_FRAMES = 80;
const EXIT_SCALE = 20;
const EXIT_Y_OFFSET = 0;
const EXIT_X_OFFSET = 0;
const EXIT_BLUR = 8;

const FONT_SIZE = 115;
const FONT_WEIGHT = 700;

export type CurvableTypesProps = {
  primary: string;          // entry tint colour for every non-first word (when tintEntry on)
  text: string;
  perWordReveal: boolean;   // false = per-letter cascade; true = whole word at once
  tintEntry: boolean;       // false = words appear in resting text colour;
                            // true = words start in `primary` and fade to text colour
  lightMode: boolean;
};

export const CurvableTypesDefaults: CurvableTypesProps = {
  primary: '#F04E23',
  text: 'Curvable does the rest',
  perWordReveal: true,
  tintEntry: false,
  lightMode: false,
};

export const CurvableTypesMeta = {
  width: STAGE_W,
  height: STAGE_H,
  fps: FPS,
};

export const computeCurvableTypesDuration = (): number =>
  LEAD_IN_FRAMES + EXIT_START_OFFSET + EXIT_FRAMES;

function mixHexColors(from: string, to: string, t: number): string {
  const parse = (h: string) => {
    const s = h.replace('#', '');
    const n = s.length === 3 ? s.split('').map((c) => c + c).join('') : s;
    return [parseInt(n.slice(0, 2), 16), parseInt(n.slice(2, 4), 16), parseInt(n.slice(4, 6), 16)] as const;
  };
  const [r1, g1, b1] = parse(from);
  const [r2, g2, b2] = parse(to);
  const u = Math.max(0, Math.min(1, t));
  const mix = (a: number, b: number) => Math.round(a + (b - a) * u);
  return `rgb(${mix(r1, r2)}, ${mix(g1, g2)}, ${mix(b1, b2)})`;
}

export const CurvableTypes: React.FC<CurvableTypesProps> = ({ primary, text, perWordReveal, tintEntry, lightMode }) => {
  const frame = useCurrentFrame();
  const bg = lightMode ? LIGHT_BG : DARK_BG;
  const textColor = lightMode ? LIGHT_TEXT : DARK_TEXT;
  const firstWordStart = LEAD_IN_FRAMES;
  const exitStartFrame = firstWordStart + EXIT_START_OFFSET;

  const exitT = interpolate(frame, [exitStartFrame, exitStartFrame + EXIT_FRAMES], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_EASE,
  });
  const eScale = 1 + (EXIT_SCALE - 1) * exitT;
  const eY = EXIT_Y_OFFSET * exitT;
  const eX = EXIT_X_OFFSET * exitT;
  const eBlur = EXIT_BLUR * exitT;

  const tokens = text.split(/(\s+)/);
  let wordIdx = 0;

  return (
    <AbsoluteFill style={{ background: bg, overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: textColor,
        }}
      >
        <div style={{ fontSize: FONT_SIZE, fontWeight: FONT_WEIGHT }}>
          <span
            style={{
              position: 'relative',
              display: 'inline-flex',
              justifyContent: 'center',
              alignItems: 'baseline',
              whiteSpace: 'pre',
              opacity: 1 - exitT,
              transform: `translate(${eX}px, ${eY}px) scale(${eScale})`,
              filter: eBlur > 0.01 ? `blur(${eBlur}px)` : undefined,
              transformOrigin: 'center center',
              willChange: 'transform, filter, opacity',
            }}
          >
            {tokens.map((tok, ti) => {
              if (tok === '' || /^\s+$/.test(tok)) {
                return (
                  <span key={`w-${ti}`} style={{ display: 'inline-block', whiteSpace: 'pre' }}>
                    {tok}
                  </span>
                );
              }
              const i = wordIdx++;
              if (i === 0) {
                const zoomT = interpolate(
                  frame,
                  [firstWordStart, firstWordStart + CURVABLE_ZOOM_FRAMES],
                  [0, 1],
                  { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_EASE },
                );
                const slideStart = firstWordStart + CURVABLE_ZOOM_FRAMES - CURVABLE_SLIDE_EARLY_FRAMES;
                const slideT = interpolate(
                  frame,
                  [slideStart, slideStart + WORD_ENTER_FRAMES],
                  [0, 1],
                  { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_EASE },
                );
                const scale = CURVABLE_START_SCALE + (1 - CURVABLE_START_SCALE) * zoomT;
                const yOffset = CURVABLE_START_Y_OFFSET * (1 - zoomT);
                const blurPx = CURVABLE_START_BLUR * (1 - zoomT);
                const tx = -WORD_SLIDE_EM * (1 - slideT);
                return (
                  <span
                    key={`w-${ti}`}
                    style={{
                      display: 'inline-block',
                      opacity: zoomT,
                      transform: `translateX(${tx}em) translateY(${yOffset}px) scale(${scale})`,
                      filter: blurPx > 0.01 ? `blur(${blurPx}px)` : undefined,
                      whiteSpace: 'pre',
                      willChange: 'transform, opacity, filter',
                    }}
                  >
                    {tok}
                  </span>
                );
              }
              const start = firstWordStart + CURVABLE_ZOOM_FRAMES - CURVABLE_SLIDE_EARLY_FRAMES + (i - 1) * WORD_STAGGER_FRAMES;
              const wordT = interpolate(frame, [start, start + WORD_ENTER_FRAMES], [0, 1], {
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_EASE,
              });
              const tx = -WORD_SLIDE_EM * (1 - wordT);
              return (
                <span
                  key={`w-${ti}`}
                  style={{
                    display: 'inline-block',
                    transform: `translateX(${tx}em)`,
                    whiteSpace: 'pre',
                    willChange: 'transform',
                  }}
                >
                  {tok.split('').map((ch, ci) => {
                    const charStart = start + (perWordReveal ? 0 : ci * CHAR_STAGGER_FRAMES);
                    const charT = interpolate(
                      frame,
                      [charStart, charStart + WORD_ENTER_FRAMES],
                      [0, 1],
                      { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: WORD_EASE },
                    );
                    const blur = WORD_BLUR * (1 - charT);
                    const color = tintEntry ? mixHexColors(primary, textColor, charT) : textColor;
                    return (
                      <span
                        key={`ch-${ci}`}
                        style={{
                          display: 'inline-block',
                          opacity: charT,
                          color,
                          filter: blur > 0.001 ? `blur(${blur}em)` : undefined,
                          whiteSpace: 'pre',
                          willChange: 'opacity, filter, color',
                        }}
                      >
                        {ch}
                      </span>
                    );
                  })}
                </span>
              );
            })}
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
