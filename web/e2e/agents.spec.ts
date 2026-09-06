import { test, expect } from '@playwright/test';

const token = 'agent-native-local-e2e-only';
const api = 'http://127.0.0.1:19219/api/agent-native/agents';
const headers = { 'X-Hermes-Session-Token': token };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only';
  });
});

test('creation opens its agent detail and retains one startup request across reloads', async ({ page, request }) => {
  await page.goto('/agents');
  await page.getByLabel('Agent name', { exact: true }).fill('Fantasy writer');
  await page.getByLabel('Purpose', { exact: true }).fill('Develop a fantasy world and write original stories.');
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/api/agent-native/agents') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  const agent = await (await responsePromise).json();
  await expect(page).toHaveURL(new RegExp(`/agents/${agent.id}$`));
  await expect(page.getByRole('main').getByRole('heading', { name: 'Fantasy writer', exact: true })).toBeVisible();
  await expect(page.getByLabel('Agent purpose')).toContainText('Develop a fantasy world and write original stories.');
  await expect(page.getByLabel('Startup request')).toContainText('First review requested');
  await expect(page.getByLabel('Execution status')).toContainText('Not started');
  expect(agent.startup.cause).toBe('creation');
  expect(agent.startup.soul_revision).toBe(agent.soul_revision);
  await page.reload();
  await expect(page.getByLabel('Startup request')).toContainText(agent.startup.id);
  await page.getByRole('link', { name: 'All agents', exact: true }).click();
  const row = page.getByRole('article').filter({ hasText: 'Fantasy writer' });
  await expect(row).toHaveCount(1);
  await row.getByRole('link', { name: 'Fantasy writer', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/agents/${agent.id}$`));
  expect((await (await request.get(`${api}/${agent.id}`, { headers })).json()).startup).toEqual(agent.startup);
});

test('retry after a lost response and reload opens the original agent and startup request', async ({ page, request }) => {
  let first: { id: string; startup: { id: string } } | undefined;
  let loseResponse = true;
  await page.route('**/api/agent-native/agents', async (route) => {
    if (route.request().method() !== 'POST' || !loseResponse) return route.continue();
    loseResponse = false;
    const response = await route.fetch(); // The real backend commits before the reply is lost.
    first = await response.json();
    await route.abort('failed');
  });
  await page.goto('/agents');
  await page.getByLabel('Agent name', { exact: true }).fill('Writer with lost response');
  await page.getByLabel('Purpose', { exact: true }).fill('Write a fantasy adventure.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Could not confirm creation');
  await page.reload();
  await expect(page.getByLabel('Agent name', { exact: true })).toHaveValue('Writer with lost response');
  await expect(page.getByLabel('Purpose', { exact: true })).toHaveValue('Write a fantasy adventure.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/agents/${first!.id}$`));
  await expect(page.getByLabel('Startup request')).toContainText(first!.startup.id);
  const agents = await (await request.get(api, { headers })).json();
  expect(agents.filter((agent: { name: string }) => agent.name === 'Writer with lost response')).toHaveLength(1);
});

test('unknown detail shows a recoverable error without inventing an agent', async ({ page }) => {
  await page.goto('/agents/not-a-real-agent');
  await expect(page.getByRole('alert')).toContainText('Could not load this agent');
  await expect(page.getByRole('link', { name: 'All agents', exact: true })).toBeVisible();
});

test('unauthenticated callers cannot list, create or inspect agents', async ({ request }) => {
  expect((await request.get(api)).status()).toBe(401);
  expect((await request.post(api, { data: { actor: 'owner', name: 'Forged', purpose: 'No', request_id: 'forged' } })).status()).toBe(401);
  expect((await request.get(`${api}/missing`)).status()).toBe(401);
});


test('storage failure prevents an unrecoverable creation write', async ({ page, request }) => {
  await page.goto('/agents');
  await page.getByLabel('Agent name', { exact: true }).fill('Writer without storage');
  await page.getByLabel('Purpose', { exact: true }).fill('Write stories.');
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) {
      if (this === window.sessionStorage) throw new DOMException('Storage unavailable', 'QuotaExceededError');
      return original.call(this, key, value);
    };
  });
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('nothing was sent');
  const agents = await (await request.get(api, { headers })).json();
  expect(agents.filter((agent: { name: string }) => agent.name === 'Writer without storage')).toHaveLength(0);
});
