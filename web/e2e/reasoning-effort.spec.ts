import { test, expect, type Page } from '@playwright/test';

const backend = 'http://127.0.0.1:19219';
const api = `${backend}/api/agent-native`;
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };
const model = 'native-browser-fixture';
const provider = 'custom:browser-fixture';

async function selectEffort(page: Page, effort: string) {
  const reasoning = page.getByRole('dialog').getByLabel('Reasoning effort', { exact: true });
  await expect(reasoning).toBeVisible();
  await expect(reasoning).toBeEnabled();
  await expect(reasoning.locator(`option[value="${effort}"]`)).toHaveCount(1);
  await reasoning.selectOption(effort);
}

async function choose(page: Page, effort: string, action = 'Save') {
  const dialog = page.getByRole('dialog');
  await dialog.getByText('browser-fixture', { exact: true }).click();
  await dialog.getByText(model, { exact: true }).click();
  await selectEffort(page, effort);
  await expect(dialog.getByRole('button', { name: action, exact: true })).toBeEnabled();
  await dialog.getByRole('button', { name: action, exact: true }).click();
  await expect(dialog).toHaveCount(0);
}

test('reasoning effort persists through defaults and retries and changes only subsequent attempts', async ({ page, request, context }) => {
  test.setTimeout(210000);
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } });
  await page.goto('/agents');
  await page.getByRole('region', { name: 'Default agent model', exact: true }).getByRole('button', { name: 'Change default model', exact: true }).click();
  await choose(page, 'low');
  await page.getByLabel('Agent name', { exact: true }).fill('Inherited reasoning');
  await page.getByLabel('Purpose', { exact: true }).fill('Use the reasoning effort copied from the creation default.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Agent model', exact: true })).toContainText('Reasoning: Low');
  const inheritedId = page.url().split('/').at(-1)!;
  const get = async (id: string) => (await (await request.get(`${api}/agents/${id}`, { headers })).json());
  expect((await get(inheritedId)).model_selection).toMatchObject({ provider, model, reasoning_effort: 'low', source: 'default' });
  await page.getByRole('link', { name: 'All agents', exact: true }).click();
  const marker = `E2E_WRITER_HOLD_EFFORT_${Date.now()}`;
  await page.getByLabel('Agent name', { exact: true }).fill('Explicit reasoning writer');
  await page.getByLabel('Purpose', { exact: true }).fill(`Write original stories about the moonlit citadel. ${marker}`);
  await page.getByLabel('Maximum run time (seconds)', { exact: true }).fill('300');
  await page.getByLabel('Maximum model steps', { exact: true }).fill('20');
  await page.getByRole('button', { name: 'Choose a different model', exact: true }).click();
  const picker = page.getByRole('dialog');
  await picker.getByText('browser-fixture', { exact: true }).click();
  await picker.getByText(model, { exact: true }).click();
  await selectEffort(page, 'high');
  await picker.getByText('native-browser-fixture-small', { exact: true }).click();
  await expect(picker).toContainText('Choose a supported reasoning effort');
  await expect(picker.getByRole('button', { name: 'Use model', exact: true })).toBeDisabled();
  await picker.getByText(model, { exact: true }).click();
  await expect(picker.getByLabel('Reasoning effort', { exact: true })).toHaveValue('high');
  await picker.getByRole('button', { name: 'Use model', exact: true }).click();
  let lost = false;
  let created: { id: string } | undefined;
  await page.route('**/api/agent-native/agents', async route => {
    if (route.request().method() !== 'POST' || lost) return route.continue();
    lost = true;
    created = await (await route.fetch()).json();
    await route.abort('failed');
  });
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Could not confirm creation');
  await page.reload();
  await expect(page.getByRole('group', { name: 'Model for this agent', exact: true })).toContainText('Reasoning: High');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/agents/${created!.id}$`));
  const id = created!.id;
  const work = page.getByRole('region', { name: 'Agent work', exact: true });
  await expect.poll(async () => {
    const response = await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers });
    return response.ok() && (await response.json()).entered;
  }, { timeout: 45000 }).toBe(true);
  await expect(work).toContainText('Reasoning: High');
  const settings = page.getByRole('region', { name: 'Agent model', exact: true });
  await settings.getByRole('button', { name: 'Change agent model', exact: true }).click();
  await selectEffort(page, 'low');
  await page.getByRole('dialog').getByRole('button', { name: 'Save', exact: true }).click();
  await expect(settings).toContainText('Reasoning: Low');
  await expect(work).toContainText('Reasoning: High');
  const active = await get(id);
  expect(active.model_selection).toMatchObject({ provider, model, reasoning_effort: 'low' });
  expect(active.work.model_selection.reasoning_effort).toBe('high');
  expect((await get(inheritedId)).model_selection.reasoning_effort).toBe('low');
  await work.getByRole('button', { name: 'Pause', exact: true }).click();
  await expect(page.getByLabel('Execution status')).toHaveText('Paused', { timeout: 30000 });

  let terminal = '';
  page.on('websocket', socket => {
    if (new URL(socket.url()).pathname === '/api/pty') socket.on('framereceived', ({ payload }) => { terminal += typeof payload === 'string' ? payload : payload.toString('utf8'); });
  });
  await page.getByRole('link', { name: 'Chat with agent', exact: true }).click();
  await expect(page.getByLabel('Conversation agent')).toContainText('Reasoning: Low');
  await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json()).managed_ready_ids, { timeout: 45000 }).toContain(id);
  let messagesSent = 0;
  const send = async (text: string) => {
    const attach = await page.evaluate(() => window.localStorage.getItem('hermes.pty.token.chat'));
    const composer = async () => (await (await request.get(`${backend}/__e2e__/managed-delivery/${id}?attach_token=${attach}`, { headers })).json()).composer;
    if (messagesSent > 0) await expect.poll(async () => (await composer())?.pending, { timeout: 30000 }).toBeNull();
    await page.locator('.xterm-helper-textarea').focus();
    await page.keyboard.type(text);
    await expect.poll(async () => (await composer())?.draft?.input).toBe(text);
    await page.keyboard.press('Enter');
    messagesSent += 1;
  };
  const opener = 'Managed conversation test: what is your purpose?';
  await send(opener);
  await expect.poll(() => terminal, { timeout: 45000 }).toContain('My purpose: Write original stories about the moonlit citadel.');
  const chatHold = `REASONING_CHAT_${Date.now()}`;
  await request.post(`${backend}/__e2e__/hold-model`, { headers, data: { marker: chatHold } });
  const heldPrompt = `Wait for the effort change ${chatHold}`;
  await send(heldPrompt);
  await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/model-holds/${chatHold}`, { headers })).json()).entered, { timeout: 45000 }).toBe(true);
  const edit = await context.newPage();
  await edit.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await edit.goto(`/agents/${id}`);
  await edit.getByRole('region', { name: 'Agent model', exact: true }).getByRole('button', { name: 'Change agent model', exact: true }).click();
  await selectEffort(edit, 'high');
  await edit.getByRole('dialog').getByRole('button', { name: 'Save', exact: true }).click();
  const updated = await get(id);
  expect(updated.model_selection.reasoning_effort).toBe('high');
  expect(updated.model_activity.find((entry: { kind: string }) => entry.kind === 'chat').reasoning_effort).toBe('low');
  await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: chatHold } });
  await expect.poll(() => terminal, { timeout: 45000 }).toContain(`LATE_TIMEOUT_REPLY_${chatHold}`);
  await edit.close();
  const followup = 'Managed conversation test: remember our conversation?';
  await send(followup);
  await expect.poll(() => terminal, { timeout: 45000 }).toContain('Our conversation is retained.');
  const evidence = await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json();
  const workRequests = evidence.model_requests.filter((entry: { tool_names: string[] }) => entry.tool_names.includes('output_publish'));
  expect(workRequests.length).toBeGreaterThan(0);
  expect(workRequests.every((entry: { reasoning: { effort: string } }) => entry.reasoning?.effort === 'high')).toBe(true);
  const chatRequests = evidence.model_requests.filter((entry: { tool_names: string[]; last_user: string }) => !entry.tool_names.length && [opener, heldPrompt, followup].some(text => entry.last_user.endsWith(text)));
  expect(chatRequests.map((entry: { reasoning: { effort: string } }) => entry.reasoning?.effort)).toEqual(['low', 'low', 'high']);
  expect(chatRequests.every((entry: { path: string; model: string }) => entry.path === '/v1/chat/completions' && entry.model === model)).toBe(true);
});


