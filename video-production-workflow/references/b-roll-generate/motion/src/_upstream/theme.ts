// Shared brand tokens  -  single source of truth so the LP, login, project
// list, and project-new pages all read identical values. The editor
// (projects/[id]) uses the dark variants below.

export const CV = {
  // Light surfaces (LP + auth/dashboard pages)
  bg: '#fcfbf8',
  surface: '#f7f4ed',
  border: '#eceae4',
  ink: '#1c1c1c',
  muted: '#5f5f5d',

  // Brand accent
  accent: '#F04E23',
  accentHover: '#D43F17',

  // Dark surfaces  -  calibrated against Lovable's dashboard tokens.
  //   body bg:        hsl(0 0% 11%)   = #1c1c1c
  //   surface (card): hsl(60 3% 15%)  = #272725  (slightly warm grey)
  //   sunken card:    hsl(0 0% 5%)    = #0d0d0d  (project tiles, lower than body)
  //   border:         #272725 (matches surface  -  almost invisible, soft)
  //   primary text:   warm off-white  = #fcfbf8
  //   muted text:     gray-150        = #cdcac4
  //   subtle text:    gray-200        = #c5c1ba
  darkBg: '#1c1c1c',
  darkSurface: '#272725',
  darkSurfaceSunken: '#0d0d0d',
  darkBorder: '#272725',
  darkBorderStrong: '#2f2f2c',
  darkText: '#fcfbf8',
  darkMuted: '#cdcac4',
  darkMutedSubtle: '#c5c1ba',
} as const;

export const RADIUS = {
  pill: 9999,
  input: 12,
  button: 12,
  card: 24,
  cardLg: 32,
} as const;
