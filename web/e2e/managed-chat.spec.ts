import { test, expect } from '@playwright/test';

const backend = 'http://127.0.0.1:19219';
const agents = `${backend}/api/agent-native/agents`;
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };
const prompt = 'Managed conversation test: what is your purpose?';
const followup = 'Managed conversation test: remember our conversation?';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
});

test('selected agents use their protected purpose and separate retained native conversations before project work', async ({ page, request }) => {
  test.setTimeout(150000);
  const roots = [];
  for (const [name, purpose] of [['Citadel writer', 'Write original stories about the moonlit citadel.'], ['Ocean writer', 'Write original stories about the glass ocean.']]) {
    const response = await request.post(agents, { headers, data: { request_id: crypto.randomUUID(), name, purpose } });
    expect(response.status()).toBe(201);
    roots.push(await response.json());
  }
  const seen = new Map<string, string>();
  let terminalOutput = '';
  page.on('websocket', (socket) => {
    const path = new URL(socket.url()).pathname;
    socket.on('framereceived', ({ payload }) => {
      const text = typeof payload === 'string' ? payload : payload.toString('utf8');
      if (path === '/api/pty') {
        expect(new URL(socket.url()).searchParams.get('purpose_revision')).toBe('1');
        terminalOutput += text;
      }
      if (path === '/api/events') {
        try {
          const event = JSON.parse(text);
          if (event.params?.type === 'session.info' && event.params.payload?.stored_session_id) {
            seen.set(event.params.payload.managed_agent?.id, event.params.payload.stored_session_id);
          }
        } catch { /* PTY output is not JSON. */ }
      }
    });
  });
  for (const root of roots) {
    await page.goto(`/agents/${root.id}`);
    await page.getByRole('link', { name: 'Chat with agent', exact: true }).click({ timeout: 15000 });
    await expect(page.getByLabel('Conversation agent')).toContainText(root.name);
    await expect(page.getByLabel('Conversation agent')).toContainText(root.purpose);
    await expect(page.locator('.hermes-chat-xterm-host .xterm-screen')).toBeVisible();
    await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json()).managed_ready_ids, { timeout: 45000 }).toContain(root.id);
    terminalOutput = '';
    await page.locator('.xterm-helper-textarea').focus();
    await page.keyboard.type(prompt);
    await page.keyboard.press('Enter');
    await expect.poll(() => terminalOutput, { timeout: 45000 }).toContain(`My purpose: ${root.purpose}`);
    await expect.poll(() => seen.get(root.id)).toBeTruthy();
    const native = await (await request.get(`${backend}/api/sessions/${seen.get(root.id)}/messages`, { headers })).json();
    expect(native.messages.filter((m: { role: string }) => ['user', 'assistant'].includes(m.role)).map((m: { content: string }) => m.content)).toEqual([prompt, `My purpose: ${root.purpose}`]);
    const current = await (await request.get(`${agents}/${root.id}`, { headers })).json();
    expect(current.execution).toBe('not_started');
    expect(current.startup).toEqual(root.startup);
  }
  expect(seen.get(roots[0].id)).not.toBe(seen.get(roots[1].id));
  terminalOutput = '';
  await page.goto(`/agents/${roots[0].id}`);
  await page.getByRole('link', { name: 'Chat with agent', exact: true }).click({ timeout: 15000 });
  await expect(page.getByLabel('Conversation agent')).toContainText(roots[0].name);
  await expect(page.locator('.hermes-chat-xterm-host .xterm-screen')).toBeVisible();
  await expect.poll(() => terminalOutput, { timeout: 30000 }).toContain(`My purpose: ${roots[0].purpose}`);
  terminalOutput = '';
  await page.locator('.xterm-helper-textarea').focus();
  await page.keyboard.type(followup);
  await page.keyboard.press('Enter');
  await expect.poll(() => terminalOutput, { timeout: 45000 }).toContain('Our conversation is retained.');
  terminalOutput = '';
  await page.reload();
  await expect(page.getByLabel('Conversation agent')).toContainText(roots[0].name);
  await expect.poll(() => terminalOutput, { timeout: 30000 }).toContain('Our conversation is retained.');
  const retained = await (await request.get(`${backend}/api/sessions/${seen.get(roots[0].id)}/messages`, { headers })).json();
  expect(retained.messages.filter((m: { role: string }) => ['user', 'assistant'].includes(m.role)).map((m: { content: string }) => m.content)).toEqual([prompt, `My purpose: ${roots[0].purpose}`, followup, 'Our conversation is retained.']);
  const evidence = await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json();
  const managedRequests = evidence.model_requests.filter((r: { last_user: string }) => r.last_user.startsWith('Managed conversation test:'));
  expect(managedRequests).toHaveLength(3);
  for (const r of managedRequests) expect(r.tool_names).toEqual([]);
});
