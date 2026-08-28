// Inline SVG so we can tint via currentColor and scale crisply.
// Source: apps/web/public/logo.svg (kept in sync  -  also served as a static
// asset for og-images, favicons, etc.).

type Props = {
  variant?: 'black' | 'white' | 'orange';
  size?: number;
  className?: string;
  // When true, uses a tight viewBox that crops out the path's natural padding
  // and recentres it (the source path sits ~3% above the viewBox centre).
  // Use this when the logo sits inside a chip/circle and you want the mark to
  // fill the container instead of floating in whitespace.
  tight?: boolean;
};

// Tight viewBox derived from the actual path bbox (x:232..848, y:192..818).
// Centre the path (cx=540.35, cy=505.1) in the new viewBox so it renders
// pixel-centred inside any square container.
const TIGHT_VIEWBOX = '200.35 165.1 680 680';

export function LogoMark({ variant = 'black', size = 26, className, tight = false }: Props) {
  const color = variant === 'white' ? '#fff' : variant === 'orange' ? '#F04E23' : '#0b0b0c';
  return (
    <svg
      width={size}
      height={size}
      viewBox={tight ? TIGHT_VIEWBOX : '0 0 1080 1080'}
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Curvable"
      className={className}
      style={{ display: 'inline-block', color }}
    >
      <path
        fill="currentColor"
        d="M522.5 192.6c-2.2.2-9.1.9-15.4 1.5-12.8 1.2-26.4 3.7-41.5 7.5C392 220.2 328.1 265.4 285.1 329c-26.1 38.6-41.4 78.9-49.4 129.5-3 18.9-3.2 64.5-.4 82.5 6.2 39.7 13.9 65.2 29.2 96.5 15.9 32.4 31.9 54.8 57.5 80.6 18.6 18.8 31 29.1 49.2 41.2 43.2 28.7 90 45.3 141.2 50.2 92.8 8.8 181.8-22.8 247.2-88 28.3-28.1 48.8-57.3 64.4-91.5 10.9-24 22-60.2 22-71.9 0-5-3.3-8.4-16.4-17.2-30.4-20.2-68.7-31.1-104.5-29.6-58.7 2.3-111.4 31.7-143.3 79.7-15.7 23.6-25.6 51.3-28.8 80.3-1.5 13.8-2.8 15.7-11.3 15.7-6.5 0-8.7-2.8-9.9-12.7-4.5-36-13.3-60-32.2-87.8-7.2-10.6-27.7-31.7-38.8-39.9-24.3-18.1-54.2-30-85.5-34.1-6.2-.8-12.7-2.2-14.3-3-3.9-2-5.5-7.4-3.5-12.1 1.8-4.3 3.5-5.1 14.1-6.4 37-4.5 68.7-17.8 96-40 34.3-28.1 59.2-73.6 63.4-116.2 1.4-14 2.4-16.6 6.8-18.5 7.9-3.3 13.7.8 14.6 10.5 3.1 31.7 13.4 60.8 30.6 86.7 10.4 15.6 32.2 37.3 48 47.8 24.9 16.4 51.9 26.2 82.5 29.7 41.5 4.7 88.8-8.3 123.2-33.9 10.1-7.5 10.7-9.8 7.3-24.8-10.5-44.9-31.4-88.2-60-124.3-10.2-12.9-35.2-38-48-48.2-45.6-36.2-100.6-59.3-157-65.8-9.7-1.1-49.3-2.1-56.5-1.4"
      />
    </svg>
  );
}
