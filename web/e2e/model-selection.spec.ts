import { test, expect, type Page, type APIRequestContext } from './fixtures';

const backend = 'http://127.0.0.1:19219';
const api = `${backend}/api/agent-native`;
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };
const primary = { provider: 'custom:browser-fixture', model: 'native-browser-fixture' };
const alternate = { provider: 'custom:browser-alternate', model: 'native-browser-fixture-small' };

async function pick(page: Page, provider: string, model: string, action = 'Save') {
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByText('Persist globally (otherwise this session only)')).toHaveCount(0);
  await dialog.getByText(provider.replace('custom:', ''), { exact: true }).click();
  await dialog.getByText(model, { exact: true }).click();
  await dialog.getByRole('button', { name: action, exact: true }).click();
  await expect(dialog).toHaveCount(0);
}

async function getAgent(request: APIRequestContext, id: string) {
  return (await request.get(`${api}/agents/${id}`, { headers })).json();
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
});

test('owner configures a new-agent default and independent agent choices with retained retry input', async ({ page, request }) => {
  await page.goto('/agents');
  const defaults = page.getByRole('region', { name: 'Default agent model', exact: true });
  await defaults.getByRole('button', { name: 'Change default model', exact: true }).click();
  await pick(page, primary.provider, primary.model);
  await expect(defaults).toContainText(primary.model);
  await page.getByLabel('Agent name', { exact: true }).fill('Default-model agent');
  await page.getByLabel('Purpose', { exact: true }).fill('Use the default selected at creation.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Agent model', exact: true })).toContainText(primary.model);
  const defaultId = page.url().split('/').at(-1)!;
  expect((await getAgent(request, defaultId)).model_selection).toMatchObject({ ...primary, source: 'default' });
  await page.getByRole('link', { name: 'All agents', exact: true }).click();
  await defaults.getByRole('button', { name: 'Change default model', exact: true }).click();
  await pick(page, alternate.provider, alternate.model);
  expect((await getAgent(request, defaultId)).model_selection).toMatchObject(primary);
  await page.reload();
  await expect(defaults).toContainText(alternate.model);
  await page.getByLabel('Agent name', { exact: true }).fill('New-default agent');
  await page.getByLabel('Purpose', { exact: true }).fill('Use the latest default without changing older agents.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Agent model', exact: true })).toContainText(alternate.model);
  const newDefaultId = page.url().split('/').at(-1)!;
  expect((await getAgent(request, newDefaultId)).model_selection).toMatchObject({ ...alternate, source: 'default' });
  await page.getByRole('link', { name: 'All agents', exact: true }).click();

  let first: { id: string } | undefined;
  let loseResponse = true;
  await page.route('**/api/agent-native/agents', async route => {
    if (route.request().method() !== 'POST' || !loseResponse) return route.continue();
    loseResponse = false;
    first = await (await route.fetch()).json();
    await route.abort('failed');
  });
  await page.getByLabel('Agent name', { exact: true }).fill('Explicit-model agent');
  await page.getByLabel('Purpose', { exact: true }).fill('Retain the chosen model after a lost reply.');
  await page.getByRole('button', { name: 'Choose a different model', exact: true }).click();
  await pick(page, primary.provider, primary.model, 'Use model');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Could not confirm creation');
  await page.reload();
  await expect(page.getByRole('group', { name: 'Model for this agent', exact: true })).toContainText(primary.model);
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/agents/${first!.id}$`));
  const model = page.getByRole('region', { name: 'Agent model', exact: true });
  await expect(model).toContainText(primary.model);
  expect((await getAgent(request, first!.id)).model_selection).toMatchObject({ ...primary, source: 'override' });
  await model.getByRole('button', { name: 'Change agent model', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
  expect((await getAgent(request, first!.id)).model_selection).toMatchObject(primary);
  await model.getByRole('button', { name: 'Change agent model', exact: true }).click();
  await pick(page, alternate.provider, alternate.model);
  await expect(model).toContainText('Applies to the next work run or chat message');
  await page.reload();
  await expect(model).toContainText(alternate.model);
  expect((await getAgent(request, defaultId)).model_selection).toMatchObject(primary);
  const all = await (await request.get(`${api}/agents`, { headers })).json();
  expect(all.filter((agent: { name: string }) => agent.name === 'Explicit-model agent')).toHaveLength(1);
});

test('owner changes future models without rewriting active work or chat and actual requests follow each choice', async ({ page, request, context }) => {
  test.setTimeout(180000);
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } });
  const marker = `E2E_WRITER_HOLD_MODELS_${Date.now()}`;
  const purpose = `Write original stories about the moonlit citadel. ${marker}`;
  const response = await request.post(`${api}/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Independently routed writer', purpose,
    model_selection: primary, work: { timeout_seconds: 300, max_iterations: 20 },
  } });
  expect(response.status()).toBe(201);
  const agent = await response.json();
  await page.goto(`/agents/${agent.id}`);
  const work = page.getByRole('region', { name: 'Agent work', exact: true });
  await expect(page.getByLabel('Execution status')).toHaveText('Running', { timeout: 45000 });
  await expect.poll(async () => {
    const hold = await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers });
    return hold.ok() && (await hold.json()).entered;
  }, { timeout: 45000 }).toBe(true);
  await expect(work).toContainText(`${primary.provider} · ${primary.model}`);
  const settings = page.getByRole('region', { name: 'Agent model', exact: true });
  await settings.getByRole('button', { name: 'Change agent model', exact: true }).click();
  await pick(page, alternate.provider, alternate.model);
  await expect(settings).toContainText(`${alternate.provider} · ${alternate.model}`);
  await expect(work).toContainText(`${primary.provider} · ${primary.model}`);
  let current = await getAgent(request, agent.id);
  expect(current.model_selection).toMatchObject(alternate);
  expect(current.work.model_selection).toMatchObject(primary);
  const workEvidence = await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json();
  const workRequests = workEvidence.model_requests.filter((r: { tool_names: string[] }) => r.tool_names.includes('output_publish'));
  expect(workRequests.length).toBeGreaterThan(0);
  expect(workRequests.every((r: { path: string; model: string }) => r.path === '/v1/chat/completions' && r.model === primary.model)).toBe(true);
  await work.getByRole('button', { name: 'Pause', exact: true }).click();
  await expect(page.getByLabel('Execution status')).toHaveText('Paused', { timeout: 30000 });

  let terminalOutput = '';
  page.on('websocket', socket => {
    if (new URL(socket.url()).pathname === '/api/pty') socket.on('framereceived', ({ payload }) => {
      terminalOutput += typeof payload === 'string' ? payload : payload.toString('utf8');
    });
  });
  await page.getByRole('link', { name: 'Chat with agent', exact: true }).click();
  await expect(page.getByLabel('Conversation agent')).toContainText(alternate.model);
  await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json()).managed_ready_ids,
    { timeout: 45000 }).toContain(agent.id);
  let messagesSent = 0;
  const send = async (text: string) => {
    const attach = await page.evaluate(() => window.localStorage.getItem('hermes.pty.token.chat'));
    const composer = async () => (await (await request.get(`${backend}/__e2e__/managed-delivery/${agent.id}?attach_token=${attach}`, { headers })).json()).composer;
    // A fresh renderer has no composer snapshot until its first input. Once
    // submitted, streamed text precedes receipt completion: later messages must
    // wait for the existing snapshot to show a settled receipt explicitly.
    if (messagesSent > 0) {
      await expect.poll(async () => (await composer())?.pending, { timeout: 30000 }).toBeNull();
    }
    await page.locator('.xterm-helper-textarea').focus();
    await page.keyboard.type(text);
    await expect.poll(async () => (await composer())?.draft?.input).toBe(text);
    await page.keyboard.press('Enter');
    messagesSent += 1;
  };
  const opener = 'Managed conversation test: what is your purpose?';
  await send(opener);
  await expect.poll(() => terminalOutput, { timeout: 45000 }).toContain('My purpose: Write original stories about the moonlit citadel.');
  const holdMarker = `MODEL_SELECTION_CHAT_${Date.now()}`;
  await request.post(`${backend}/__e2e__/hold-model`, { headers, data: { marker: holdMarker } });
  await send(`Wait for owner model selection ${holdMarker}`);
  await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/model-holds/${holdMarker}`, { headers })).json()).entered, { timeout: 45000 }).toBe(true);
  const edit = await context.newPage();
  await edit.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await edit.goto(`/agents/${agent.id}`);
  await edit.getByRole('region', { name: 'Agent model', exact: true }).getByRole('button', { name: 'Change agent model', exact: true }).click();
  await pick(edit, primary.provider, primary.model);
  current = await getAgent(request, agent.id);
  expect(current.model_selection).toMatchObject(primary);
  expect(current.model_activity.find((entry: { kind: string }) => entry.kind === 'chat')).toMatchObject(alternate);
  await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: holdMarker } });
  await expect.poll(() => terminalOutput, { timeout: 45000 }).toContain(`LATE_TIMEOUT_REPLY_${holdMarker}`);
  await edit.close();
  const followup = 'Managed conversation test: remember our conversation?';
  await send(followup);
  await expect.poll(() => terminalOutput, { timeout: 45000 }).toContain('Our conversation is retained.');
  const evidence = await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json();
  const chatRequests = evidence.model_requests.filter((r: { last_user: string; tool_names: string[] }) => !r.tool_names.length && [opener, `Wait for owner model selection ${holdMarker}`, followup].some(text => r.last_user.endsWith(text)));
  expect(chatRequests.map((r: { path: string; model: string }) => ({ path: r.path, model: r.model }))).toEqual([
    { path: '/alternate/v1/chat/completions', model: alternate.model },
    { path: '/alternate/v1/chat/completions', model: alternate.model },
    { path: '/v1/chat/completions', model: primary.model },
  ]);
  current = await getAgent(request, agent.id);
  expect(current.model_activity.find((entry: { kind: string }) => entry.kind === 'chat')).toMatchObject(primary);
  expect(current.work.model_selection).toMatchObject(primary);
});

test('unknown default prevents accidental creation until an explicit configured model is chosen', async ({ page, request }) => {
  let creates = 0;
  page.on('request', (event) => {
    if (event.method() === 'POST' && new URL(event.url()).pathname === '/api/agent-native/agents') creates += 1;
  });
  await page.route('**/api/agent-native/models/default', (route) => route.abort('failed'));
  await page.goto('/agents');
  await page.getByLabel('Agent name', { exact: true }).fill('Explicit model during default outage');
  await page.getByLabel('Purpose', { exact: true }).fill('Keep model choice explicit when the default cannot be checked.');
  await expect(page.getByRole('region', { name: 'Default agent model', exact: true })).toContainText('Could not load the default model');
  await expect(page.getByRole('button', { name: 'Create agent', exact: true })).toBeDisabled();
  expect(creates).toBe(0);
  await page.getByRole('button', { name: 'Choose a different model', exact: true }).click();
  await pick(page, alternate.provider, alternate.model, 'Use model');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('region', { name: 'Agent model', exact: true })).toContainText(alternate.model);
  const id = page.url().split('/').at(-1)!;
  expect((await getAgent(request, id)).model_selection).toMatchObject({ ...alternate, source: 'override' });
  expect(creates).toBe(1);
});
