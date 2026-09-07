import { test, expect } from '@playwright/test';
const backend = 'http://127.0.0.1:19219';
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };

test('selected work posts progress in Plane before the native worker finishes', async ({ page, request }) => {
  test.setTimeout(60000);
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } });
  const marker = 'E2E_PLAN_HOLD_PROGRESS';
  const response = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Continuous progress', purpose: `Write original fantasy stories. ${marker}`,
    work: { timeout_seconds: 300, max_iterations: 20 },
  } });
  expect(response.status()).toBe(201);
  const { id } = await response.json();
  const api = `${backend}/api/agent-native/agents/${id}`;
  try {
    await expect.poll(async () => {
      const r = await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers });
      return r.ok() && (await r.json()).entered;
    }, { timeout: 30000 }).toBe(true);
    const agent = await (await request.get(api, { headers })).json();
    const evidence = await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json();
    expect(agent.work.state).toBe('running');
    expect(evidence.worker_alive).toBe(true);
    expect(evidence.comments.some((c: { issue: string; comment_html: string }) => c.issue === agent.work.focus.item_id && c.comment_html.includes('Selected work item') && c.comment_html.includes(agent.work.id))).toBe(true);
    await page.goto(`/agents/${id}`);
    const reporting = page.getByRole('region', { name: 'Plane progress', exact: true });
    await expect(reporting).toContainText('Confirmed');
    await expect(reporting).toContainText('Selected work item');
    await page.reload();
    await expect(reporting).toContainText('Confirmed');
    const after = await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json();
    expect(after.comments).toHaveLength(evidence.comments.length);
    await page.getByRole('button', { name: 'Pause', exact: true }).click();
    await expect(page.getByLabel('Execution status')).toHaveText('Paused');
  } finally {
    await request.post(`${api}/work/pause`, { headers });
    await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker } });
  }
});


test('owner verbosity persists and governs native checkpoint reporting', async ({ page, request }) => {
  test.setTimeout(60000);
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } });
  const response = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Detailed progress', purpose: 'Write original fantasy stories. E2E_PROGRESS_CHECKPOINTS',
  } });
  expect(response.status()).toBe(201);
  const { id } = await response.json();
  const api = `${backend}/api/agent-native/agents/${id}`;
  await page.goto(`/agents/${id}`);
  const setting = page.getByRole('region', { name: 'Progress reporting settings', exact: true });
  await expect(setting.getByLabel('Progress verbosity', { exact: true })).toHaveValue('standard');
  await setting.getByLabel('Progress verbosity', { exact: true }).selectOption('detailed');
  await setting.getByRole('button', { name: 'Save reporting settings', exact: true }).click();
  await expect(setting).toContainText('Saved');
  await page.reload();
  await expect(setting.getByLabel('Progress verbosity', { exact: true })).toHaveValue('detailed');
  await expect.poll(async () => (await (await request.get(api, { headers })).json()).setup.status, { timeout: 30000 }).toBe('ready');
  const start = await request.post(`${api}/work`, { headers, data: { timeout_seconds: 300, max_iterations: 20, expected_revision: 1 } });
  expect(start.ok()).toBe(true);
  try {
    await expect.poll(async () => {
      const r = await request.get(`${backend}/__e2e__/model-holds/E2E_PROGRESS_CHECKPOINTS`, { headers });
      return r.ok() && (await r.json()).entered;
    }, { timeout: 30000 }).toBe(true);
    const evidence = await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json();
    expect(evidence.worker_alive).toBe(true);
    expect(evidence.comments.some((c: { comment_html: string }) => c.comment_html.includes('Outline prepared'))).toBe(true);
    expect(evidence.comments.some((c: { comment_html: string }) => c.comment_html.includes('Scene beats checked'))).toBe(true);
    await expect(page.getByRole('region', { name: 'Plane progress', exact: true })).toContainText('Scene beats checked');
  } finally {
    await request.post(`${api}/work/pause`, { headers });
    await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: 'E2E_PROGRESS_CHECKPOINTS' } });
  }
});
