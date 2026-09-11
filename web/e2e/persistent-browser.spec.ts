import { test, expect } from './persistent-cdp.fixture';

// Proves the dashboard suite can attach to the dedicated persistent browser
// over CDP. Runs against the shared instance when AN_BROWSER_CDP is set, and
// otherwise falls back to a normal per-run browser (so the default suite is
// unaffected). The page runs in an isolated context on the shared browser.
test('persistent browser fixture attaches and renders', async ({ page }) => {
  await page.goto('data:text/html,<title>persistent-browser</title><h1 id="ok">attached</h1>');
  await expect(page).toHaveTitle('persistent-browser');
  await expect(page.locator('#ok')).toHaveText('attached');
});
