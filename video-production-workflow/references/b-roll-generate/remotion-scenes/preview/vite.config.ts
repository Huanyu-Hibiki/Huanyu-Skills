import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [react()],
  base: "/remotion-scenes/",
  resolve: {
    alias: {
      "@scenes": fileURLToPath(new URL("../src/scenes", import.meta.url)),
      "@common": fileURLToPath(new URL("../src/common", import.meta.url)),
    },
    dedupe: ["react", "react-dom", "remotion", "@remotion/player"],
  },
  optimizeDeps: {
    include: ["react", "react-dom", "remotion", "@remotion/player"],
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});
