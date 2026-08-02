/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  test: {
    // Web Crypto's SubtleCrypto is available globally in Node - no jsdom
    // needed just to test the crypto module.
    environment: "node",
  },
});
