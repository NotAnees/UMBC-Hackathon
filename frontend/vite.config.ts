import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    // Bind-mounted source on macOS/Windows does not emit inotify events, so the
    // watcher has to poll or hot reload silently stops working in the container.
    watch: { usePolling: true, interval: 300 },
  },
});
