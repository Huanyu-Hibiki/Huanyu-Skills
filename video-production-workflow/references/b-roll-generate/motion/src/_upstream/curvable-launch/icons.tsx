'use client';

import React from 'react';

export const ArrowUpIcon: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 19V5" />
    <path d="M5 12l7-7 7 7" />
  </svg>
);

export const PlayGlyph: React.FC<{ size?: number }> = ({ size = 12 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M8 5v14l11-7z" />
  </svg>
);

export const FrameBackGlyph: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M15 18l-6-6 6-6" />
  </svg>
);

export const FrameForwardGlyph: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 6l6 6-6 6" />
  </svg>
);

export const JumpStartGlyph: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <rect x="4" y="5" width="2.4" height="14" rx="1" />
    <path d="M20 5v14l-12-7z" />
  </svg>
);

export const JumpEndGlyph: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <rect x="17.6" y="5" width="2.4" height="14" rx="1" />
    <path d="M4 5v14l12-7z" />
  </svg>
);

export const FullscreenGlyph: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 9V4h5" />
    <path d="M20 9V4h-5" />
    <path d="M4 15v5h5" />
    <path d="M20 15v5h-5" />
  </svg>
);

export const MinimizeGlyph: React.FC<{ size?: number }> = ({ size = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    <path d="M9 4v5H4" />
    <path d="M15 4v5h5" />
    <path d="M9 20v-5H4" />
    <path d="M15 20v-5h5" />
  </svg>
);

export const CheckGlyph: React.FC<{ size?: number; color?: string }> = ({ size = 10, color = '#fff' }) => (
  <svg width={size} height={size} viewBox="0 0 10 10" fill="none">
    <path d="M2 5.2L4.1 7.2L8 3" stroke={color} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

export { LogoMark } from '../LogoMark';
