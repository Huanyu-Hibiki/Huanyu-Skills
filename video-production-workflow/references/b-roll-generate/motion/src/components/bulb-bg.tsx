'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// This is the library's own copy of the bulb composition. Per-project
// sessions edit `the per-project copy of this file`
// and we never want that to ripple into the library.
//
// Anything imported here is local to the library: the palette helpers come
// from `../palettes` (also frozen). Do NOT import from `@curvable/shared` or
// from the project compositions directory.
//
// Any change here is an intentional library design change.
// ============================================================================

import React, { useMemo } from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import {
  bulbPalette,
  bulbPaletteLight,
  bulbLightLayerOpacities,
  bulbDarkLayerOpacities,
} from '../palettes';

type Pt = readonly [number, number];

const LAYER1_POINTS: Pt[] = [
  [-77.2, 299.385], [-77.0468, 288.498], [-76.5875, 277.638], [-75.8233, 266.83], [-74.7559, 256.101],
  [-73.388, 245.475], [-71.7228, 234.98], [-69.7644, 224.64], [-67.5175, 214.48], [-64.9874, 204.524],
  [-62.1804, 194.797], [-59.1031, 185.322], [-55.7629, 176.122], [-52.168, 167.219], [-48.3269, 158.634],
  [-44.249, 150.388], [-39.944, 142.501], [-35.4223, 134.992], [-30.6948, 127.879], [-25.773, 121.18],
  [-20.6685, 114.909], [-15.3939, 109.083], [-9.96166, 103.716], [-4.38501, 98.8196], [1.32267, 94.4066],
  [7.14761, 90.4874], [13.0758, 87.0715], [19.0929, 84.1671], [25.1845, 81.7811], [31.3359, 79.9194],
  [37.5322, 78.5864], [43.7586, 77.7853], [50, 77.518], [56.2414, 77.7853], [62.4678, 78.5864],
  [68.6641, 79.9194], [74.8155, 81.7811], [80.9071, 84.1671], [86.9242, 87.0715], [92.8524, 90.4874],
  [98.6773, 94.4066], [104.385, 98.8196], [109.962, 103.716], [115.394, 109.083], [120.669, 114.909],
  [125.773, 121.18], [130.695, 127.879], [135.422, 134.992], [139.944, 142.501], [144.249, 150.388],
  [148.327, 158.634], [152.168, 167.219], [155.763, 176.122], [159.103, 185.322], [162.18, 194.797],
  [164.987, 204.524], [167.517, 214.48], [169.764, 224.64], [171.723, 234.98], [173.388, 245.475],
  [174.756, 256.101], [175.823, 266.83], [176.587, 277.638], [177.047, 288.498], [177.2, 299.385],
];

const LAYER2_POINTS: Pt[] = [
  [-70, 299.385], [-69.8555, 288.917], [-69.4222, 278.474], [-68.7012, 268.082], [-67.6942, 257.765],
  [-66.4038, 247.549], [-64.8328, 237.457], [-62.9853, 227.515], [-60.8655, 217.746], [-58.4787, 208.173],
  [-55.8306, 198.82], [-52.9274, 189.709], [-49.7764, 180.863], [-46.3849, 172.302], [-42.7613, 164.047],
  [-38.9141, 156.119], [-34.8528, 148.535], [-30.5871, 141.315], [-26.1272, 134.476], [-21.4839, 128.034],
  [-16.6684, 122.004], [-11.6923, 116.403], [-6.56761, 111.241], [-1.30661, 106.534], [4.07799, 102.29],
  [9.57322, 98.5219], [15.1658, 95.2374], [20.8424, 92.4447], [26.5892, 90.1505], [32.3923, 88.3604],
  [38.2379, 87.0786], [44.1119, 86.3083], [50, 86.0513], [55.8881, 86.3083], [61.7621, 87.0786],
  [67.6077, 88.3604], [73.4108, 90.1505], [79.1576, 92.4447], [84.8342, 95.2374], [90.4268, 98.5219],
  [95.922, 102.29], [101.307, 106.534], [106.568, 111.241], [111.692, 116.403], [116.668, 122.004],
  [121.484, 128.034], [126.127, 134.476], [130.587, 141.315], [134.853, 148.535], [138.914, 156.119],
  [142.761, 164.047], [146.385, 172.302], [149.776, 180.863], [152.927, 189.709], [155.831, 198.82],
  [158.479, 208.173], [160.866, 217.746], [162.985, 227.515], [164.833, 237.457], [166.404, 247.549],
  [167.694, 257.765], [168.701, 268.082], [169.422, 278.474], [169.855, 288.917], [170, 299.385],
];

