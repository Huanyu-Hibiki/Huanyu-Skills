'use client';

import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { glowStore, loadPresets, runtimeKnobs, type GlowPreset } from './glowStore';

// Renders the Apple-Intelligence-style inside glow by compiling the
// react-native-animated-glow SkSL shader against CanvasKit directly. No
// react-native-web, no Reanimated, no Skia wrapper. The shader source is
// ported verbatim from reactnativeglow.com's bundle (see
// apps/web/.notes/skia-glow-investigation.md); the JS side packs uniforms
// and drives the phase increment from a plain rAF loop.

const MAX_LAYERS = 10;
const COLOR_STOPS = 8;
const PERIMETER_SPEED = 0.166; // matches upstream: full walk ≈ 6s at speed 1

// Runtime-tweakable knobs (breathePeriod / breatheAmount / bleedCss) live in
// glowStore.runtimeKnobs so the __cvGlow debug API can mutate them at runtime.
// The breathing pulse is Curvable-specific (upstream library doesn't breathe);
// the bleed shifts the bright SDF peak just past the visible canvas so its
// inward Gaussian fade is all you ever see  -  no hard "pin line" at the edge.

// ---------- SkSL shader (transcribed from the upstream bundle) ----------

const SHADER_SRC = `
uniform float2 u_resolution;
uniform float2 u_rectSize;
uniform float u_cornerRadius;
uniform float4 u_backgroundColor;
uniform float u_borderWidth;
uniform float u_borderProgress;
uniform float u_layerCount;
uniform float u_coverage[${MAX_LAYERS}];
uniform float4 u_glowSizes[${MAX_LAYERS}];
uniform float u_opacity[${MAX_LAYERS}];
uniform float u_relativeOffset[${MAX_LAYERS}];
uniform float u_layerProgress[${MAX_LAYERS}];
uniform float4 u_colors_0[${COLOR_STOPS}];
${Array.from({ length: MAX_LAYERS }, (_, i) => `uniform float4 u_colors_${i + 1}[${COLOR_STOPS}];`).join('\n')}
uniform float u_masterOpacity;
uniform float u_placements[${MAX_LAYERS}];
uniform float u_isBorderAnimated;
uniform float u_coverageFeather;
uniform float u_perimBlend;

const float PI = 3.14159265359;

float smoothT(float t) { return t * t * (3.0 - 2.0 * t); }

float sdfRoundedBox(float2 p, float2 b, float r) {
  float2 q = abs(p) - b + r;
  return min(max(q.x, q.y), 0.0) + length(max(q, float2(0.0))) - r;
}

float calcPerimeter(float2 p, float2 b, float r) {
  float w = b.x - r;
  float h = b.y - r;
  float c = PI * r / 2.0;
  float H = 2.0 * w;
  float V = 2.0 * h;
  float s0 = c;
  float s1 = s0 + H;
  float s2 = s1 + c;
  float s3 = s2 + V;
  float s4 = s3 + c;
  float s5 = s4 + H;
  float s6 = s5 + c;
  float perimeter = s6 + V;
  if (perimeter == 0.0) return 0.0;
  float dist = 0.0;
  if (p.x < -w) {
    if (p.y < -h) {
      float2 cp = p - float2(-w, -h);
      dist = c * ((atan(cp.y, cp.x) + PI) / (PI / 2.0));
    } else if (p.y > h) {
      float2 cp = p - float2(-w, h);
      dist = s5 + c * ((atan(cp.y, cp.x) - PI / 2.0) / (PI / 2.0));
    } else {
      dist = s6 + (h - p.y);
    }
  } else if (p.x > w) {
    if (p.y < -h) {
      float2 cp = p - float2(w, -h);
      dist = s1 + c * ((atan(cp.y, cp.x) + PI / 2.0) / (PI / 2.0));
    } else if (p.y > h) {
      float2 cp = p - float2(w, h);
      dist = s3 + c * (atan(cp.y, cp.x) / (PI / 2.0));
    } else {
      dist = s2 + (h + p.y);
    }
  } else {
    // -w <= p.x <= w. The upstream shader assigns top-edge perim if p.y < 0
    // and bottom-edge perim otherwise, which is wrong for deep interior
    // pixels close to the left or right edge  -  it creates a hard color seam
    // at p.x = +/-w because the left/right "branch" returns the side-edge
    // perim while this branch returns the top/bottom perim, and those colors
    // don't match. Fix: pick whichever of the 4 edges is actually closest.
    if (p.y < -h) {
      dist = s0 + (w + p.x);
    } else if (p.y > h) {
      dist = s4 + (w - p.x);
    } else {
      float dtop = b.y + p.y;
      float dright = b.x - p.x;
      float dbot = b.y - p.y;
      float dleft = b.x + p.x;
      if (dtop <= dright && dtop <= dbot && dtop <= dleft) {
        dist = s0 + (w + p.x);
      } else if (dright <= dbot && dright <= dleft) {
        dist = s2 + (h + p.y);
      } else if (dbot <= dleft) {
        dist = s4 + (w - p.x);
      } else {
        dist = s6 + (h - p.y);
      }
    }
  }
  return dist / perimeter;
}

float4 gradient(float progress, float4 colors[${COLOR_STOPS}]) {
  float t = progress * float(${COLOR_STOPS - 1});
  float4 result = colors[${COLOR_STOPS - 1}];
  for (int i = ${COLOR_STOPS - 2}; i >= 0; i--) {
    if (t < float(i + 1)) {
      result = mix(colors[i], colors[i + 1], t - float(i));
    }
  }
  return result;
}

float interpSize(float progress, float4 sizes) {
  float seg = 1.0 / 3.0;
  if (progress < seg) return mix(sizes.x, sizes.y, smoothT(progress / seg));
  if (progress < 2.0 * seg) return mix(sizes.y, sizes.z, smoothT((progress - seg) / seg));
  return mix(sizes.z, sizes.w, smoothT((progress - 2.0 * seg) / seg));
}

float gaussianFalloff(float x, float sigma) {
  if (sigma <= 0.0) return 0.0;
  return exp(-(x * x) / (2.0 * sigma * sigma));
}

float4 layerColor(int idx, float t) {
${Array.from({ length: MAX_LAYERS }, (_, i) =>
  `  if (idx == ${i}) return gradient(t, u_colors_${i + 1});`,
).join('\n')}
  return float4(0.0);
}

// Compute one layer's contribution at a given perimeter coordinate. Splits
// out so we can call it 4x per pixel (one per edge candidate) and blend the
// results, which is what eliminates the medial-axis color seam.
// SkSL note: uniform arrays can't be indexed with a non-constant expression
// inside a function (the index has to be a literal or compile-time constant),
// so we pass the per-layer uniform values in as scalars instead of letting
// this function index them itself.
float4 layerContribAt(int idx, float perimNorm, float d,
                      float layerProgress, float relativeOffset,
                      float coverage, float opacity,
                      float4 glowSizes, float placement) {
  float animated = fract(perimNorm - layerProgress + relativeOffset);
  if (coverage == 0.0) return float4(0.0);
  float bandMask = 1.0;
  if (coverage < 1.0) {
    float feather = min(u_coverageFeather, coverage * 0.5);
    float fadeIn  = smoothstep(0.0, feather, animated);
    float fadeOut = 1.0 - smoothstep(coverage - feather, coverage, animated);
    bandMask = fadeIn * fadeOut;
    if (bandMask <= 0.0) return float4(0.0);
  } else if (animated > coverage) {
    return float4(0.0);
  }
  float segP = animated / coverage;
  float thickness = interpSize(segP, glowSizes);
  float falloff = gaussianFalloff(abs(d), thickness) * bandMask;
  if (d > 0.0 && placement == 1.0) falloff = 0.0;
  if (falloff <= 0.0) return float4(0.0);
  float4 c = layerColor(idx, segP);
  return c * falloff * opacity;
}

half4 main(float2 fragCoord) {
  float2 center = u_resolution * 0.5;
  float2 p = fragCoord - center;
  float2 b = u_rectSize * 0.5;
  float r = u_cornerRadius;
  float d = sdfRoundedBox(p, b, r);

  // Compute perimeter segment landmarks once. We use these to map an
  // edge-projection back to its perimeter parameter.
  float w_ = b.x - r;
  float h_ = b.y - r;
  float c_arc = PI * r / 2.0;
  float s0 = c_arc;
  float s1 = s0 + 2.0 * w_;
  float s2 = s1 + c_arc;
  float s3 = s2 + 2.0 * h_;
  float s4 = s3 + c_arc;
  float s5 = s4 + 2.0 * w_;
  float s6 = s5 + c_arc;
  float perimTotal = s6 + 2.0 * h_;

  // Project this pixel onto each of the 4 straight edges and compute the
  // perimeter parameter at that projection. Used in a weighted blend below.
  float cx = clamp(p.x, -w_, w_);
  float cy = clamp(p.y, -h_, h_);
  float perimT = (s0 + (cx + w_)) / perimTotal;
  float perimR = (s2 + (cy + h_)) / perimTotal;
  float perimB = (s4 + (w_ - cx)) / perimTotal;
  float perimL = (s6 + (h_ - cy)) / perimTotal;

  // Soft weights based on distance to each edge. Closer edges dominate; at
  // the medial axis (two edges equidistant) weights are equal and the two
  // colors blend, killing the diagonal seam that "pick one closest edge"
  // produces.
  float dt = b.y + p.y;
  float dr = b.x - p.x;
  float db = b.y - p.y;
  float dl = b.x + p.x;
  float dMin = min(min(dt, dr), min(db, dl));
  float softness = max(0.5, u_perimBlend);
  float wT = exp((dMin - dt) / softness);
  float wR = exp((dMin - dr) / softness);
  float wB = exp((dMin - db) / softness);
  float wL = exp((dMin - dl) / softness);
  float wSum = wT + wR + wB + wL;
  wT /= wSum;
  wR /= wSum;
  wB /= wSum;
  wL /= wSum;

  float4 behindGlow = float4(0.0);
  float4 frontGlow  = float4(0.0);

  int layerCount = int(u_layerCount);
  for (int i = 0; i < ${MAX_LAYERS}; i++) {
    if (i >= layerCount) break;
    // Pull this layer's uniforms into scalar locals so the helper doesn't
    // have to dynamically index into u_* arrays (SkSL forbids that).
    float lp = u_layerProgress[i];
    float ro = u_relativeOffset[i];
    float cv = u_coverage[i];
    float op = u_opacity[i];
    float4 gs = u_glowSizes[i];
    float pl = u_placements[i];
    float4 cT = layerContribAt(i, perimT, d, lp, ro, cv, op, gs, pl);
    float4 cR = layerContribAt(i, perimR, d, lp, ro, cv, op, gs, pl);
    float4 cB = layerContribAt(i, perimB, d, lp, ro, cv, op, gs, pl);
    float4 cL = layerContribAt(i, perimL, d, lp, ro, cv, op, gs, pl);
    float4 contrib = wT * cT + wR * cR + wB * cB + wL * cL;
    if (pl == 0.0) behindGlow += contrib;
    else            frontGlow  += contrib;
  }

  float4 finalColor = behindGlow;
  if (d <= 0.0) {
    finalColor = mix(finalColor, u_backgroundColor, u_backgroundColor.a);
  }
  finalColor += frontGlow;

  // Animated border (drawn directly on the rect edge) is part of the
  // upstream feature set but Curvable never enables it  -  u_isBorderAnimated
  // is hardcoded to 0 in writeStaticPresetUniforms. Block dropped to avoid
  // referencing the now-unused calcPerimeter() helper.

  return half4(finalColor * u_masterOpacity);
}
`;

