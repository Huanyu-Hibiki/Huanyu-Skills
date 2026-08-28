'use client';

// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// Library's own copy of the Grainient background. Per-project agents must
// NOT edit this file. They work on per-project compositions only.
//
// Source shader ported verbatim from React Bits' Grainient. Two adaptations
// for Remotion compatibility:
//   1. iTime is driven by Remotion's useCurrentFrame(), not performance.now,
//      so frames render deterministically in the Player AND on the server.
//   2. We render exactly once per React commit (no rAF loop)  -  the Player
//      drives the frame cadence by re-rendering on each frame tick.
//
// Knobs exposed at the library level: color1, color2, color3.
// Every other shader parameter is baked from the sandbox values the user
// signed off on. Loop duration is 8 s at 30 fps.
// ============================================================================

import React, { useEffect, useRef } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { Renderer, Program, Mesh, Triangle } from 'ogl';

export type GrainientBgProps = {
  // Source-of-truth brand color. Drives the default values of color1/2/3
  // via `deriveGrainientPalette()`; the registry calls that derivation
  // whenever the user changes the global brand color, so the three shades
  // follow along. The user can still edit color1/2/3 manually; those
  // overrides stick until the next time `primary` changes.
  primary: string;
  color1: string;
  color2: string;
  color3: string;
};

// HSL shift helpers  -  used to derive the three shade values from a single
// brand color. Kept simple (HSL not OKLCH) because we just need a perceptual
// lightness shift; the brand hue is preserved exactly.
function hexToHsl(hex: string): { h: number; s: number; l: number } {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return { h: 0, s: 0, l: 0.5 };
  const r = parseInt(m[1]!, 16) / 255;
  const g = parseInt(m[2]!, 16) / 255;
  const b = parseInt(m[3]!, 16) / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  const d = max - min;
  let h = 0;
  let s = 0;
  if (d !== 0) {
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)); break;
      case g: h = ((b - r) / d + 2); break;
      case b: h = ((r - g) / d + 4); break;
    }
    h /= 6;
  }
  return { h, s, l };
}

function hslToHex(h: number, s: number, l: number): string {
  const hue2rgb = (p: number, q: number, t: number): number => {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  };
  let r: number, g: number, b: number;
  if (s === 0) {
    r = g = b = l;
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1 / 3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1 / 3);
  }
  const to = (v: number) => Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0');
  return `#${to(r)}${to(g)}${to(b)}`;
}

// Given a primary hex, return the three shades that drive the gradient.
// Deltas measured from the new sign-off triplet
// (#F04E23 / #C04F00 / #FF6D00) relative to the brand primary `#F04E23`.
// Color 1 = primary exactly. Colors 2 and 3 shift hue + saturation + lightness
// so a non-orange primary still produces three coherent shades with the same
// shape (a slightly warmer shadow + a slightly hotter highlight).
//
// Hue is normalized to [0,1) (HSL convention).
const COLOR1_DELTA_H = 0;
const COLOR1_DELTA_S = 0;
const COLOR1_DELTA_L = 0;
const COLOR2_DELTA_H = 12 / 360;
const COLOR2_DELTA_S = 0.13;
const COLOR2_DELTA_L = -0.16;
const COLOR3_DELTA_H = 13 / 360;
const COLOR3_DELTA_S = 0.13;
const COLOR3_DELTA_L = -0.04;

export function deriveGrainientPalette(primaryHex: string): { color1: string; color2: string; color3: string } {
  const { h, s, l } = hexToHsl(primaryHex);
  const clamp = (v: number) => Math.max(0, Math.min(1, v));
  const wrapHue = (v: number) => ((v % 1) + 1) % 1;
  return {
    color1: hslToHex(wrapHue(h + COLOR1_DELTA_H), clamp(s + COLOR1_DELTA_S), clamp(l + COLOR1_DELTA_L)),
    color2: hslToHex(wrapHue(h + COLOR2_DELTA_H), clamp(s + COLOR2_DELTA_S), clamp(l + COLOR2_DELTA_L)),
    color3: hslToHex(wrapHue(h + COLOR3_DELTA_H), clamp(s + COLOR3_DELTA_S), clamp(l + COLOR3_DELTA_L)),
  };
}