const LAYER3_POINTS: Pt[] = [
  [-60.4, 299.385], [-60.267, 289.44], [-59.8684, 279.52], [-59.2051, 269.647], [-58.2787, 259.846],
  [-57.0915, 250.141], [-55.6462, 240.554], [-53.9465, 231.108], [-51.9963, 221.828], [-49.8004, 212.734],
  [-47.3641, 203.848], [-44.6932, 195.193], [-41.7942, 186.789], [-38.6741, 178.656], [-35.3404, 170.814],
  [-31.801, 163.282], [-28.0646, 156.078], [-24.1401, 149.219], [-20.037, 142.721], [-15.7652, 136.601],
  [-11.335, 130.874], [-6.75694, 125.552], [-2.0422, 120.649], [2.79792, 116.176], [7.75175, 112.145],
  [12.8074, 108.565], [17.9526, 105.445], [23.175, 102.792], [28.462, 100.612], [33.801, 98.9116],
  [39.1789, 97.6939], [44.5829, 96.9621], [50, 96.718], [55.4171, 96.9621], [60.8211, 97.6939],
  [66.199, 98.9116], [71.538, 100.612], [76.825, 102.792], [82.0474, 105.445], [87.1926, 108.565],
  [92.2483, 112.145], [97.2021, 116.176], [102.042, 120.649], [106.757, 125.552], [111.335, 130.874],
  [115.765, 136.601], [120.037, 142.721], [124.14, 149.219], [128.065, 156.078], [131.801, 163.282],
  [135.34, 170.814], [138.674, 178.656], [141.794, 186.789], [144.693, 195.193], [147.364, 203.848],
  [149.8, 212.734], [151.996, 221.828], [153.946, 231.108], [155.646, 240.554], [157.091, 250.141],
  [158.279, 259.846], [159.205, 269.647], [159.868, 279.52], [160.267, 289.44], [160.4, 299.385],
];

const buildPolygon = (points: Pt[], yShift: number): string => {
  const parts = points.map(([x, y]) => `${x}% ${y - yShift}%`);
  return `polygon(${parts.join(', ')})`;
};

export type ExitDirection = 'down' | 'up';

export type BulbBgProps = {
  primary: string;
  peakRise: number;
  infiniteLoop: boolean;
  loops: number;
  exitDirection: ExitDirection;
  // false = dark canvas + dark-bg palette; true = light canvas + light-bg
  // palette (deepGlow fades to near-white, shadow tints darker).
  lightMode: boolean;
};

export const BulbBgDefaults: BulbBgProps = {
  primary: '#F04E23',
  peakRise: 24,
  infiniteLoop: false,
  loops: 2,
  exitDirection: 'down',
  lightMode: false,
};

const ENTER_FRAMES = 24;
const EXIT_FRAMES = 24;
// Trimmed from 110 to cut the dead space between iterations without
// speeding up the motion itself.
const LOOP_FRAMES = 90;
const RISE_FRAMES = Math.floor(LOOP_FRAMES * 0.59);
const FALL_FRAMES = LOOP_FRAMES - RISE_FRAMES;
const OFFSCREEN_SHIFT = 42;
const FPS = 30;
const ENGULF_PEAK_MULT = 1.8;
const ENGULF_SCALE = 2.6;
const ENGULF_HOLD_FRAMES = 60;

