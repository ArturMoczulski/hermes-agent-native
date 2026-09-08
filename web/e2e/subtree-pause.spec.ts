import { expect, test } from '@playwright/test';

const backend = 'http://127.0.0.1:19219';
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };

test('owner pause visibly and durably pauses an entire active agent subtree', async ({ page, request }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: false } });
  const create = (data: Record<string, unknown>) => request.post(`${backend}/api/agent-native/agents`, {
    headers,
    data: {
      request_id: crypto.randomUUID(), name: 'Pause hierarchy',
      purpose: 'Continue useful work until the owner pauses it.',
      work: { timeout_seconds: 180, max_iterations: 50 },
      ...data,
    },
  });
  const parentResponse = await create({});
  expect(parentResponse.ok()).toBeTruthy();
  const parent = await parentResponse.json();
  const childResponse = await create({ parent_id: parent.id, name: 'Pause hierarchy child' });
  expect(childResponse.ok()).toBeTruthy();
  const child = await childResponse.json();

  await page.goto(`/agents/${parent.id}?view=full`);
  await expect(page.getByText('Pause stops automatic work for this agent and every active descendant.')).toBeVisible();
  await page.getByRole('button', { name: 'Pause', exact: true }).click();

  await expect(page.getByLabel('Execution status')).toHaveText('Paused');
  await expect(page.getByRole('status', { name: 'Agent paused' })).toContainText('This agent and every active descendant are paused.');
  const childState = await (await request.get(`${backend}/api/agent-native/agents/${child.id}`, { headers })).json();
  expect(childState.pause).toMatchObject({ paused: true });
  expect(childState.execution).toBe('paused');
  expect(childState.work.state).toBe('paused');
});