// ---------- color parsing ----------

function parseColor(input: string): [number, number, number, number] {
  const s = input.trim();
  const m = s.match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)$/i);
  if (m) {
    return [+m[1]! / 255, +m[2]! / 255, +m[3]! / 255, m[4] !== undefined ? +m[4]! : 1];
  }
  if (s.startsWith('#')) {
    const h = s.slice(1);
    const norm = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
    const r = parseInt(norm.slice(0, 2), 16) / 255;
    const g = parseInt(norm.slice(2, 4), 16) / 255;
    const b = parseInt(norm.slice(4, 6), 16) / 255;
    const a = norm.length === 8 ? parseInt(norm.slice(6, 8), 16) / 255 : 1;
    return [r, g, b, a];
  }
  return [0, 0, 0, 0];
}

// HSL <-> RGB helpers. We use HSL interpolation (not straight RGB lerp) when
// resampling user colors so the midpoint between two saturated, opposing-hue
// colors doesn't darken visibly. RGB linear interpolation of e.g. blue and
// magenta lands on a ~30%-darker purple at t=0.5; HSL keeps the lightness
// constant and just rotates the hue, eliminating that valley. The shader's
// own mix() between adjacent stops is still RGB-linear, but at COLOR_STOPS=8
// each interval covers ~25° of hue, small enough that the residual dip is
// imperceptible.