export const computeBulbDuration = (
  props: Pick<BulbBgProps, 'infiniteLoop' | 'loops' | 'exitDirection'>,
): number => {
  if (props.infiniteLoop) return LOOP_FRAMES;
  const base = ENTER_FRAMES + Math.max(1, props.loops) * LOOP_FRAMES;
  if (props.exitDirection === 'up') return base + FALL_FRAMES + ENGULF_HOLD_FRAMES;
  return base + EXIT_FRAMES;
};

export const BulbBgMeta = {
  width: 1920,
  height: 1080,
  fps: FPS,
  durationFrames: computeBulbDuration(BulbBgDefaults),
};

const easeInOutQuad = (t: number) =>
  t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

const loopProgress = (frameInLoop: number, loopFrames: number): number => {
  const riseEnd = Math.floor(loopFrames * 0.59);
  if (frameInLoop <= riseEnd) {
    const linear = interpolate(frameInLoop, [0, riseEnd], [0, 1], { extrapolateRight: 'clamp' });
    return easeInOutQuad(linear);
  }
  const linear = interpolate(frameInLoop, [riseEnd, loopFrames - 1], [0, 1], { extrapolateRight: 'clamp' });
  return 1 - easeInOutQuad(linear);
};

export const BulbBg: React.FC<BulbBgProps> = ({
  primary,
  peakRise,
  infiniteLoop,
  loops,
  exitDirection,
  lightMode,
}) => {
  const background = lightMode ? '#FAFAF7' : '#000000';
  const { hotCore, midGlow, deepGlow, shadowColor } = useMemo(
    () => (lightMode ? bulbPaletteLight(primary) : bulbPalette(primary)),
    [primary, lightMode],
  );
  const layerOpacities = lightMode ? bulbLightLayerOpacities : bulbDarkLayerOpacities;
  const frame = useCurrentFrame();

  let yShift: number;
  let opacity = 1;
  let scale = 1;
  if (infiniteLoop) {
    yShift = loopProgress(frame % LOOP_FRAMES, LOOP_FRAMES) * peakRise;
  } else {
    const loopCount = Math.max(1, loops);
    const mergedRiseFrames = ENTER_FRAMES + RISE_FRAMES;
    const mergedFallFrames = FALL_FRAMES + EXIT_FRAMES;
    const totalAmplitude = peakRise + OFFSCREEN_SHIFT;
    const mergedRiseEnd = mergedRiseFrames;
    const firstFallEnd = ENTER_FRAMES + LOOP_FRAMES;
    const lastRiseStart = ENTER_FRAMES + (loopCount - 1) * LOOP_FRAMES;
    const lastRiseEnd = lastRiseStart + RISE_FRAMES;
    const engulfGrowEnd = lastRiseEnd + FALL_FRAMES;
    const exitFallStart = loopCount === 1 ? mergedRiseEnd : lastRiseEnd;

    const FADE_OUT_EARLY = 0.3;
    const fadeOut = (linear: number) =>
      1 - easeInOutQuad(interpolate(linear, [0, 1 - FADE_OUT_EARLY], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));

    const exitIsUp = exitDirection === 'up';
    const tripleMerge = exitIsUp && loopCount === 1;
    const engulfActive = exitIsUp && (tripleMerge || frame >= lastRiseStart);

    if (engulfActive) {
      const mergeStart = tripleMerge ? 0 : lastRiseStart;
      const endYShift = peakRise * ENGULF_PEAK_MULT;
      if (frame < engulfGrowEnd) {
        const t = interpolate(frame, [mergeStart, engulfGrowEnd], [0, 1], { extrapolateRight: 'clamp' });
        yShift = easeInOutQuad(t) * endYShift;
        if (frame >= lastRiseEnd) {
          const sT = interpolate(frame, [lastRiseEnd, engulfGrowEnd], [0, 1], { extrapolateRight: 'clamp' });
          scale = 1 + easeInOutQuad(sT) * (ENGULF_SCALE - 1);
        }
      } else {
        yShift = endYShift;
        scale = ENGULF_SCALE;
        const holdEnd = engulfGrowEnd + ENGULF_HOLD_FRAMES;
        const fadeStart = engulfGrowEnd + ENGULF_HOLD_FRAMES * 0.5;
        if (frame > fadeStart) {
          const t = interpolate(frame, [fadeStart, holdEnd], [0, 1], { extrapolateRight: 'clamp' });
          opacity = 1 - easeInOutQuad(t);
        }
      }
    } else if (frame < mergedRiseEnd) {
      // Enter: rise from off-screen (-OFFSCREEN_SHIFT) up to peak. Was
      // accidentally starting at rest (0) so the bulb just appeared.
      const linear = interpolate(frame, [0, mergedRiseEnd], [0, 1], { extrapolateRight: 'clamp' });
      yShift = -OFFSCREEN_SHIFT + easeInOutQuad(linear) * totalAmplitude;
    } else if (loopCount === 1 && !exitIsUp) {
      const linear = interpolate(frame, [mergedRiseEnd, mergedRiseEnd + mergedFallFrames], [0, 1], { extrapolateRight: 'clamp' });
      yShift = peakRise - easeInOutQuad(linear) * totalAmplitude;
      opacity = fadeOut(linear);
    } else if (frame < firstFallEnd) {
      const linear = interpolate(frame, [mergedRiseEnd, firstFallEnd], [0, 1], { extrapolateRight: 'clamp' });
      yShift = peakRise * (1 - easeInOutQuad(linear));
    } else if (frame < lastRiseEnd) {
      const frameInLoops = frame - firstFallEnd;
      yShift = loopProgress(frameInLoops % LOOP_FRAMES, LOOP_FRAMES) * peakRise;
    } else {
      const linear = interpolate(frame, [exitFallStart, exitFallStart + mergedFallFrames], [0, 1], { extrapolateRight: 'clamp' });
      yShift = peakRise - easeInOutQuad(linear) * totalAmplitude;
      opacity = fadeOut(linear);
    }
  }

  const poly1 = useMemo(() => buildPolygon(LAYER1_POINTS, yShift), [yShift]);
  const poly2 = useMemo(() => buildPolygon(LAYER2_POINTS, yShift), [yShift]);
  const poly3 = useMemo(() => buildPolygon(LAYER3_POINTS, yShift), [yShift]);

  return (
    <AbsoluteFill style={{ backgroundColor: background, overflow: 'hidden' }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          filter: `blur(120px) drop-shadow(color-mix(in srgb, ${shadowColor} 58%, transparent) 0px 26.4px 51.84px) drop-shadow(color-mix(in srgb, ${shadowColor} 58%, transparent) 0px 40.9px 99.36px)`,
          transform: `translateZ(0) scale(${scale})`,
          transformOrigin: 'center bottom',
          opacity,
        }}
      >
        <div style={{ position: 'absolute', inset: 0, opacity: layerOpacities.deepGlow }}>
          <div style={{ width: '100%', height: '100%', background: deepGlow, clipPath: poly1 }} />
        </div>
        <div style={{ position: 'absolute', inset: 0, opacity: layerOpacities.midGlow }}>
          <div style={{ width: '100%', height: '100%', background: midGlow, clipPath: poly2 }} />
        </div>
        <div style={{ position: 'absolute', inset: 0, opacity: layerOpacities.hotCore }}>
          <div style={{ width: '100%', height: '100%', background: hotCore, clipPath: poly3 }} />
        </div>
      </div>
    </AbsoluteFill>
  );
};
