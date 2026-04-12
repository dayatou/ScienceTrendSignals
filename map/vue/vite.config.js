import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  base: "/ScienceTrendSignals/",
  plugins: [vue()],
  server: {
    host: "0.0.0.0",
  },
});
