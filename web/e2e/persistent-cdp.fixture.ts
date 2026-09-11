import { test as base, expect } from '@playwright/test';

// Attach a spec to the dedicated persistent Chromium
// (scripts/dev/persistent-browser.sh) over CDP instead of launching a fresh
// browser per run. Import { test, expect } from this module rather than
// '@playwright/test'.
//
// With AN_BROWSER_CDP unset this is a transparent passthrough to the normal
// per-run browser, so CI and the default suite are unchanged. With it set, the
// shared instance is used and left open; each test still gets its own isolated
// browser context, preserving the isolation guarantee of the test runner.
//
//   AN_BROWSER_CDP="$(scripts/dev/persistent-browser.sh endpoint)" \
//     npm run test:e2e --workspace web -- --config playwright.persistent.config.ts \
//     persistent-browser.spec.ts --retries 0
const cdpEndpoint = process.env.AN_BROWSER_CDP?.trim();

export const test = cdpEndpoint
  ? base.extend({
      browser: async ({ playwright }, use) => {
        const browser = await playwright.chromium.connectOverCDP(cdpEndpoint);
        // Never close: the instance is shared, long-lived and owned by the script.
        await use(browser);
      },
    })
  : base;

export { expect };
