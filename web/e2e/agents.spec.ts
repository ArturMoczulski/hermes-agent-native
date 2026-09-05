import { test, expect } from '@playwright/test';

test('owner creates an inactive agent and sees it after reload', async ({ page }) => {
  await page.addInitScript(() => {
    window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only';
  });
  await page.goto('/agents');
  await page.getByLabel('Agent name', { exact: true }).fill('Metal artist');
  await page.getByLabel('Purpose', { exact: true }).fill('Compose and develop original metal music.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  const agent = page.getByRole('article').filter({ hasText: 'Metal artist' });
  await expect(agent).toContainText('Compose and develop original metal music.');
  await expect(agent).toContainText('Not started');
  await page.reload();
  await expect(agent).toHaveCount(1);
  await expect(agent).toContainText('Compose and develop original metal music.');
});

test('unauthenticated callers cannot list or create agents', async ({ request }) => {
  const url = 'http://127.0.0.1:19219/api/agent-native/agents';
  expect((await request.get(url)).status()).toBe(401);
  expect((await request.post(url, { data: { actor: 'owner', name: 'Forged', purpose: 'No', request_id: 'forged' } })).status()).toBe(401);
});