test('reasoning labels open the actual default and agent controls', async ({ page, request }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await page.goto('/agents');
  const defaults = page.getByRole('region', { name: 'Default agent model', exact: true });
  await expect(defaults.getByRole('button', { name: 'Reasoning: Runtime automatic', exact: true })).toBeVisible();
  await defaults.getByRole('button', { name: 'Reasoning: Runtime automatic', exact: true }).click();
  await expect(page.getByRole('dialog')).toContainText('not inherited from the Hermes settings page');
  await choose(page, 'low');
  await expect(defaults.getByRole('button', { name: 'Reasoning: Low', exact: true })).toBeVisible();
  await page.getByLabel('Agent name', { exact: true }).fill('Reasoning controls');
  await page.getByLabel('Purpose', { exact: true }).fill('Inspect configurable reasoning without running a model.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  const settings = page.getByRole('region', { name: 'Agent model', exact: true });
  await settings.getByRole('button', { name: 'Reasoning: Low', exact: true }).click();
  await selectEffort(page, 'high');
  await page.getByRole('dialog').getByRole('button', { name: 'Save', exact: true }).click();
  await expect(settings.getByRole('button', { name: 'Reasoning: High', exact: true })).toBeVisible();
  await page.reload();
  await expect(settings.getByRole('button', { name: 'Reasoning: High', exact: true })).toBeVisible();
  const result = await request.get(`${api}/models/default`, { headers });
  expect((await result.json()).reasoning_effort).toBe('low');
});