const DEFAULT_PRIMARY = '#F04E23';

export const GrainientBgDefaults: GrainientBgProps = {
  primary: DEFAULT_PRIMARY,
  color1: '#f04e23',
  color2: '#c04f00',
  color3: '#ff6d00',
};

const FPS = 30;
const STAGE_W = 1920;
const STAGE_H = 1080;
const LOOP_FRAMES = 240; // 8 s at 30 fps

export const GrainientBgMeta = {
  width: STAGE_W,
  height: STAGE_H,
  fps: FPS,
  durationFrames: LOOP_FRAMES,
};

export const computeGrainientBgDuration = (): number => LOOP_FRAMES;

// Baked shader settings from the /sandbox/grainient JSON the user signed off
// on (color3=ff6800, warpStrength=0.7, warpSpeed=5.8, zoom=0.75, plus React
// Bits defaults for the rest). Grain is hard-disabled  -  not user-tunable.
const TIME_SPEED      = 0.25;
const COLOR_BALANCE   = 0;
const WARP_STRENGTH   = 0.7;
const WARP_FREQUENCY  = 5;
const WARP_SPEED      = 5.8;
const WARP_AMPLITUDE  = 50;
const BLEND_ANGLE     = 0;
const BLEND_SOFTNESS  = 0.05;
const ROTATION_AMOUNT = 500;
const NOISE_SCALE     = 2;
// Grain amount is now driven directly by the user-controlled knob; this
// constant is no longer used.
const GRAIN_SCALE     = 2;
const GRAIN_ANIMATED  = false;
const CONTRAST        = 1.5;
const GAMMA           = 1;
const SATURATION      = 1;
const CENTER_X        = 0;
const CENTER_Y        = 0;
const ZOOM            = 0.75;

function hexToRgb(hex: string): [number, number, number] {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  if (!m) return [1, 1, 1];
  return [parseInt(m[1]!, 16) / 255, parseInt(m[2]!, 16) / 255, parseInt(m[3]!, 16) / 255];
}

const VERTEX = `#version 300 es
in vec2 position;
void main() {
  gl_Position = vec4(position, 0.0, 1.0);
}
`;

