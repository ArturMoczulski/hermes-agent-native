import { test as base, expect, type Browser } from '@playwright/test';

// Dashboard e2e specs attach to the dedicated "test" Chromium over CDP so the
// suite reuses one long-lived browser on its own profile, separate from the
// agent's browsing profile. This keeps test cookies/storage from mixing with the
// agent's session. Each test still receives a fresh isolated browser context, so
// this does not trade test isolation for speed.
//
// If the instance is not reachable (CI, a plain local run) the test launches its
// own browser, so default behavior and CI are unchanged. Demo recordings force a
// local launch because video capture needs a Playwright-launched browser.
//
// Start/stop the instance with `scripts/dev/persistent-browser.sh start test`.
// Override the endpoint with AN_BROWSER_E2E_CDP; set it to "off" to force a
// local launch.
const configured = process.env.AN_BROWSER_E2E_CDP?.trim();
const endpoint = configured && configured !== 'off' ? configured : 'http://127.0.0.1:9223';
const forceLocal = process.env.AN_E2E_DEMO === '1' || configured === 'off';

export const test = base.extend({
  browser: [
    async ({ playwright, launchOptions }, use) => {
      let browser: Browser | undefined;
      let shared = false;
      if (!forceLocal) {
        try {
          browser = await playwright.chromium.connectOverCDP(endpoint, { timeout: 3000 });
          shared = true;
        } catch {
          // Instance not running; fall through to a normal per-run browser.
        }
      }
      if (!shared) {
        browser = await playwright.chromium.launch(launchOptions);
      }
      await use(browser as Browser);
      // Leave the shared instance open; close only a browser this run launched.
      if (!shared) await (browser as Browser).close();
    },
    { scope: 'worker' },
  ],
});

export { expect };
export type { APIRequestContext, Locator, Page, TestInfo } from '@playwright/test';
