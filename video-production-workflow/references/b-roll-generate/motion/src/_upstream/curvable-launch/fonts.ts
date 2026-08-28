'use client';

import { loadFont as loadGeist } from '@remotion/google-fonts/Geist';
import { loadFont as loadGeistMono } from '@remotion/google-fonts/GeistMono';

const geist = loadGeist('normal', { weights: ['400', '500', '600', '700'] });
const geistMono = loadGeistMono('normal', { weights: ['400', '500'] });

export const SANS_FAMILY = geist.fontFamily;
export const MONO_FAMILY = geistMono.fontFamily;