type RGB = [number, number, number];
type RGBA = [number, number, number, number];
type HSL = [number, number, number];

function rgbToHsl(r: number, g: number, b: number): HSL {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h: number;
  if (max === r) h = (g - b) / d + (g < b ? 6 : 0);
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;
  return [h / 6, s, l];
}

function hslToRgb(h: number, s: number, l: number): RGB {
  if (s === 0) return [l, l, l];
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const hue2rgb = (t: number): number => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  return [hue2rgb(h + 1 / 3), hue2rgb(h), hue2rgb(h - 1 / 3)];
}

function lerpHsl(a: HSL, b: HSL, t: number): HSL {
  // Hue wraps in [0,1); take the shorter arc so the rotation is direct.
  let dh = b[0] - a[0];
  if (dh > 0.5) dh -= 1;
  else if (dh < -0.5) dh += 1;
  const h = ((a[0] + dh * t) + 1) % 1;
  return [h, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];
}

// Expand a color list to exactly COLOR_STOPS by HSL-interpolated resample.
// Cyclic: the first color is appended to the end before resampling so the
// gradient wraps without a visible seam where the perimeter walk loops back
// (matches upstream's `seamless = [...colors, colors[0]]` packing  -  see
// Appendix A in apps/web/.notes/skia-glow-investigation.md).
function expandColors(colors: string[]): RGBA[] {
  const parsed: RGBA[] = colors.length > 0 ? colors.map(parseColor) : [[0, 0, 0, 0]];
  const closed: RGBA[] = parsed.length > 1 ? [...parsed, parsed[0]!] : parsed;
  if (closed.length === 1) {
    return Array.from({ length: COLOR_STOPS }, () => closed[0]!);
  }
  const hsls: HSL[] = closed.map((c) => rgbToHsl(c[0], c[1], c[2]));
  const out: RGBA[] = [];
  for (let i = 0; i < COLOR_STOPS; i++) {
    const t = (i / (COLOR_STOPS - 1)) * (closed.length - 1);
    const lo = Math.floor(t);
    const hi = Math.min(closed.length - 1, lo + 1);
    const f = t - lo;
    const mixedHsl = lerpHsl(hsls[lo]!, hsls[hi]!, f);
    const rgb = hslToRgb(mixedHsl[0], mixedHsl[1], mixedHsl[2]);
    const alpha = closed[lo]![3] + (closed[hi]![3] - closed[lo]![3]) * f;
    out.push([rgb[0], rgb[1], rgb[2], alpha]);
  }
  return out;
}

