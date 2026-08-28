/**
 * Remotion Configuration
 * 
 * Configuration options: https://remotion.dev/docs/config
 */

import { Config } from "@remotion/cli/config";

// Set video image format
Config.setVideoImageFormat("jpeg");

// Overwrite output files by default
Config.setOverwriteOutput(true);

// WebGL (Three.js) support for GPU rendering
// "angle" enables GPU rendering on both Mac and Linux
Config.setChromiumOpenGlRenderer("angle");
