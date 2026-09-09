import { test, expect } from '@playwright/test';
const backend = 'http://127.0.0.1:19219';
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };
test('owner feedback reaches a native worker and its saved output', async ({ page, request }) => {
  test.setTimeout(90000);
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } });
  const response = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Feedback writer', purpose: 'Write drafts. E2E_FEEDBACK_HOLD',
    work: { timeout_seconds: 180, max_iterations: 12 } } });
  expect(response.status()).toBe(201);
  const { id } = await response.json();
  const api = `${backend}/api/agent-native/agents/${id}`;
  try {
    await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/model-holds/E2E_FEEDBACK_HOLD`, { headers })).json()).entered, { timeout: 30000 }).toBe(true);
    await page.goto(`/agents/${id}`);
    await page.getByRole('link', { name: 'Full view', exact: true }).click();
    const form = page.getByRole('region', { name: 'Feedback for work', exact: true });
    await expect(form).toBeVisible();
    await form.getByLabel('Direction for subsequent work').fill('Give the dragon a hopeful ending.');
    await form.getByRole('button', { name: 'Send feedback' }).click();
    await expect(form).toContainText('Pending');
    await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: 'E2E_FEEDBACK_HOLD' } });
    await expect(form).toContainText('Agent reports handled', { timeout: 30000 });
    await expect.poll(async () => (await (await request.get(api, { headers })).json()).work.state).toBe('completed');
    const output = (await (await request.get(api, { headers })).json()).work.outputs[0];
    await page.goto(`/agents/${id}?output=${output.output_id}&version=1`);
    await expect(page.getByRole('article', { name: 'Output reader', exact: true })).toContainText('Give the dragon a hopeful ending.');
  } finally {
    await request.post(`${api}/work/pause`, { headers });
    await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: 'E2E_FEEDBACK_HOLD' } });
  }
});