function sizeToVec4(g: number | number[]): [number, number, number, number] {
  if (Array.isArray(g)) {
    if (g.length === 4) return [g[0]!, g[1]!, g[2]!, g[3]!];
    if (g.length === 3) return [g[0]!, g[1]!, g[2]!, g[2]!];
    if (g.length === 2) return [g[0]!, g[1]!, g[1]!, g[1]!];
    if (g.length === 1) return [g[0]!, g[0]!, g[0]!, g[0]!];
    return [0, 0, 0, 0];
  }
  return [g, g, g, g];
}

// ---------- uniform layout ----------

type UniformLayout = {
  buffer: Float32Array;
  offsets: {
    resolution: number;
    rectSize: number;
    cornerRadius: number;
    backgroundColor: number;
    borderWidth: number;
    borderProgress: number;
    layerCount: number;
    coverage: number;
    glowSizes: number;
    opacity: number;
    relativeOffset: number;
    layerProgress: number;
    colors_0: number;
    colors_layers: number; // start of u_colors_1
    masterOpacity: number;
    placements: number;
    isBorderAnimated: number;
    coverageFeather: number;
    perimBlend: number;
  };
};

function createUniformLayout(): UniformLayout {
  let off = 0;
  const offsets = {
    resolution: ((): number => { const r = off; off += 2; return r; })(),
    rectSize: ((): number => { const r = off; off += 2; return r; })(),
    cornerRadius: ((): number => { const r = off; off += 1; return r; })(),
    backgroundColor: ((): number => { const r = off; off += 4; return r; })(),
    borderWidth: ((): number => { const r = off; off += 1; return r; })(),
    borderProgress: ((): number => { const r = off; off += 1; return r; })(),
    layerCount: ((): number => { const r = off; off += 1; return r; })(),
    coverage: ((): number => { const r = off; off += MAX_LAYERS; return r; })(),
    glowSizes: ((): number => { const r = off; off += MAX_LAYERS * 4; return r; })(),
    opacity: ((): number => { const r = off; off += MAX_LAYERS; return r; })(),
    relativeOffset: ((): number => { const r = off; off += MAX_LAYERS; return r; })(),
    layerProgress: ((): number => { const r = off; off += MAX_LAYERS; return r; })(),
    colors_0: ((): number => { const r = off; off += COLOR_STOPS * 4; return r; })(),
    colors_layers: ((): number => { const r = off; off += MAX_LAYERS * COLOR_STOPS * 4; return r; })(),
    masterOpacity: ((): number => { const r = off; off += 1; return r; })(),
    placements: ((): number => { const r = off; off += MAX_LAYERS; return r; })(),
    isBorderAnimated: ((): number => { const r = off; off += 1; return r; })(),
    coverageFeather: ((): number => { const r = off; off += 1; return r; })(),
    perimBlend: ((): number => { const r = off; off += 1; return r; })(),
  };
  return { buffer: new Float32Array(off), offsets };
}

