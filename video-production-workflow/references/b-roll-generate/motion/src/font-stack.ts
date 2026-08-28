// Resolve a brand-font name (e.g. 'Geist', 'SF Pro', 'Manrope') into a
// CSS font-family string both library previews (browser) and renders can use.
// Mirrors loadBrandFont in packages/render/src/fonts.ts.

const SF_PRO_STACK = `-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro', system-ui, 'Inter', sans-serif`;

const ALIASES: Record<string, string> = {
  Geist: 'Geist, system-ui, sans-serif',
  Manrope: 'Manrope, system-ui, sans-serif',
  Inter: 'Inter, system-ui, sans-serif',
  Outfit: 'Outfit, system-ui, sans-serif',
  'Space Grotesk': '"Space Grotesk", system-ui, sans-serif',
  'Plus Jakarta Sans': '"Plus Jakarta Sans", system-ui, sans-serif',
};

export function brandFontStack(family: string | undefined): string {
  if (!family) return ALIASES.Geist!;
  if (family === 'SF Pro' || family === 'System') return SF_PRO_STACK;
  return ALIASES[family] ?? ALIASES.Geist!;
}
