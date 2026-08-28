// FROZEN library copy. Do not import from outside this directory and do not
//
// Typewriter where each character is born in `primary` (caret + accent
// colour) and fades to `resting` over `fadeFrames`. The caret is a vertical
// pill that sits flush against the trailing edge of the latest glyph at a
// fixed `caretGap`, so the visual distance between the caret and the most-
// recent letter stays constant throughout typing.

import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';

// Horizontal padding kept clear of glyph + caret so long strings shrink to
// fit the canvas instead of running off the edge. Expressed as a fraction of
// the composition width so it scales with the canvas.
const PADDING_X_FRACTION = 0.08;

export type CaretShape = 'bar' | 'block';
export type FadeMode = 'smooth' | 'hard';

export type TypewriterProps = {
  text: string;
  primary: string;
  lightMode: boolean;
  fontFamily: string;
  fontSize: number;
  fontWeight: number;
  letterSpacing: number;
  framesPerChar: number;
  fadeFrames: number;
  fadeMode: FadeMode;
  caretShape: CaretShape;
  caretWidth: number;
  caretBlockWidth: number;
  caretHeightRatio: number;
  caretBlockHeightRatio: number;
  caretBlockOpacity: number;
  caretGap: number;
  caretBlinkHz: number;
  startDelayFrames: number;
  holdFrames: number;
  loop: boolean;
};

export const TypewriterDefaults: TypewriterProps = {
  text: 'Curvable',
  primary: '#F04E23',
  lightMode: true,
  fontFamily: 'Geist, Inter, system-ui, sans-serif',
  fontSize: 220,
  fontWeight: 600,
  letterSpacing: -2,
  framesPerChar: 3,
  fadeFrames: 5,
  fadeMode: 'smooth',
  caretShape: 'bar',
  caretWidth: 10,
  caretBlockWidth: 110,
  caretHeightRatio: 1.05,
  caretBlockHeightRatio: 0.7,
  caretBlockOpacity: 1,
  caretGap: 8,
  caretBlinkHz: 2,
  startDelayFrames: 0,
  holdFrames: 76,
  loop: true,
};

const FPS = 30;

export const TypewriterMeta = {
  width: 1920,
  height: 1080,
  fps: FPS,
};

export const computeTypewriterDuration = (
  p: Pick<TypewriterProps, 'text' | 'framesPerChar' | 'fadeFrames' | 'startDelayFrames' | 'holdFrames'>,
): number => {
  const typingFrames = p.text.length * p.framesPerChar;
  return p.startDelayFrames + typingFrames + p.fadeFrames + p.holdFrames;
};

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

