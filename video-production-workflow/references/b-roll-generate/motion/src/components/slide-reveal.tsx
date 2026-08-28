// FROZEN library copy. Do not import from outside this directory and do not
//
// Slide reveal: a single sentence in one container that slides off-screen
// (left) with a slow-start / fast-end bezier. Each word lifts in from below
// as its natural sentence position passes canvas centre, briefly held in the
// accent color before fading to the resting text color.
//
// Library naming (matches typewriter):
//   primary  = accent color (shared via sharedPrimary across the library)
//   resting  = text color (the dark / final color)
//   background = canvas background

import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate, Easing } from 'remotion';

export type SlideRevealProps = {
  text: string;
  primary: string;              // accent (born color)
  lightMode: boolean;
  fontFamily: string;
  fontSize: number;
  fontWeight: number;
  letterSpacing: number;
  wordGap: number;
  totalFrames: number;
  exitX: number;
  exitY: number;
  bezierP1x: number;
  bezierP1y: number;
  bezierP2x: number;
  bezierP2y: number;
  wordEntranceFrames: number;
  wordEntranceBlur: number;
  wordEntranceY: number;
  wordEntranceP1x: number;
  wordEntranceP1y: number;
  wordEntranceP2x: number;
  wordEntranceP2y: number;
  accentEnabled: boolean;
  accentHoldFrames: number;
  accentFadeFrames: number;
  startDelayFrames: number;
  holdFrames: number;
  loop: boolean;
};

export const SlideRevealDefaults: SlideRevealProps = {
  text: 'Stop designing, start prompting',
  primary: '#F04E23',
  lightMode: true,
  fontFamily: 'Geist, Inter, system-ui, sans-serif',
  fontSize: 122,
  fontWeight: 600,
  letterSpacing: -1,
  wordGap: 40,
  totalFrames: 70,
  exitX: -2400,
  exitY: 0,
  bezierP1x: 0.3,
  bezierP1y: 0.2,
  bezierP2x: 0.85,
  bezierP2y: 0.2,
  wordEntranceFrames: 24,
  wordEntranceBlur: 14,
  wordEntranceY: 80,
  wordEntranceP1x: 0.32,
  wordEntranceP1y: 0.72,
  wordEntranceP2x: 0,
  wordEntranceP2y: 1,
  accentEnabled: true,
  accentHoldFrames: 7,
  accentFadeFrames: 22,
  startDelayFrames: 6,
  holdFrames: 30,
  loop: true,
};

const FPS = 30;

export const SlideRevealMeta = {
  width: 1920,
  height: 1080,
  fps: FPS,
};

export const computeSlideRevealDuration = (
  p: Pick<SlideRevealProps, 'startDelayFrames' | 'totalFrames' | 'holdFrames'>,
): number => p.startDelayFrames + p.totalFrames + p.holdFrames;