function writeStaticPresetUniforms(layout: UniformLayout, preset: GlowPreset) {
  const { buffer, offsets } = layout;
  buffer[offsets.cornerRadius] = preset.cornerRadius;
  buffer[offsets.backgroundColor + 0] = 0;
  buffer[offsets.backgroundColor + 1] = 0;
  buffer[offsets.backgroundColor + 2] = 0;
  buffer[offsets.backgroundColor + 3] = 0;
  buffer[offsets.borderWidth] = 0;
  buffer[offsets.borderProgress] = 0;
  buffer[offsets.isBorderAnimated] = 0;
  buffer[offsets.masterOpacity] = 1;

  const layers = preset.glowLayers.slice(0, MAX_LAYERS);
  buffer[offsets.layerCount] = layers.length;

  // Zero everything per-layer first so a shorter preset doesn't leak old data.
  for (let i = 0; i < MAX_LAYERS; i++) {
    buffer[offsets.coverage + i] = 0;
    buffer[offsets.opacity + i] = 0;
    buffer[offsets.relativeOffset + i] = 0;
    buffer[offsets.placements + i] = 1; // default inside
    const gs = offsets.glowSizes + i * 4;
    buffer[gs + 0] = 0;
    buffer[gs + 1] = 0;
    buffer[gs + 2] = 0;
    buffer[gs + 3] = 0;
  }

  // Border colors u_colors_0  -  unused, but the shader expects valid floats.
  for (let s = 0; s < COLOR_STOPS; s++) {
    const o = offsets.colors_0 + s * 4;
    buffer[o + 0] = 0;
    buffer[o + 1] = 0;
    buffer[o + 2] = 0;
    buffer[o + 3] = 0;
  }

  layers.forEach((layer, i) => {
    buffer[offsets.coverage + i] = Math.max(0, Math.min(1, layer.coverage));
    buffer[offsets.opacity + i] = layer.opacity;
    buffer[offsets.relativeOffset + i] = layer.relativeOffset ?? 0;
    buffer[offsets.placements + i] =
      layer.glowPlacement === 'behind' ? 0 : layer.glowPlacement === 'inside' ? 1 : 2;

    const sz = sizeToVec4(layer.glowSize);
    const gs = offsets.glowSizes + i * 4;
    buffer[gs + 0] = sz[0];
    buffer[gs + 1] = sz[1];
    buffer[gs + 2] = sz[2];
    buffer[gs + 3] = sz[3];

    const expanded = expandColors(layer.colors);
    const colorBase = offsets.colors_layers + i * COLOR_STOPS * 4;
    for (let s = 0; s < COLOR_STOPS; s++) {
      const o = colorBase + s * 4;
      const c = expanded[s]!;
      buffer[o + 0] = c[0];
      buffer[o + 1] = c[1];
      buffer[o + 2] = c[2];
      buffer[o + 3] = c[3];
    }
  });
}

// ---------- CanvasKit lazy loader ----------

// canvaskit-wasm's npm entry references Node-only `fs`/`path`, which Turbopack
// refuses to bundle. We sidestep the bundler entirely by injecting the loader
// as a <script> tag at runtime (this is exactly what reactnativeglow.com does)
// and reading the global `CanvasKitInit` factory it installs. Both the loader
// JS and the WASM are self-hosted under /public.

type CanvasKitModule = any; // canvaskit-wasm has no exported TS types we want to lean on

declare global {
  // eslint-disable-next-line no-var
  var CanvasKitInit: undefined | ((opts: { locateFile: (s: string) => string }) => Promise<CanvasKitModule>);
}

let canvasKitPromise: Promise<CanvasKitModule> | null = null;

function ensureCanvasKitScript(): Promise<void> {
  if (typeof window === 'undefined') return Promise.reject(new Error('no window'));
  if (typeof window.CanvasKitInit === 'function') return Promise.resolve();
  const existing = document.querySelector<HTMLScriptElement>('script[data-canvaskit-loader]');
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('canvaskit loader failed')), { once: true });
    });
  }
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = '/canvaskit.js';
    script.async = true;
    script.dataset.canvaskitLoader = 'true';
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('canvaskit loader failed'));
    document.head.appendChild(script);
  });
}