const FRAGMENT = `#version 300 es
precision highp float;
uniform vec2 iResolution;
uniform float iTime;
uniform float uLoopDuration; // seconds; the crossfade window
uniform float uTimeSpeed;
uniform float uColorBalance;
uniform float uWarpStrength;
uniform float uWarpFrequency;
uniform float uWarpSpeed;
uniform float uWarpAmplitude;
uniform float uBlendAngle;
uniform float uBlendSoftness;
uniform float uRotationAmount;
uniform float uNoiseScale;
uniform float uGrainAmount;
uniform float uGrainScale;
uniform float uGrainAnimated;
uniform float uContrast;
uniform float uGamma;
uniform float uSaturation;
uniform vec2 uCenterOffset;
uniform float uZoom;
uniform vec3 uColor1;
uniform vec3 uColor2;
uniform vec3 uColor3;
out vec4 fragColor;
#define S(a,b,t) smoothstep(a,b,t)
mat2 Rot(float a){float s=sin(a),c=cos(a);return mat2(c,-s,s,c);}
vec2 hash(vec2 p){p=vec2(dot(p,vec2(2127.1,81.17)),dot(p,vec2(1269.5,283.37)));return fract(sin(p)*43758.5453);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p),u=f*f*(3.0-2.0*f);float n=mix(mix(dot(-1.0+2.0*hash(i+vec2(0.0,0.0)),f-vec2(0.0,0.0)),dot(-1.0+2.0*hash(i+vec2(1.0,0.0)),f-vec2(1.0,0.0)),u.x),mix(dot(-1.0+2.0*hash(i+vec2(0.0,1.0)),f-vec2(0.0,1.0)),dot(-1.0+2.0*hash(i+vec2(1.0,1.0)),f-vec2(1.0,1.0)),u.x),u.y);return 0.5+0.5*n;}

// All time-dependent computation lives here so we can sample the shader
// twice per pixel  -  once at the current loop time and once at
// (current - loopDuration)  -  and blend them. That guarantees the start and
// end of the loop are pixel-identical, so the player's loop wrap is invisible.
vec3 sampleAt(vec2 C, float iT){
  float t=iT*uTimeSpeed;
  vec2 uv=C/iResolution.xy;
  float ratio=iResolution.x/iResolution.y;
  vec2 tuv=uv-0.5+uCenterOffset;
  tuv/=max(uZoom,0.001);
  float degree=noise(vec2(t*0.1,tuv.x*tuv.y)*uNoiseScale);
  tuv.y*=1.0/ratio;
  tuv*=Rot(radians((degree-0.5)*uRotationAmount+180.0));
  tuv.y*=ratio;
  float frequency=uWarpFrequency;
  float ws=max(uWarpStrength,0.001);
  float amplitude=uWarpAmplitude/ws;
  float warpTime=t*uWarpSpeed;
  tuv.x+=sin(tuv.y*frequency+warpTime)/amplitude;
  tuv.y+=sin(tuv.x*(frequency*1.5)+warpTime)/(amplitude*0.5);
  vec3 colLav=uColor1;
  vec3 colOrg=uColor2;
  vec3 colDark=uColor3;
  float b=uColorBalance;
  float s=max(uBlendSoftness,0.0);
  mat2 blendRot=Rot(radians(uBlendAngle));
  float blendX=(tuv*blendRot).x;
  float edge0=-0.3-b-s;
  float edge1=0.2-b+s;
  float v0=0.5-b+s;
  float v1=-0.3-b-s;
  vec3 layer1=mix(colDark,colOrg,S(edge0,edge1,blendX));
  vec3 layer2=mix(colOrg,colLav,S(edge0,edge1,blendX));
  vec3 col=mix(layer1,layer2,S(v0,v1,tuv.y));
  vec2 grainUv=uv*max(uGrainScale,0.001);
  if(uGrainAnimated>0.5){grainUv+=vec2(iT*0.05);}
  float grain=fract(sin(dot(grainUv,vec2(12.9898,78.233)))*43758.5453);
  col+=(grain-0.5)*uGrainAmount;
  col=(col-0.5)*uContrast+0.5;
  float luma=dot(col,vec3(0.2126,0.7152,0.0722));
  col=mix(vec3(luma),col,uSaturation);
  col=pow(max(col,0.0),vec3(1.0/max(uGamma,0.001)));
  col=clamp(col,0.0,1.0);
  return col;
}

void main(){
  float L=max(uLoopDuration,0.001);
  float ta=mod(iTime,L);
  float tb=ta-L; // negative; sampleAt is defined for any real t
  float w=ta/L; // 0 at loop start, 1 at loop end
  vec3 a=sampleAt(gl_FragCoord.xy,ta);
  vec3 b=sampleAt(gl_FragCoord.xy,tb);
  // At w=0:   100% a == sampleAt(0).        (true current frame)
  // At w=1-ε: ~100% b == sampleAt(-ε)≈sampleAt(0). Same as w=0 → seamless.
  fragColor=vec4(mix(a,b,w),1.0);
}
`;

type GLState = {
  renderer: Renderer;
  program: Program;
  mesh: Mesh;
};