export const Typewriter: React.FC<TypewriterProps> = (props) => {
  const {
    text,
    primary,
    lightMode,
    fontFamily,
    fontSize,
    fontWeight,
    letterSpacing,
    framesPerChar,
    fadeFrames,
    fadeMode,
    caretShape,
    caretWidth,
    caretBlockWidth,
    caretHeightRatio,
    caretBlockHeightRatio,
    caretBlockOpacity,
    caretGap,
    caretBlinkHz,
    startDelayFrames,
    holdFrames,
    loop,
  } = props;

  const background = lightMode ? '#FAFAF7' : '#000000';
  const resting = lightMode ? '#0B0B12' : '#FFFFFF';

  const cycleFrames = useMemo(
    () => computeTypewriterDuration(props),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [text, framesPerChar, fadeFrames, startDelayFrames, holdFrames],
  );

  const rawFrame = useCurrentFrame();
  const frame = loop ? rawFrame % cycleFrames : rawFrame;

  const typingStart = startDelayFrames;
  const visibleCount = Math.max(
    0,
    Math.min(text.length, Math.floor((frame - typingStart) / framesPerChar) + 1),
  );

  const caretIdle = frame >= typingStart + text.length * framesPerChar;
  const caretOpacity = useMemo(() => {
    if (caretBlinkHz <= 0) return 1;
    if (!caretIdle) return 1;
    const t = (frame / FPS) * caretBlinkHz;
    return Math.floor(t * 2) % 2 === 0 ? 1 : 0;
  }, [frame, caretBlinkHz, caretIdle]);

  const glyphs: { ch: string; color: string }[] = [];
  for (let i = 0; i < visibleCount; i++) {
    let color: string;
    if (fadeMode === 'hard') {
      // Hard switch: latest glyph stays primary for a single char-tick, then
      // snaps to resting (so the last letter doesn't stay orange forever).
      const bornAt = typingStart + i * framesPerChar;
      const age = frame - bornAt;
      color = i === visibleCount - 1 && age < framesPerChar ? primary : resting;
    } else {
      const bornAt = typingStart + i * framesPerChar;
      const age = frame - bornAt;
      const t = fadeFrames <= 0 ? 1 : Math.min(1, Math.max(0, age / fadeFrames));
      const eased = easeOutCubic(t);
      color = mixHex(primary, resting, eased);
    }
    glyphs.push({ ch: text[i]!, color });
  }

  // Pre-compute scale based on the FULL string width so the layout doesn't
  // jitter as glyphs appear. Measured via canvas in the browser; falls back
  // to a coarse estimate during SSR/non-DOM render hosts.
  const { width: canvasWidth } = useVideoConfig();
  const scale = useMemo(() => {
    const naturalWidth = measureTextWidth(text, fontFamily, fontSize, fontWeight, letterSpacing);
    const totalWidth = naturalWidth + caretGap + caretWidth;
    const budget = canvasWidth * (1 - 2 * PADDING_X_FRACTION);
    return Math.min(1, budget / Math.max(1, totalWidth));
  }, [text, fontFamily, fontSize, fontWeight, letterSpacing, caretGap, caretWidth, canvasWidth]);

  return (
    <AbsoluteFill
      style={{
        background,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily,
        fontWeight,
        fontSize,
        letterSpacing,
        lineHeight: 1,
      }}
    >
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          transform: `scale(${scale})`,
          transformOrigin: 'center',
          willChange: 'transform',
        }}
      >
        <span style={{ display: 'inline-flex', alignItems: 'baseline' }}>
          {glyphs.map((g, i) => (
            <span key={i} style={{ color: g.color, whiteSpace: 'pre' }}>
              {g.ch}
            </span>
          ))}
        </span>
        <span
          style={{
            display: 'inline-block',
            marginLeft: caretGap,
            width: caretShape === 'block' ? caretBlockWidth : caretWidth,
            height: fontSize * (caretShape === 'block' ? caretBlockHeightRatio : caretHeightRatio),
            background: primary,
            opacity: caretOpacity * (caretShape === 'block' ? caretBlockOpacity : 1),
            borderRadius: caretShape === 'block' ? 4 : caretWidth / 2,
            transform: 'translateY(2%)',
          }}
        />
      </div>
    </AbsoluteFill>
  );
};

// ---- text measurement ----------------------------------------------------

let _measureCanvas: HTMLCanvasElement | null = null;
function measureTextWidth(
  text: string,
  fontFamily: string,
  fontSize: number,
  fontWeight: number,
  letterSpacing: number,
): number {
  if (typeof document === 'undefined') {
    // Coarse server-side fallback. ~0.55em per glyph is a fair average for
    // sans-serif at 600 weight; only matters for first-render layout.
    return text.length * fontSize * 0.55 + letterSpacing * Math.max(0, text.length - 1);
  }
  if (!_measureCanvas) _measureCanvas = document.createElement('canvas');
  const ctx = _measureCanvas.getContext('2d');
  if (!ctx) return text.length * fontSize * 0.55;
  ctx.font = `${fontWeight} ${fontSize}px ${fontFamily}`;
  return ctx.measureText(text).width + letterSpacing * Math.max(0, text.length - 1);
}

// ---- color helpers -------------------------------------------------------

function clamp01(n: number) {
  return Math.max(0, Math.min(1, n));
}
function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  const v =
    h.length === 3
      ? h.split('').map((c) => parseInt(c + c, 16))
      : [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  return [v[0] ?? 0, v[1] ?? 0, v[2] ?? 0];
}
function rgbToHex(r: number, g: number, b: number): string {
  const toHex = (n: number) => Math.round(clamp01(n / 255) * 255).toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}
function mixHex(a: string, b: string, t: number): string {
  const [ar, ag, ab] = hexToRgb(a);
  const [br, bg, bb] = hexToRgb(b);
  const k = clamp01(t);
  return rgbToHex(ar + (br - ar) * k, ag + (bg - ag) * k, ab + (bb - ab) * k);
}
