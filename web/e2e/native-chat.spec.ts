import { test, expect } from '@playwright/test';

const backend = 'http://127.0.0.1:19219';
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };
const opener = 'Native browser test: remember the moonlit citadel.';
const reply = 'The moonlit citadel is remembered in this conversation.';
const followup = 'Native browser test: what place did I mention?';
const recalled = 'You mentioned the moonlit citadel before reloading the browser.';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only';
  });
});

test('native chat sends through the TUI and Hermes engine, then resumes its persisted conversation', async ({ page, request }, testInfo) => {
  test.setTimeout(120000);
  let terminalOutput = '';
  const inputFrames: string[] = [];
  page.on('websocket', (socket) => {
    if (new URL(socket.url()).pathname !== '/api/pty') return;
    socket.on('framesent', ({ payload }) => inputFrames.push(typeof payload === 'string' ? payload : payload.toString('utf8')));
    socket.on('framereceived', ({ payload }) => {
      terminalOutput += typeof payload === 'string' ? payload : payload.toString('utf8');
    });
  });
  await page.goto('/chat');
  const terminal = page.locator('.hermes-chat-xterm-host .xterm-screen');
  await expect(terminal).toBeVisible();
  await expect.poll(async () => {
    const response = await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers });
    return (await response.json()).ready;
  }, { timeout: 60000 }).toBe(true);
  await page.locator('.xterm-helper-textarea').focus();
  await page.keyboard.type(opener);
  await page.keyboard.press('Enter');
  await expect.poll(() => terminalOutput, { timeout: 45000 }).toContain(reply);

  await expect.poll(async () => {
    const data = await (await request.get(`${backend}/api/sessions?min_messages=2`, { headers })).json();
    return data.sessions.length;
  }).toBe(1);
  const nativeSessions = await (await request.get(`${backend}/api/sessions?min_messages=2`, { headers })).json();
  expect(nativeSessions.sessions).toHaveLength(1);
  const sessionId = nativeSessions.sessions[0].id;
  const messagesUrl = `${backend}/api/sessions/${sessionId}/messages`;
  await expect.poll(async () => {
    const data = await (await request.get(messagesUrl, { headers })).json();
    return data.messages.filter((message: { role: string; content: string }) => message.role === 'assistant').map((message: { content: string }) => message.content);
  }).toEqual([reply]);
  const firstEvidence = await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json();
  expect(firstEvidence.model_requests).toHaveLength(1);
  expect(firstEvidence.model_requests[0].last_user).toContain(opener);
  expect(firstEvidence.model_requests[0].model).toBe('native-browser-fixture');

  terminalOutput = '';
  await page.reload();
  await expect(terminal).toBeVisible();
  await expect.poll(() => terminalOutput, { timeout: 30000 }).toContain(reply);
  await page.locator('.xterm-helper-textarea').focus();
  await page.keyboard.type(followup);
  await page.keyboard.press('Enter');
  await expect.poll(() => terminalOutput, { timeout: 45000 }).toContain(recalled);
  await testInfo.attach('terminal-input', { body: JSON.stringify(inputFrames), contentType: 'application/json' });
  await expect.poll(async () => {
    const data = await (await request.get(messagesUrl, { headers })).json();
    return data.messages.filter((message: { role: string }) => message.role === 'user' || message.role === 'assistant').map((message: { content: string }) => message.content);
  }).toEqual([opener, reply, followup, recalled]);
  const finalEvidence = await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json();
  expect(finalEvidence.model_requests).toHaveLength(2);
  expect(finalEvidence.model_requests[1].history_has_first_exchange).toBe(true);
  expect((await (await request.get(`${backend}/api/sessions?min_messages=2`, { headers })).json()).sessions.map((session: { id: string }) => session.id)).toEqual([sessionId]);
  expect(terminalOutput).not.toContain('Chat unavailable');
  await expect(page.getByRole('button', { name: 'Reconnect chat', exact: true })).not.toBeVisible();
});

test('native terminal rejects an unauthenticated WebSocket', async ({ page }) => {
  await page.goto('/agents');
  const result = await page.evaluate(() => new Promise<{ opened: boolean; code: number }>((resolve) => {
    const socket = new WebSocket('ws://127.0.0.1:19219/api/pty');
    let opened = false;
    socket.onopen = () => { opened = true; };
    socket.onclose = (event) => resolve({ opened, code: event.code });
  }));
  expect(result.opened).toBe(false);
  expect(result.code).toBe(1006);
});