export const GrainientBg: React.FC<GrainientBgProps> = ({
  // `primary` is the brand-color knob; the registry maps it into color1/2/3
  // before the component ever sees it. We accept the prop so the global
  // pill auto-injects, but the GL layer reads color1/2/3 directly.
  primary: _primary,
  color1,
  color2,
  color3,
}) => {
  void _primary;
  const containerRef = useRef<HTMLDivElement | null>(null);
  const stateRef = useRef<GLState | null>(null);
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // One-time WebGL init. We mount a single canvas; everything after this
  // mutates uniforms in place and re-renders synchronously per React commit.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const renderer = new Renderer({
      webgl: 2,
      alpha: false,
      antialias: false,
      dpr: Math.min(typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1, 2),
    });
    const gl = renderer.gl;
    const canvas = gl.canvas;
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.display = 'block';
    container.appendChild(canvas);

    const geometry = new Triangle(gl);
    const program = new Program(gl, {
      vertex: VERTEX,
      fragment: FRAGMENT,
      uniforms: {
        iTime:           { value: 0 },
        iResolution:     { value: new Float32Array([1, 1]) },
        uLoopDuration:   { value: LOOP_FRAMES / FPS },
        uTimeSpeed:      { value: TIME_SPEED },
        uColorBalance:   { value: COLOR_BALANCE },
        uWarpStrength:   { value: WARP_STRENGTH },
        uWarpFrequency:  { value: WARP_FREQUENCY },
        uWarpSpeed:      { value: WARP_SPEED },
        uWarpAmplitude:  { value: WARP_AMPLITUDE },
        uBlendAngle:     { value: BLEND_ANGLE },
        uBlendSoftness:  { value: BLEND_SOFTNESS },
        uRotationAmount: { value: ROTATION_AMOUNT },
        uNoiseScale:     { value: NOISE_SCALE },
        uGrainAmount:    { value: 0 },
        uGrainScale:     { value: GRAIN_SCALE },
        uGrainAnimated:  { value: GRAIN_ANIMATED ? 1 : 0 },
        uContrast:       { value: CONTRAST },
        uGamma:          { value: GAMMA },
        uSaturation:     { value: SATURATION },
        uCenterOffset:   { value: new Float32Array([CENTER_X, CENTER_Y]) },
        uZoom:           { value: ZOOM },
        uColor1:         { value: new Float32Array([1, 1, 1]) },
        uColor2:         { value: new Float32Array([1, 1, 1]) },
        uColor3:         { value: new Float32Array([1, 1, 1]) },
      },
    });
    const mesh = new Mesh(gl, { geometry, program });
    stateRef.current = { renderer, program, mesh };

    // Size the GL buffer to composition pixels (1920×1080), not screen pixels.
    // Inside Remotion's <Player>, getBoundingClientRect() returns post-CSS-
    // scale screen pixels, which would lock the canvas to whatever size the
    // Player happens to be. We size the BUFFER once at composition resolution
    // and let CSS scale the canvas visually via `width/height: 100%`.
    const setSize = () => {
      renderer.setSize(STAGE_W, STAGE_H);
      // ogl's setSize overwrites canvas.style.width/height with fixed px  - 
      // re-apply 100% so the canvas visually fills its parent regardless of
      // how the Player scales the composition.
      canvas.style.width = '100%';
      canvas.style.height = '100%';
      const res = program.uniforms.iResolution!.value as Float32Array;
      res[0] = gl.drawingBufferWidth;
      res[1] = gl.drawingBufferHeight;
    };
    setSize();

    return () => {
      try { container.removeChild(canvas); } catch { /* ignore */ }
      stateRef.current = null;
    };
  }, []);

  // Per-frame: update iTime + colors, then render exactly once. Driven by
  // `frame` (and the props), so Remotion's frame stepping produces
  // deterministic output for both the Player and the server render.
  useEffect(() => {
    const state = stateRef.current;
    if (!state) return;
    const { renderer, program, mesh } = state;
    const u = program.uniforms;

    u.iTime!.value = frame / Math.max(1, fps);

    const c1 = u.uColor1!.value as Float32Array;
    const c2 = u.uColor2!.value as Float32Array;
    const c3 = u.uColor3!.value as Float32Array;
    const r1 = hexToRgb(color1); c1[0] = r1[0]; c1[1] = r1[1]; c1[2] = r1[2];
    const r2 = hexToRgb(color2); c2[0] = r2[0]; c2[1] = r2[1]; c2[2] = r2[2];
    const r3 = hexToRgb(color3); c3[0] = r3[0]; c3[1] = r3[1]; c3[2] = r3[2];

    renderer.render({ scene: mesh });
  }, [frame, fps, color1, color2, color3]);

  return (
    <AbsoluteFill style={{ overflow: 'hidden' }}>
      <div ref={containerRef} style={{ position: 'absolute', inset: 0 }} />
    </AbsoluteFill>
  );
};
