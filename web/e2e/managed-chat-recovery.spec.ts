import { test, expect } from '@playwright/test';

const backend = 'http://127.0.0.1:19219';
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };
const agents = `${backend}/api/agent-native/agents`;
const draft = 'Managed conversation test: what is your purpose? Keep this citadelDraftUnsentQ7.';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
});

test('unsent managed draft survives native renderer restart and remains with its agent', async ({ page, request }) => {
  test.setTimeout(150000);
  const roots: { id: string; name: string; purpose: string }[] = [];
  for (const [name, purpose] of [
    ['Draft citadel writer', 'Write original stories about the moonlit citadel.'],
    ['Draft ocean writer', 'Write original stories about the glass ocean.'],
  ]) {
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
      if (path === '/api/pty') terminalOutput += text;
      if (path === '/api/events') {
        try {
          const event = JSON.parse(text);
          if (event.params?.type === 'session.info' && event.params.payload?.managed_agent?.id) {
            seen.set(event.params.payload.managed_agent.id, event.params.payload.stored_session_id);
          }
        } catch { /* Non-JSON transport frame. */ }
      }
    });
  });
  const evidence = async () => (await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json());
  const before = (await evidence()).model_requests.length;
  const open = async (root: typeof roots[number]) => {
    terminalOutput = '';
    await page.goto(`/agents/${root.id}`);
    await page.getByRole('link', { name: 'Chat with agent', exact: true }).click();
    await expect(page.getByLabel('Conversation agent')).toContainText(root.name);
    await expect(page.locator('.hermes-chat-xterm-host .xterm-screen')).toBeVisible();
    await expect.poll(async () => (await evidence()).managed_ready_ids, { timeout: 45000 }).toContain(root.id);
    await expect.poll(() => seen.get(root.id)).toBeTruthy();
  };

  await open(roots[0]);
  await page.locator('.xterm-helper-textarea').focus();
  await page.keyboard.type(draft);
  await page.keyboard.press('Control+l');
  await expect.poll(() => terminalOutput).toContain('citadelDraftUnsentQ7');
  const attach = await page.evaluate(() => window.localStorage.getItem('hermes.pty.token.chat'));
  expect(attach).toBeTruthy();

  await open(roots[1]);
  expect(terminalOutput).not.toContain('citadelDraftUnsentQ7');
  expect((await evidence()).model_requests).toHaveLength(before);

  // Expire only the first agent's actual Node/Ink renderer. Its browser token,
  // native gateway/session and protected host storage remain intact.
  const expired = await request.post(`${backend}/__e2e__/expire-managed-renderer`, {
    headers, data: { agent_id: roots[0].id, attach_token: attach },
  });
  expect(expired.status()).toBe(200);
  expect(await expired.json()).toEqual({ expired: 1 });

  await open(roots[0]);
  await page.locator('.xterm-helper-textarea').focus();
  await page.keyboard.press('Control+l');
  await expect.poll(() => terminalOutput, { timeout: 30000 }).toContain('citadelDraftUnsentQ7');
  expect((await evidence()).model_requests).toHaveLength(before);

  // Merely selecting/restoring did not submit. One explicit Enter must send
  // the complete retained draft exactly once through the real native loop.
  terminalOutput = '';
  await page.keyboard.press('Enter');
  await expect.poll(() => terminalOutput, { timeout: 45000 }).toContain(`My purpose: ${roots[0].purpose}`);
  const native = await (await request.get(`${backend}/api/sessions/${seen.get(roots[0].id)}/messages`, { headers })).json();
  expect(native.messages.filter((message: { role: string }) => message.role === 'user').map((message: { content: string }) => message.content)).toEqual([draft]);
  expect((await evidence()).model_requests).toHaveLength(before + 1);
  const other = await (await request.get(`${backend}/api/sessions/${seen.get(roots[1].id)}/messages`, { headers })).json();
  expect(other.messages.filter((message: { role: string }) => message.role === 'user')).toEqual([]);
});
