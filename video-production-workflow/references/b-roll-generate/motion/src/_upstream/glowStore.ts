// Shared glow-preset store. Lives in a module-level singleton so the SceneGlow
// renderer (mounted inside the editor) and the tuner card (mounted on /demo)
// both subscribe to the same preset object and re-render together.

export type GlowLayer = {
  glowPlacement: 'inside' | 'behind' | 'over';
  colors: string[];
  glowSize: number | number[]; // number = uniform; array = [top,right,bottom,left] (we use max for blur)
  opacity: number;
  speedMultiplier: number;
  coverage: number; // 0..1
  relativeOffset?: number;
};

export type GlowPreset = {
  name: string;
  cornerRadius: number;
  animationSpeed: number;
  glowLayers: GlowLayer[];
};

// The locked Apple-Intelligence preset values used to live here. They are
// Curvable IP (weeks of hand-tuning) and now live server-side only in
// apps/web/lib/server/glowPresets.ts, served via /api/v1/glow/preset to
// authenticated allowlisted sessions. Call loadPresets() to fetch them.

// An empty placeholder used until the real preset arrives from the API. Keeps
// the shader uniforms in a renderable state without leaking any IP.
const EMPTY_PRESET: GlowPreset = {
  name: 'placeholder',
  cornerRadius: 50,
  animationSpeed: 1,
  glowLayers: [],
};

// Cache the in-flight promise + the resolved presets so multiple call sites
// during initial mount share one network round-trip instead of each issuing
// its own. The network tab was previously showing 5 parallel/sequential
// /api/v1/glow/preset hits per page load (1+ second each on warm cache).
let presetsCache: { rainbow: GlowPreset; orange: GlowPreset } | null = null;
let presetsInFlight: Promise<{ rainbow: GlowPreset; orange: GlowPreset } | null> | null = null;

export async function loadPresets(): Promise<{ rainbow: GlowPreset; orange: GlowPreset } | null> {
  if (presetsCache) return presetsCache;
  if (presetsInFlight) return presetsInFlight;
  presetsInFlight = (async () => {
    try {
      const res = await fetch('/api/v1/glow/preset', { credentials: 'same-origin' });
      if (!res.ok) return null;
      const data = (await res.json()) as { rainbow: GlowPreset; orange: GlowPreset };
      presetsCache = data;
      return data;
    } catch {
      return null;
    } finally {
      presetsInFlight = null;
    }
  })();
  return presetsInFlight;
}

// Legacy export kept so a stale import doesn't break the build. Resolves to
// the placeholder; consumers should call loadPresets() instead.
export const APPLE_INTELLIGENCE: GlowPreset = EMPTY_PRESET;
export const APPLE_INTELLIGENCE_ORANGE: GlowPreset = EMPTY_PRESET;

let preset: GlowPreset = APPLE_INTELLIGENCE;
const listeners = new Set<() => void>();
let enabled = false;
// When true, the glow stays on regardless of phase changes. Used by the
// /demo tuner so we can inspect the running shader without retriggering
// the Full run flow every few seconds.
let loopMode = false;

// Runtime-mutable rendering knobs. Read every frame by SceneGlowSkia, so
// changes propagate without re-mounting the canvas. Exposed on the debug
// __cvGlow API in dev so we can visually iterate without code edits.
export const runtimeKnobs = {
  breathePeriod: 4.2,
  breatheAmount: 0.22,
  bleedCss: 8,
  // Fraction of the perimeter that the comet's head and tail fade across
  // (for layers with coverage < 1). Values like 0.05-0.15 give a soft band
  // start/end; 0 reverts to the upstream hard-edged behavior.
  coverageFeather: 0.1,
  // Softness of the cross-edge blend, expressed as a FRACTION of the
  // canvas's smaller dimension. The shader picks a weighted average of all 4
  // edges' colors per pixel; this controls how localized that weighting is.
  // Using a fraction (instead of fixed pixels) keeps the seam-killing
  // behavior consistent across viewport sizes. 30% kills the diagonal
  // medial-axis seams completely at the 16:9 preview size while preserving
  // per-edge color character (each rainbow color still dominates its side).
  // Set to 0 to bring the seams back for comparison.
  perimBlend: 0.3,
};

export const glowStore = {
  get: () => preset,
  set: (p: GlowPreset) => {
    preset = p;
    listeners.forEach((l) => l());
  },
  isEnabled: () => enabled,
  setEnabled: (v: boolean) => {
    // Loop mode swallows disable calls so the Editor's phase->glow effect
    // can't fade us out when the demo lands on `done` or `idle`.
    if (loopMode && !v) return;
    enabled = v;
    listeners.forEach((l) => l());
  },
  isLoop: () => loopMode,
  setLoop: (v: boolean) => {
    loopMode = v;
    if (v && !enabled) {
      enabled = true;
    }
    listeners.forEach((l) => l());
  },
  subscribe: (l: () => void) => {
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  },
};

// Debug API exposed on window so we can poke the preset from the DevTools
// console for fast visual iteration. Dev-only  -  never ship to production
// (would let anyone enumerate the locked layer count + tuning knobs).
if (typeof window !== 'undefined' && process.env.NODE_ENV !== 'production') {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (window as any).__cvGlow = {
    solo(idx: number) {
      const p = glowStore.get();
      if (idx < 0 || idx >= p.glowLayers.length) {
        console.warn('[cvGlow] solo: index out of range', idx, 'have', p.glowLayers.length);
        return;
      }
      glowStore.set({ ...p, glowLayers: [p.glowLayers[idx]!] });
    },
    async restore() {
      const presets = await loadPresets();
      if (presets) glowStore.set(presets.rainbow);
    },
    layers() {
      return glowStore.get().glowLayers.map((l, i) => ({
        i,
        placement: l.glowPlacement,
        size: l.glowSize,
        opacity: l.opacity,
        coverage: l.coverage,
        speedMult: l.speedMultiplier,
        colors: l.colors,
      }));
    },
    tweak(idx: number, patch: Partial<GlowLayer>) {
      const p = glowStore.get();
      const next = p.glowLayers.map((l, i) => (i === idx ? { ...l, ...patch } : l));
      glowStore.set({ ...p, glowLayers: next });
    },
    breathe(amount: number | boolean) {
      runtimeKnobs.breatheAmount =
        amount === false ? 0 : amount === true ? 0.22 : amount;
      console.log('[cvGlow] breatheAmount =', runtimeKnobs.breatheAmount);
    },
    bleed(cssPx: number) {
      runtimeKnobs.bleedCss = cssPx;
      console.log('[cvGlow] bleedCss =', cssPx);
    },
    knob(name: keyof typeof runtimeKnobs, value: number) {
      (runtimeKnobs as Record<string, number>)[name] = value;
      console.log('[cvGlow]', name, '=', value);
    },
    knobs: () => ({ ...runtimeKnobs }),
    get: () => glowStore.get(),
    set: (p: GlowPreset) => glowStore.set(p),
  };
}
