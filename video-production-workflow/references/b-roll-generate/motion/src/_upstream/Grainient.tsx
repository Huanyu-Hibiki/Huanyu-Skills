'use client';

// LP-only non-Remotion port of the curvable-launch GrainientBg shader.
// Drives time via rAF instead of useCurrentFrame so it can be used inside
// the LP template tiles regardless of whether they're inside a Remotion
// <Player>. Same WebGL shader, same uniforms, same look as the Meet
// Curvable video's grainient layer.

import React, { useEffect, useRef } from 'react';
import { Renderer, Program, Mesh, Triangle } from 'ogl';

export type GrainientProps = {
  color1?: string;
  color2?: string;
  color3?: string;
  // Optional external clock (seconds). When set, the rAF + IO loop is
  // bypassed and `iTime` is driven by this value  -  used by the Remotion
  // render pipeline so output frames are deterministic.
  tSecOverride?: number;
};

const STAGE_W = 1920;
const STAGE_H = 1080;
const LOOP_SECONDS = 8;

const TIME_SPEED = 0.25;
const COLOR_BALANCE = 0;
const WARP_STRENGTH = 0.7;
const WARP_FREQUENCY = 5;
const WARP_SPEED = 5.8;
const WARP_AMPLITUDE = 50;
const BLEND_ANGLE = 0;
const BLEND_SOFTNESS = 0.05;
const ROTATION_AMOUNT = 500;
const NOISE_SCALE = 2;
const GRAIN_SCALE = 2;
const CONTRAST = 1.5;
const GAMMA = 1;
const SATURATION = 1;
const CENTER_X = 0;
const CENTER_Y = 0;
const ZOOM = 0.75;

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
uniform float uLoopDuration;
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
  float tb=ta-L;
  float w=ta/L;
  vec3 a=sampleAt(gl_FragCoord.xy,ta);
  vec3 b=sampleAt(gl_FragCoord.xy,tb);
  fragColor=vec4(mix(a,b,w),1.0);
}
`;

export const Grainient: React.FC<GrainientProps> = ({
  color1 = '#f04e23',
  color2 = '#f76c45',
  color3 = '#f04e23',
  tSecOverride,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  // GL state held in a ref so the override-driven useEffect below can
  // push new iTime values + force a render without rebuilding WebGL.
  const stateRef = useRef<{ renderer: Renderer; program: Program; mesh: Mesh } | null>(null);
  const tSecOverrideRef = useRef<number | undefined>(tSecOverride);
  tSecOverrideRef.current = tSecOverride;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Cap device-pixel-ratio to 1. The Grainient is a soft procedural
    // noise gradient  -  there's no high-frequency detail that would
    // benefit from Retina-density oversampling, and the canvas is
    // already rendered into a small tile (~300px on desktop). dpr=1
    // cuts the fragment-shader budget by 4× on Retina displays with
    // no visible difference. (Previously dpr was capped at 2.)
    const renderer = new Renderer({
      webgl: 2,
      alpha: false,
      antialias: false,
      dpr: 1,
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
        iTime: { value: 0 },
        iResolution: { value: new Float32Array([1, 1]) },
        uLoopDuration: { value: LOOP_SECONDS },
        uTimeSpeed: { value: TIME_SPEED },
        uColorBalance: { value: COLOR_BALANCE },
        uWarpStrength: { value: WARP_STRENGTH },
        uWarpFrequency: { value: WARP_FREQUENCY },
        uWarpSpeed: { value: WARP_SPEED },
        uWarpAmplitude: { value: WARP_AMPLITUDE },
        uBlendAngle: { value: BLEND_ANGLE },
        uBlendSoftness: { value: BLEND_SOFTNESS },
        uRotationAmount: { value: ROTATION_AMOUNT },
        uNoiseScale: { value: NOISE_SCALE },
        uGrainAmount: { value: 0 },
        uGrainScale: { value: GRAIN_SCALE },
        uContrast: { value: CONTRAST },
        uGamma: { value: GAMMA },
        uSaturation: { value: SATURATION },
        uCenterOffset: { value: new Float32Array([CENTER_X, CENTER_Y]) },
        uZoom: { value: ZOOM },
        uColor1: { value: new Float32Array(hexToRgb(color1)) },
        uColor2: { value: new Float32Array(hexToRgb(color2)) },
        uColor3: { value: new Float32Array(hexToRgb(color3)) },
      },
    });
    const mesh = new Mesh(gl, { geometry, program });
    stateRef.current = { renderer, program, mesh };

    renderer.setSize(STAGE_W, STAGE_H);
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    const res = program.uniforms.iResolution!.value as Float32Array;
    res[0] = gl.drawingBufferWidth;
    res[1] = gl.drawingBufferHeight;

    // External-clock mode (Remotion render): skip rAF + IO entirely.
    // The component renders once with the current override; later
    // override changes drive a re-render via the dedicated effect
    // below. Returning early keeps the WebGL context alive but idle.
    if (tSecOverrideRef.current !== undefined) {
      program.uniforms.iTime!.value = tSecOverrideRef.current;
      renderer.render({ scene: mesh });
      return () => {
        stateRef.current = null;
        try { container.removeChild(canvas); } catch { /* ignore */ }
      };
    }

    // Visibility-gated rAF loop. While the tile is in the viewport,
    // accumulate elapsed time and render every frame. Off-screen, we
    // cancel the rAF entirely  -  the WebGL context sits idle, costing
    // ~nothing. When the tile scrolls back into view, rAF resumes
    // from the same elapsed value (no time-jump), so the gradient
    // picks up where it left off instead of drifting forward during
    // the off-screen period.
    let raf = 0;
    let running = false;
    let elapsed = 0;
    let lastT = 0;
    const tick = (now: number) => {
      elapsed += (now - lastT) / 1000;
      lastT = now;
      program.uniforms.iTime!.value = elapsed;
      renderer.render({ scene: mesh });
      raf = requestAnimationFrame(tick);
    };
    const start = () => {
      if (running) return;
      running = true;
      lastT = performance.now();
      raf = requestAnimationFrame(tick);
    };
    const stop = () => {
      if (!running) return;
      running = false;
      cancelAnimationFrame(raf);
    };

    // IntersectionObserver toggles the loop based on viewport
    // visibility. Use a small rootMargin so it kicks in just BEFORE
    // the tile becomes visible  -  avoids a blank first frame on scroll.
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) start();
          else stop();
        }
      },
      { rootMargin: '200px 0px' },
    );
    io.observe(container);
    // Render at least one frame immediately so the gradient appears
    // even before IO fires its first callback.
    renderer.render({ scene: mesh });

    return () => {
      io.disconnect();
      stop();
      stateRef.current = null;
      try { container.removeChild(canvas); } catch { /* ignore */ }
    };
  }, [color1, color2, color3]);

  // External-clock driver. When tSecOverride changes, push iTime to
  // the GL program and synchronously re-render so Remotion captures
  // the right frame.
  useEffect(() => {
    if (tSecOverride === undefined) return;
    const s = stateRef.current;
    if (!s) return;
    s.program.uniforms.iTime!.value = tSecOverride;
    s.renderer.render({ scene: s.mesh });
  }, [tSecOverride]);

  return (
    <div
      ref={containerRef}
      style={{ position: 'absolute', inset: 0, overflow: 'hidden', pointerEvents: 'none' }}
      aria-hidden
    />
  );
};