export const SlideReveal: React.FC<SlideRevealProps> = (props) => {
  const {
    text,
    primary,
    lightMode,
    fontFamily,
    fontSize,
    fontWeight,
    letterSpacing,
    wordGap,
    totalFrames,
    exitX,
    exitY,
    bezierP1x,
    bezierP1y,
    bezierP2x,
    bezierP2y,
    wordEntranceFrames,
    wordEntranceBlur,
    wordEntranceY,
    wordEntranceP1x,
    wordEntranceP1y,
    wordEntranceP2x,
    wordEntranceP2y,
    accentEnabled,
    accentHoldFrames,
    accentFadeFrames,
    startDelayFrames,
    loop,
  } = props;

  const background = lightMode ? '#FAFAF7' : '#000000';
  const resting = lightMode ? '#0B0B12' : '#FFFFFF';

  const cycleFrames = computeSlideRevealDuration(props);
  const rawFrame = useCurrentFrame();
  const frame = loop ? rawFrame % cycleFrames : rawFrame;
  const localFrame = frame - startDelayFrames;

  const easing = useMemo(
    () => Easing.bezier(clamp01(bezierP1x), bezierP1y, clamp01(bezierP2x), bezierP2y),
    [bezierP1x, bezierP1y, bezierP2x, bezierP2y],
  );
  const entranceEasing = useMemo(
    () => Easing.bezier(clamp01(wordEntranceP1x), wordEntranceP1y, clamp01(wordEntranceP2x), wordEntranceP2y),
    [wordEntranceP1x, wordEntranceP1y, wordEntranceP2x, wordEntranceP2y],
  );

  const words = useMemo(() => text.split(/\s+/).filter(Boolean), [text]);
  const wordWidths = useMemo(
    () => words.map((w) => measureTextWidth(w, fontFamily, fontSize, fontWeight, letterSpacing)),
    [words, fontFamily, fontSize, fontWeight, letterSpacing],
  );

  const wordCenters = useMemo(() => {
    const centers: number[] = [];
    let cursor = 0;
    for (let i = 0; i < wordWidths.length; i++) {
      if (i > 0) {
        const prev = wordWidths[i - 1] ?? 0;
        const cur = wordWidths[i] ?? 0;
        cursor += prev / 2 + wordGap + cur / 2;
      }
      centers.push(cursor);
    }
    return centers;
  }, [wordWidths, wordGap]);

  const { width: canvasWidth } = useVideoConfig();
  const lastIdx = wordWidths.length - 1;
  const lastWordRightInContainer = lastIdx >= 0
    ? (wordCenters[lastIdx] ?? 0) + (wordWidths[lastIdx] ?? 0) / 2
    : 0;
  const minExitX = -(canvasWidth / 2 + lastWordRightInContainer + 80);
  const effectiveExitX = Math.min(exitX, minExitX);

  const easedT = (f: number) => {
    if (f <= 0) return 0;
    if (f >= totalFrames) return 1;
    return easing(f / totalFrames);
  };
  const containerX = effectiveExitX * easedT(localFrame);
  const containerY = exitY * easedT(localFrame);

  const findCenterFrame = (targetT: number): number => {
    if (targetT <= 0) return 0;
    if (targetT >= 1) return totalFrames;
    let lo = 0;
    let hi = totalFrames;
    for (let i = 0; i < 28; i++) {
      const mid = (lo + hi) / 2;
      const tNorm = mid / totalFrames;
      if (easing(tNorm) < targetT) lo = mid;
      else hi = mid;
    }
    return (lo + hi) / 2;
  };
  const denom = Math.max(Math.abs(effectiveExitX), Math.abs(exitY)) || 1;
  const centerNorm = (c: number) => Math.abs(c) / denom;

  const wordAppearAt = useMemo(
    () => wordCenters.map((c) => {
      const target = centerNorm(c);
      if (target >= 1) return totalFrames;
      const centreFrame = findCenterFrame(target);
      return Math.max(0, Math.round(centreFrame - wordEntranceFrames / 2));
    }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [wordCenters, totalFrames, wordEntranceFrames, effectiveExitX, exitY, easing],
  );

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
        color: resting,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          position: 'relative',
          transform: `translate(${containerX}px, ${containerY}px)`,
          willChange: 'transform',
          whiteSpace: 'nowrap',
        }}
      >
        {words.map((w, i) => {
          const center = wordCenters[i] ?? 0;
          const width = wordWidths[i] ?? 0;
          const appearAt = wordAppearAt[i] ?? 0;
          const tOpacity = interpolate(
            localFrame,
            [appearAt, appearAt + wordEntranceFrames],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic) },
          );
          const blur = wordEntranceBlur * (1 - tOpacity);
          const wy = interpolate(
            localFrame,
            [appearAt, appearAt + wordEntranceFrames],
            [wordEntranceY, 0],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: entranceEasing },
          );

          let wordColor = resting;
          if (accentEnabled) {
            const ageColor = localFrame - appearAt - accentHoldFrames;
            const tColor = accentFadeFrames <= 0
              ? (ageColor >= 0 ? 1 : 0)
              : Math.min(1, Math.max(0, ageColor / accentFadeFrames));
            const eased = 1 - Math.pow(1 - tColor, 3);
            wordColor = mixHex(primary, resting, eased);
          }

          return (
            <span
              key={i}
              style={{
                position: 'absolute',
                left: center - width / 2,
                top: -fontSize / 2,
                transform: `translateY(${wy}px)`,
                opacity: tOpacity,
                filter: blur > 0.1 ? `blur(${blur}px)` : 'none',
                color: wordColor,
                willChange: 'opacity, filter, transform, color',
              }}
            >
              {w}
            </span>
          );
        })}
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
