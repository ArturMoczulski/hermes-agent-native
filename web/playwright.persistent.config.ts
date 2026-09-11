import { defineConfig } from '@playwright/test';

// Focused config for the shared "test" browser. It starts no local webServer:
// the selected spec decides its target URL. Every spec now imports the shared
// fixture (web/e2e/fixtures.ts), which auto-attaches to
// http://127.0.0.1:9223 when the test instance is running and otherwise launches
// a normal per-run browser. The default playwright.config.ts (real backend +
// Vite) and CI are unchanged.
//
//   scripts/dev/persistent-browser.sh start test
//   npm run test:e2e --workspace web -- --config playwright.persistent.config.ts \
//     persistent-browser.spec.ts --retries 0
export default defineConfig({
  testDir: './e2e',
  workers: 1,
  use: {
    trace: 'off',
    // Used only when the test instance is unreachable and the fixture falls back
    // to launching a browser; a CDP attach ignores launch options.
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH },
  },
});
