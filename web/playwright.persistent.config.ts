import { defineConfig } from '@playwright/test';

// Focused config for the dedicated persistent browser. It starts no local
// webServer: the selected spec decides its target URL. The persistent CDP
// fixture attaches tests to the long-lived instance when AN_BROWSER_CDP is set.
// The default playwright.config.ts (real backend + Vite, own browser) and CI
// are untouched, so this is purely opt-in.
//
//   AN_BROWSER_CDP="$(scripts/dev/persistent-browser.sh endpoint)" \
//     npm run test:e2e --workspace web -- --config playwright.persistent.config.ts \
//     persistent-browser.spec.ts --retries 0
export default defineConfig({
  testDir: './e2e',
  workers: 1,
  use: {
    trace: 'off',
    // Used only when AN_BROWSER_CDP is unset and the fixture falls back to
    // launching a browser; a CDP attach ignores launch options.
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH },
  },
});
