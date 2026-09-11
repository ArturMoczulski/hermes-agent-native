import { expect, test } from './fixtures';

const backend = 'http://127.0.0.1:19219';
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };

test('a rejected item read and exhausted step limit retain output and continue autonomously', async ({ page, request }) => {
  test.setTimeout(60000);
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } });
  const response = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Read recovery proof',
    purpose: 'Prepare a useful draft. E2E_READ_LIMIT_RECOVERY',
    work: { timeout_seconds: 50, max_iterations: 4 },
  } });
  expect(response.status()).toBe(201);
  const agent = await response.json();
  const api = `${backend}/api/agent-native/agents/${agent.id}`;
  try {
    expect((await request.post(`${api}/cadence`, { headers, data: {
      expected_revision: 1, enabled: true, interval_seconds: 4,
    } })).ok()).toBe(true);
    await page.goto(`/agents/${agent.id}`);
    await expect.poll(async () => {
      const attempts = await (await request.get(`${api}/attempts`, { headers })).json();
      return attempts.some((a: { id: string; state: string }) => a.id === agent.work.id && a.state === 'limit_reached')
        && attempts.some((a: { id: string; state: string }) => a.id !== agent.work.id && a.state === 'completed');
    }, { timeout: 40000 }).toBe(true);
    const current = await (await request.get(api, { headers })).json();
    expect(current.cadence.enabled).toBe(true);
    expect(current.automatic_work.state).not.toBe('framework_failure');
    expect(current.work.outputs.filter((o: { title: string }) => o.title === 'Retained recovery draft')).toHaveLength(1);
    expect(current.work.results.some((r: { summary: string }) => r.summary.includes('Continued automatically'))).toBe(true);
    await expect(page.getByRole('heading', { name: 'Retained recovery draft · Version 1', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Retry failed work', exact: true })).toHaveCount(0);
    await expect(page.getByText('Framework failure', { exact: true })).toHaveCount(0);
  } finally {
    await request.delete(api, { headers });
  }
});