function loadCanvasKit(): Promise<CanvasKitModule> {
  if (canvasKitPromise) return canvasKitPromise;
  canvasKitPromise = ensureCanvasKitScript().then(() => {
    const init = window.CanvasKitInit;
    if (typeof init !== 'function') throw new Error('CanvasKitInit not on window after loader');
    return init({ locateFile: () => '/canvaskit.wasm' });
  });
  return canvasKitPromise;
}

// ---------- React component ----------

// Intro/outro animation:
//   off          target=0  no canvas, no rAF
//   fade-in      ramp opacity 0→1 over FADE_IN_MS (ease-out)
//   on           opacity = 1 (steady)
//   pulse-out    brief brighten above 1 then settle back, simulates a final
//                "release" beat before the glow disappears
//   fade-out     ramp 1→0 over FADE_OUT_MS (ease-in-out)
//   off (again)  unmount the canvas
const FADE_IN_MS = 950;
const PULSE_MS = 380;
const PULSE_AMOUNT = 0.45; // peak overshoot above 1
const FADE_OUT_MS = 650;

type GlowPhase = 'off' | 'fade-in' | 'on' | 'pulse-out' | 'fade-out';

function easeOutCubic(t: number): number {
  const k = 1 - t;
  return 1 - k * k * k;
}
function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

