// Public surface for @curvable/motion. Each component ships:
//   - a React.FC ready to drop into a Remotion <Player> or <Composition>
//   - a TypeScript props type
//   - a frozen `Defaults` object you can spread into <Player inputProps>
//   - a `Meta` object with width/height/fps
//   - a `compute<Name>Duration` helper for variable-length scenes
//
// All fourteen components are deterministic on frame: render the same
// input at the same frame and you get the same pixels, so they slot into
// renderMedia for headless MP4 output the same way they slot into a
// Remotion Player for browser preview.

// Text
export * from './components/cascading-text';
export * from './components/curvable-types';
export * from './components/paste-pill';
export * from './components/slide-reveal';
export * from './components/text-hover';
export * from './components/text-swap';
export * from './components/typewriter';

// Background
export * from './components/bulb-bg';
export * from './components/ellipse-bloom';
export * from './components/grainient-bg';
export * from './components/two-drops-bg';

// Component (composite scenes that combine a backdrop, props, and a
// foreground composition into one launch-tile sized rendering).
export * from './components/floating-stack';
export * from './components/prompt-input';
export * from './components/stats-grid';
