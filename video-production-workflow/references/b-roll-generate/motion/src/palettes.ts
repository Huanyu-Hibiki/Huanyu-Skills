// ============================================================================
// FROZEN  -  DO NOT EDIT.
// ============================================================================
// This file is the library's own copy of the palette recipes. The library
// must NOT depend on @curvable/shared/palettes or any per-project code,
// because per-project sessions edit those files and we never want a
// broken project to break the library page.
//
// Only the library preset components import from this file. The runtime
// app (@curvable/shared, per-project compositions, Remotion renders) keeps
// using its own palettes module.
//
// Any palette-recipe change here is an intentional library design change
// and should be reviewed independently of project work.
// ============================================================================

type OKLCH = { L: number; C: number; H: number };

const hexToRgb = (hex: string): [number, number, number] => {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const n = parseInt(full, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
};

const srgbToLinear = (c: number): number => {
  const x = c / 255;
  return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
};

const rgbToOklab = (r: number, g: number, b: number): [number, number, number] => {
  const lr = srgbToLinear(r);
  const lg = srgbToLinear(g);
  const lb = srgbToLinear(b);
  const l = 0.4122214708 * lr + 0.5363325363 * lg + 0.0514459929 * lb;
  const m = 0.2119034982 * lr + 0.6806995451 * lg + 0.1073969566 * lb;
  const s = 0.0883024619 * lr + 0.2817188376 * lg + 0.6299787005 * lb;
  const l_ = Math.cbrt(l);
  const m_ = Math.cbrt(m);
  const s_ = Math.cbrt(s);
  return [
    0.2104542553 * l_ + 0.793617785 * m_ - 0.0040720468 * s_,
    1.9779984951 * l_ - 2.428592205 * m_ + 0.4505937099 * s_,
    0.0259040371 * l_ + 0.7827717662 * m_ - 0.808675766 * s_,
  ];
};

export const hexToOklch = (hex: string): OKLCH => {
  const [r, g, b] = hexToRgb(hex);
  const [L, a, bb] = rgbToOklab(r, g, b);
  const C = Math.sqrt(a * a + bb * bb);
  let H = (Math.atan2(bb, a) * 180) / Math.PI;
  if (H < 0) H += 360;
  return { L, C, H };
};

export const oklchString = ({ L, C, H }: OKLCH): string =>
  `oklch(${(L * 100).toFixed(3)}% ${C.toFixed(4)} ${H.toFixed(2)})`;

export type BulbPalette = {
  background: string;
  deepGlow: string;
  midGlow: string;
  hotCore: string;
  shadowColor: string;
};

export const bulbPalette = (primaryHex: string): BulbPalette => {
  const p = hexToOklch(primaryHex);
  return {
    // hotCore lifted to match the lightest inner layer of the corner-cycle
    // (drops) palette so the bulb's centre reads as a soft pale glow.
    // midGlow stays at primary so the dome keeps its red identity.
    hotCore:     oklchString(p),
    shadowColor: oklchString(p),
    midGlow:     oklchString({ L: Math.max(0.05, p.L - 0.24), C: p.C * 0.85, H: p.H }),
    deepGlow:    oklchString({ L: Math.max(0.02, p.L - 0.68), C: p.C * 0.40, H: p.H }),
    background:  oklchString({ L: 0.029, C: 0.013, H: p.H }),
  };
};

// Light-background bulb palette. Body (hotCore + midGlow) stay at the brand
// primary; the outer peak-tip layer lifts to near-white so the bulb fades
// INTO the light surface instead of darkening. Shadow color is a darker
// primary so the drop-shadow filter casts a soft brand-tinted shadow rather
// than a glow. Layer opacities differ from the dark-bg version  -  the
// component reads them via `bulbLightLayerOpacities` below.
export const bulbPaletteLight = (primaryHex: string): BulbPalette => {
  const p = hexToOklch(primaryHex);
  return {
    hotCore:     oklchString(p),
    midGlow:     oklchString(p),
    deepGlow:    oklchString({ L: Math.min(0.99, p.L + 0.345), C: p.C * 0.25, H: p.H }),
    shadowColor: oklchString({ L: Math.max(0.05, p.L - 0.18), C: p.C, H: p.H }),
    background:  '#FAFAF7',
  };
};

export const bulbLightLayerOpacities = {
  hotCore: 0.92,
  midGlow: 0.96,
  deepGlow: 0.2,
} as const;

export const bulbDarkLayerOpacities = {
  hotCore: 0.92,
  midGlow: 0.96,
  deepGlow: 1,
} as const;

// Heuristic: returns true if the background hex is "light" (sRGB luma > 0.5).
// Used by presets to pick between dark-bg and light-bg palettes.
export function isLightHex(hex: string): boolean {
  const h = hex.replace('#', '');
  const v =
    h.length === 3
      ? h.split('').map((c) => parseInt(c + c, 16))
      : [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
  const [r, g, b] = v as [number, number, number];
  const luma = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  return luma > 0.5;
}

export type CornerCyclePalette = {
  background: string;
  deep: string;
  halo: string;
  mid: string;
  hot: string;
  core: string;
  shadowColor: string;
};

export type EllipseBloomPalette = {
  // Innermost highlight = primary.
  core: string;
  // Outer ring = darker, slightly desaturated shade of the primary, so the
  // bloom keeps the primary's hue without channel-stacking artefacts.
  outer: string;
};

export const ellipseBloomPalette = (primaryHex: string): EllipseBloomPalette => {
  const p = hexToOklch(primaryHex);
  return {
    core:  oklchString(p),
    outer: oklchString({ L: Math.max(0.05, p.L - 0.15), C: p.C * 0.85, H: p.H }),
  };
};

// Light-background variant. Core stays at the brand primary; the outer ring
// flips to pure white so the bloom fades softly into the light surface
// instead of darkening around it.
export const ellipseBloomPaletteLight = (primaryHex: string): EllipseBloomPalette => {
  const p = hexToOklch(primaryHex);
  return {
    core:  oklchString(p),
    outer: '#ffffff',
  };
};

// Light-background two-drops recipe. Inverse of the dark-bg layer roles:
// under multiply blend on a cream canvas the outer halo needs to be LIGHTER
// than the inner core (the opposite of the dark variant) so the drop reads
// as a soft pastel halo with a saturated centre. Tuned for the 2-layer
// (deep + core) structure.
export type TwoDropsLightLayer = { color: string; opacity: number };

export const twoDropsLightLayers = (primaryHex: string): TwoDropsLightLayer[] => {
  const p = hexToOklch(primaryHex);
  return [
    // Layer 0 (outer "deep"): light pastel tint of primary. Multiplies softly
    // into the cream bg as a barely-there glow.
    {
      color: oklchString({ L: Math.min(0.90, p.L + 0.25), C: p.C * 0.45, H: p.H }),
      opacity: 0.55,
    },
    // Layer 1 (inner "core"): primary at near-full saturation, slightly
    // darkened so it reads cleanly against the cream bg.
    {
      color: oklchString({ L: Math.max(0.4, p.L - 0.05), C: p.C * 0.95, H: p.H }),
      opacity: 0.85,
    },
  ];
};

export const twoDropsLightShadow = (primaryHex: string): string =>
  oklchString(hexToOklch(primaryHex));

export const cornerCyclePalette = (primaryHex: string): CornerCyclePalette => {
  const p = hexToOklch(primaryHex);
  return {
    core:        oklchString(p),
    hot:         oklchString({ L: Math.max(0.05, p.L - 0.10), C: p.C * 0.95, H: p.H }),
    mid:         oklchString({ L: Math.max(0.05, p.L - 0.20), C: p.C * 0.90, H: p.H }),
    halo:        oklchString({ L: Math.max(0.05, p.L - 0.26), C: p.C * 0.85, H: p.H }),
    deep:        oklchString({ L: Math.max(0.05, p.L - 0.32), C: p.C * 0.80, H: p.H }),
    shadowColor: oklchString(p),
    background:  oklchString({ L: 0.029, C: 0.013, H: p.H }),
  };
};