export function SceneGlowSkia({ visible = true }: { visible?: boolean }) {
  const preset = useSyncExternalStore(glowStore.subscribe, glowStore.get, () => glowStore.get());
  const enabled = useSyncExternalStore(glowStore.subscribe, glowStore.isEnabled, () => false);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const presetRef = useRef(preset);
  presetRef.current = preset;

  // Keep the canvas mounted through the outro animation, then unmount.
  const [mounted, setMounted] = useState(false);

  // Latest `enabled` for the rAF loop to read without re-mounting.
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  useEffect(() => {
    if (visible && enabled) setMounted(true);
    // When enabled flips false, the rAF loop runs the outro then calls
    // setMounted(false)  -  see draw() below.
  }, [enabled, visible]);

  // Locked glow preset values are server-only IP  -  fetch them once the canvas
  // wants to mount. Until they arrive the store holds a placeholder (no layers)
  // so the shader compiles but renders nothing visible.
  useEffect(() => {
    if (glowStore.get().glowLayers.length > 0) return;
    loadPresets().then((p) => {
      if (p) glowStore.set(p.rainbow);
    });
  }, []);

  const shouldRender = visible && mounted;

  useEffect(() => {
    if (!shouldRender) return;
    if (typeof window === 'undefined') return;

    const container: HTMLDivElement | null = containerRef.current;
    const canvas: HTMLCanvasElement | null = canvasRef.current;
    if (!container || !canvas) return;
    // Local aliases so TS narrowing survives inside nested function declarations.
    const c = canvas;
    const ct = container;

    let cancelled = false;
    let raf = 0;
    let surface: any = null;
    let effect: any = null;
    let ck: CanvasKitModule | null = null;

    const layout = createUniformLayout();
    const phase = new Float32Array(MAX_LAYERS);

    let lastSize = { w: 0, h: 0 };
    function resize() {
      // Use offsetWidth/Height so the canvas sizes to the LAYOUT box of the
      // container, ignoring any CSS transforms applied to ancestors. This
      // matters when the glow is rendered inside a Remotion Player whose
      // composition is CSS-scaled to fit the player viewport  -  getBoundingClientRect
      // would return the scaled (visible) rect instead of the composition-resolution
      // rect, sizing the canvas wrong.
      const dpr = Math.min(2, window.devicePixelRatio || 1);
      const cssW = Math.max(1, ct.offsetWidth || Math.floor(ct.getBoundingClientRect().width));
      const cssH = Math.max(1, ct.offsetHeight || Math.floor(ct.getBoundingClientRect().height));
      const pxW = Math.max(1, Math.floor(cssW * dpr));
      const pxH = Math.max(1, Math.floor(cssH * dpr));
      const sizeChanged = pxW !== lastSize.w || pxH !== lastSize.h;
      if (sizeChanged) {
        c.width = pxW;
        c.height = pxH;
        c.style.width = `${cssW}px`;
        c.style.height = `${cssH}px`;
        lastSize = { w: pxW, h: pxH };
      }
      // (Re)build the surface whenever the canvas resized OR CanvasKit just
      // finished loading. The size guard above already skips DOM mutations,
      // so we still avoid thrashing when nothing changed.
      if (ck && (sizeChanged || !surface)) {
        if (surface) {
          try {
            surface.delete();
          } catch {
            /* ignore */
          }
        }
        surface = ck.MakeWebGLCanvasSurface(c);
      }
    }

    const ro = new ResizeObserver(() => resize());
    ro.observe(ct);

    let lastTime = performance.now();
    let elapsed = 0;

    // Intro/outro state machine. Start as 'fade-in' since the effect only
    // runs while mounted, and mount is gated on enabled=true.
    let phaseState: GlowPhase = 'fade-in';
    let phaseStart = performance.now();
    let opacity = 0;

    // Read the container's computed border-radius once at mount. The
    // SceneGlowSkia wrapper sets borderRadius: 'inherit', so this picks up
    // whatever the preview frame defines. Matching the preview frame's actual
    // radius is what makes the rect's corners coincide with the visible clip,
    // so we don't see a separate rounded-rect curve floating inside.
    function readCornerRadius(): number {
      try {
        const v = parseFloat(getComputedStyle(ct).borderTopLeftRadius);
        if (Number.isFinite(v) && v > 0) return v;
      } catch {
        /* ignore */
      }
      return presetRef.current.cornerRadius;
    }

    function draw(now: number) {
      if (cancelled) return;
      raf = requestAnimationFrame(draw);

      const dt = Math.min(0.1, (now - lastTime) / 1000);
      lastTime = now;
      elapsed += dt;
      const dpr = Math.min(2, window.devicePixelRatio || 1);

      // Drive the intro/outro state machine.
      const phaseElapsed = now - phaseStart;
      switch (phaseState) {
        case 'fade-in': {
          const t = Math.min(phaseElapsed / FADE_IN_MS, 1);
          opacity = easeInOutCubic(t);
          if (t >= 1) {
            phaseState = 'on';
            phaseStart = now;
          }
          break;
        }
        case 'on':
          opacity = 1;
          if (!enabledRef.current) {
            phaseState = 'pulse-out';
            phaseStart = now;
          }
          break;
        case 'pulse-out': {
          // Half-sine bump above 1 then settle. Smooth peak then back to 1.
          const t = Math.min(phaseElapsed / PULSE_MS, 1);
          opacity = 1 + Math.sin(t * Math.PI) * PULSE_AMOUNT;
          if (t >= 1) {
            phaseState = 'fade-out';
            phaseStart = now;
          }
          break;
        }
        case 'fade-out': {
          const t = Math.min(phaseElapsed / FADE_OUT_MS, 1);
          opacity = 1 - easeInOutCubic(t);
          if (t >= 1) {
            opacity = 0;
            // Drop out of the loop and unmount the canvas.
            cancelled = true;
            cancelAnimationFrame(raf);
            setMounted(false);
            return;
          }
          break;
        }
        case 'off':
          opacity = 0;
          break;
      }
      // If a fade-out was interrupted by re-enabling, transition back to
      // fade-in. We start from t=0 of the fade-in curve  -  there may be a small
      // visible "rewind" of brightness, but this only happens if the user
      // toggles in/off rapidly, which isn't a normal flow.
      if (enabledRef.current && (phaseState === 'pulse-out' || phaseState === 'fade-out')) {
        phaseState = 'fade-in';
        phaseStart = now;
      }

      const p = presetRef.current;
      const animSpeed = p.animationSpeed ?? 1;
      const layers = p.glowLayers.slice(0, MAX_LAYERS);

      // Refresh preset-derived uniforms each frame (cheap; lets the tuner
      // mutate the preset live without us reconciling diffs).
      writeStaticPresetUniforms(layout, p);

      // Apply the animated master opacity. writeStaticPresetUniforms set this
      // to 1, so we override here to drive the intro/outro envelope.
      layout.buffer[layout.offsets.masterOpacity] = Math.max(0, opacity);

      // Smooth the in-perimeter band edge for partial-coverage layers so the
      // comet's head/tail don't snap on and off like a rectangle.
      layout.buffer[layout.offsets.coverageFeather] = Math.max(0, runtimeKnobs.coverageFeather);

      // Cross-edge color blend softness, written in device pixels but
      // derived from a CANVAS-RELATIVE fraction so the seam-kill behavior
      // looks the same on a 400px-wide preview and a 1500px-wide preview.
      // perimBlend is a fraction of min(canvas_w, canvas_h); multiplied here
      // by the canvas's actual device-pixel size (which is c.width / c.height
      // computed just below).
      // (Actual write happens after w/h are read.)

      // Curvable-specific breathing: scale all per-layer glowSize vec4 entries
      // by a slow sin oscillation. Done AFTER writeStaticPresetUniforms so we
      // don't fight its zero-fill of unused layer slots. Read from
      // runtimeKnobs so the __cvGlow.breathe(...) debug knob takes effect
      // without re-mount.
      if (runtimeKnobs.breatheAmount !== 0) {
        const breathe = 1 + Math.sin((elapsed / runtimeKnobs.breathePeriod) * Math.PI * 2) * runtimeKnobs.breatheAmount;
        for (let i = 0; i < layers.length; i++) {
          const off = layout.offsets.glowSizes + i * 4;
          layout.buffer[off + 0] = layout.buffer[off + 0]! * breathe;
          layout.buffer[off + 1] = layout.buffer[off + 1]! * breathe;
          layout.buffer[off + 2] = layout.buffer[off + 2]! * breathe;
          layout.buffer[off + 3] = layout.buffer[off + 3]! * breathe;
        }
      }

      for (let i = 0; i < MAX_LAYERS; i++) {
        const layer = layers[i];
        const mult = layer?.speedMultiplier ?? 0;
        phase[i] = (phase[i]! + PERIMETER_SPEED * dt * animSpeed * mult) % 1;
        if (phase[i]! < 0) phase[i] = phase[i]! + 1;
        layout.buffer[layout.offsets.layerProgress + i] = phase[i]!;
      }

      if (!surface || !effect || !ck) return;

      const w = c.width;
      const h = c.height;
      const bleedCss = runtimeKnobs.bleedCss;
      const bleedPx = bleedCss * dpr;
      layout.buffer[layout.offsets.resolution + 0] = w;
      layout.buffer[layout.offsets.resolution + 1] = h;
      // Rect is bleedPx larger than the canvas on every side, so the bright
      // peak at d=0 sits just outside the visible area. Canvas pixels are all
      // at d < 0, giving a pure inward fade with no hard outer cutoff.
      layout.buffer[layout.offsets.rectSize + 0] = w + 2 * bleedPx;
      layout.buffer[layout.offsets.rectSize + 1] = h + 2 * bleedPx;
      // Corner radius matches the preview frame's border-radius, shifted out
      // by bleed so the rect's rounded outline traces the same curve as the
      // visible frame (just bleedPx outside it).
      layout.buffer[layout.offsets.cornerRadius] = (readCornerRadius() + bleedCss) * dpr;

      // Edge-blend softness as a fraction of the canvas's smaller dimension.
      // Keeps the seam-kill effect consistent regardless of canvas size.
      const minDim = Math.min(w, h);
      layout.buffer[layout.offsets.perimBlend] = Math.max(0.5, runtimeKnobs.perimBlend * minDim);

      const shader = effect.makeShader(layout.buffer);
      const paint = new ck.Paint();
      paint.setShader(shader);
      const skCanvas = surface.getCanvas();
      skCanvas.clear(ck.TRANSPARENT);
      skCanvas.drawPaint(paint);
      surface.flush();
      paint.delete();
      shader.delete();
    }

    loadCanvasKit()
      .then((mod) => {
        if (cancelled) return;
        ck = mod;
        effect = ck.RuntimeEffect.Make(SHADER_SRC, (err: string) => {
          console.error('[SceneGlowSkia] SkSL compile error:', err);
        });
        if (!effect) {
          console.error('[SceneGlowSkia] failed to compile SkSL shader (no effect returned)');
          return;
        }
        resize();
        lastTime = performance.now();
        raf = requestAnimationFrame(draw);
      })
      .catch((err) => {
        console.error('[SceneGlowSkia] CanvasKit init failed', err);
      });

    return () => {
      cancelled = true;
      cancelAnimationFrame(raf);
      ro.disconnect();
      if (surface) {
        try {
          surface.delete();
        } catch {
          /* ignore */
        }
      }
      if (effect) {
        try {
          effect.delete();
        } catch {
          /* ignore */
        }
      }
    };
  }, [shouldRender]);

  if (!shouldRender) return null;

  return (
    <div
      ref={containerRef}
      aria-hidden
      style={{
        position: 'absolute',
        inset: 0,
        overflow: 'hidden',
        pointerEvents: 'none',
        borderRadius: 'inherit',
        zIndex: 1,
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          display: 'block',
        }}
      />
    </div>
  );
}
