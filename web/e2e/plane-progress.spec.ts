import { test, expect } from './fixtures';
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


test('saved output link is present in Plane before finish and opens the exact version', async ({ page, request }) => {
  test.setTimeout(90000);
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true, dashboard_url: 'http://127.0.0.1:19220' } });
  const created = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Linked outputs', purpose: 'Write an original fantasy story. E2E_OUTPUT_LINK_HOLD',
    work: { timeout_seconds: 300, max_iterations: 20 },
  } });
  expect(created.status()).toBe(201);
  const { id } = await created.json();
  const api = `${backend}/api/agent-native/agents/${id}`;
  try {
    await expect.poll(async () => {
      const r = await request.get(`${backend}/__e2e__/model-holds/E2E_OUTPUT_LINK_HOLD`, { headers });
      return r.ok() && (await r.json()).entered;
    }, { timeout: 30000 }).toBe(true);
    const agent = await (await request.get(api, { headers })).json();
    expect(agent.work.state).toBe('running');
    const output = agent.work.outputs[0];
    expect(output.version).toBe(1);
    await page.setExtraHTTPHeaders(headers);
    await page.goto(`${backend}/__e2e__/plane-comments/${id}`);
    const link = page.getByRole('link', { name: /Open saved output/ });
    await expect(link).toHaveCount(1);
    await expect(link).toHaveAttribute('href', `http://127.0.0.1:19220/agents/${id}?output=${output.output_id}&version=1`);
    await link.click();
    await expect(page).toHaveURL(new RegExp(`output=${output.output_id}&version=1`));
    await expect(page.getByRole('region', { name: 'Saved outputs', exact: true })).toContainText('At moonrise, Mara found a dragon');
    const pendingSection = page.getByRole('region', { name: 'Pending Plane output sections', exact: true });
    await expect(pendingSection).toContainText('Description update pending');
    await expect(pendingSection).toContainText('simultaneous edits');
    await pendingSection.getByText('Review output references').click();
    await expect(pendingSection.getByRole('textbox', { name: 'Output references' })).toHaveValue(new RegExp(`output=${output.output_id}&version=1`));
    await expect(pendingSection.getByRole('link', { name: /Open saved output/ })).toHaveAttribute('href', `http://127.0.0.1:19220/agents/${id}?output=${output.output_id}&version=1`);

    await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: 'E2E_OUTPUT_LINK_HOLD' } });
    await expect.poll(async () => (await (await request.get(api, { headers })).json()).work.state, { timeout: 30000 }).toBe('completed');
    await expect.poll(async () => {
      const e = await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json();
      return e.comments.some((c: { comment_html: string }) => c.comment_html.includes('Attempt completed'));
    }, { timeout: 15000 }).toBe(true);
    const evidence = await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json();
    expect(evidence.comments.some((c: { comment_html: string }) => c.comment_html.includes('Result recorded: submitted') && c.comment_html.includes('not owner acceptance'))).toBe(true);
    expect(evidence.worker_alive).toBe(false);
    await page.reload();
    await expect(page.getByRole('region', { name: 'Saved outputs', exact: true })).toContainText('At moonrise, Mara found a dragon');
    const finalAgent = await (await request.get(api, { headers })).json();
    const resultId = finalAgent.work.results[0].id;
    await page.goto(`${backend}/__e2e__/plane-comments/${id}`);
    const resultLink = page.getByRole('link', { name: 'Open recorded result', exact: true });
    await expect(resultLink).toHaveAttribute('href', `http://127.0.0.1:19220/agents/${id}#result-${resultId}`);
    await resultLink.click();
    await expect(page.locator(`#result-${resultId}`)).toBeInViewport();
    let terminal = '';
    page.on('websocket', socket => {
      if (new URL(socket.url()).pathname === '/api/pty') socket.on('framereceived', ({ payload }) => {
        terminal += typeof payload === 'string' ? payload : payload.toString('utf8');
      });
    });
    await page.getByRole('link', { name: 'Chat with agent', exact: true }).click();
    await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json()).managed_ready_ids,
      { timeout: 45000 }).toContain(id);
    await page.locator('.xterm-helper-textarea').focus();
    await page.keyboard.type('AN73 describe recorded work');
    const attach = await page.evaluate(() => window.localStorage.getItem('hermes.pty.token.chat'));
    await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/managed-delivery/${id}?attach_token=${attach}`, { headers })).json()).composer?.draft?.input).toBe('AN73 describe recorded work');
    await page.keyboard.press('Enter');
    await expect.poll(() => terminal, { timeout: 45000 }).toContain(`Recorded work: completed; output ${output.output_id}`);
    expect((await (await request.get(api, { headers })).json()).work.state).toBe('completed');


  } finally {
    await request.post(`${api}/work/pause`, { headers });
    await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: 'E2E_OUTPUT_LINK_HOLD' } });
  }
});
