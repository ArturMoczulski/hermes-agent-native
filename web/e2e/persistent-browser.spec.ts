import { test, expect } from './fixtures';

// Proves the dashboard suite attaches to the dedicated "test" browser over CDP.
// The shared fixture auto-attaches to http://127.0.0.1:9223 when it is running
// and otherwise launches a normal per-run browser, so this passes either way.
// The page runs in an isolated context on the shared browser.
test('persistent browser fixture attaches and renders', async ({ page }) => {
  await page.goto('data:text/html,<title>persistent-browser</title><h1 id="ok">attached</h1>');
  await expect(page).toHaveTitle('persistent-browser');
  await expect(page.locator('#ok')).toHaveText('attached');
});
