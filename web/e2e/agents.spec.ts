import { test, expect, demoCheckpoint } from './demo-fixture';

const token = 'agent-native-local-e2e-only';
const api = 'http://127.0.0.1:19219/api/agent-native/agents';
const headers = { 'X-Hermes-Session-Token': token };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only';
  });
});

test('creation opens its agent detail and retains one startup request across reloads', async ({ page, request }) => {
  await page.goto('/agents');
  await page.getByLabel('Agent name', { exact: true }).fill('Fantasy writer');
  await page.getByLabel('Purpose', { exact: true }).fill('Develop a fantasy world and write original stories.');
  const responsePromise = page.waitForResponse((response) => response.url().endsWith('/api/agent-native/agents') && response.request().method() === 'POST');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  const agent = await (await responsePromise).json();
  await expect(page).toHaveURL(new RegExp(`/agents/${agent.id}$`));
  await expect(page.getByRole('main').getByRole('heading', { name: 'Fantasy writer', exact: true })).toBeVisible();
  await expect(page.getByLabel('Agent purpose')).toContainText('Develop a fantasy world and write original stories.');
  await expect(page.getByLabel('Startup request')).toContainText('First review requested');
  await expect(page.getByLabel('Execution status')).toContainText('Not started');
  expect(agent.startup.cause).toBe('creation');
  expect(agent.startup.soul_revision).toBe(agent.soul_revision);
  await page.reload();
  await expect(page.getByLabel('Startup request')).toContainText(agent.startup.id);
  await page.getByRole('link', { name: 'All agents', exact: true }).click();
  const row = page.getByRole('article').filter({ hasText: 'Fantasy writer' });
  await expect(row).toHaveCount(1);
  await row.getByRole('link', { name: 'Fantasy writer', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/agents/${agent.id}$`));
  expect((await (await request.get(`${api}/${agent.id}`, { headers })).json()).startup).toEqual(agent.startup);
  await demoCheckpoint(page, test.info(), {
    title: 'One agent, one startup request',
    expected: 'Creation opens the correct agent and reload preserves its purpose and startup identity.',
    proof: 'Fantasy writer appears once in the roster. Its original startup request is unchanged after reload and navigation.',
    focus: page.getByLabel('Startup request'),
  });
});

test('retry after a lost response and reload opens the original agent and startup request', async ({ page, request }) => {
  let first: { id: string; startup: { id: string } } | undefined;
  let loseResponse = true;
  await page.route('**/api/agent-native/agents', async (route) => {
    if (route.request().method() !== 'POST' || !loseResponse) return route.continue();
    loseResponse = false;
    const response = await route.fetch(); // The real backend commits before the reply is lost.
    first = await response.json();
    await route.abort('failed');
  });
  await page.goto('/agents');
  await page.getByLabel('Agent name', { exact: true }).fill('Writer with lost response');
  await page.getByLabel('Purpose', { exact: true }).fill('Write a fantasy adventure.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('Could not confirm creation');
  await page.reload();
  await expect(page.getByLabel('Agent name', { exact: true })).toHaveValue('Writer with lost response');
  await expect(page.getByLabel('Purpose', { exact: true })).toHaveValue('Write a fantasy adventure.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/agents/${first!.id}$`));
  await expect(page.getByLabel('Startup request')).toContainText(first!.startup.id);
  const agents = await (await request.get(api, { headers })).json();
  expect(agents.filter((agent: { name: string }) => agent.name === 'Writer with lost response')).toHaveLength(1);
  await demoCheckpoint(page, test.info(), {
    title: 'Lost creation reply recovered safely',
    expected: 'Retry after reload must reopen the committed agent instead of creating a duplicate.',
    proof: 'Exactly one Writer with lost response exists; the visible startup ID matches the first committed request.',
    focus: page.getByLabel('Startup request'),
  });
});

test('unknown detail shows a recoverable error without inventing an agent', async ({ page }) => {
  await page.goto('/agents/not-a-real-agent');
  await expect(page.getByRole('alert')).toContainText('Could not load this agent');
  await expect(page.getByRole('link', { name: 'All agents', exact: true })).toBeVisible();
  await demoCheckpoint(page, test.info(), {
    title: 'Unknown agent has a recovery path',
    expected: 'An invalid agent address must show an error and a way back to the roster.',
    proof: 'Could not load this agent is visible, with All agents available. No agent was invented.',
    focus: page.getByRole('alert'),
  });
});

test('unauthenticated callers cannot list, create or inspect agents', async ({ page, request }) => {
  const listStatus = (await request.get(api)).status();
  const createStatus = (await request.post(api, { data: { actor: 'owner', name: 'Forged', purpose: 'No', request_id: 'forged' } })).status();
  const inspectStatus = (await request.get(`${api}/missing`)).status();
  expect(listStatus).toBe(401);
  expect(createStatus).toBe(401);
  expect(inspectStatus).toBe(401);
  await demoCheckpoint(page, test.info(), {
    title: 'API evidence: unauthenticated access rejected',
    expected: 'Reading, creating and inspecting agents requires the owner session token.',
    proof: `Actual HTTP responses: list ${listStatus}; forged owner creation ${createStatus}; inspect ${inspectStatus}. All three are Unauthorized.`,
  });
});


test('storage failure prevents an unrecoverable creation write', async ({ page, request }) => {
  await page.goto('/agents');
  await page.getByLabel('Agent name', { exact: true }).fill('Writer without storage');
  await page.getByLabel('Purpose', { exact: true }).fill('Write stories.');
  await page.evaluate(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function (key, value) {
      if (this === window.sessionStorage) throw new DOMException('Storage unavailable', 'QuotaExceededError');
      return original.call(this, key, value);
    };
  });
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  await expect(page.getByRole('alert')).toContainText('nothing was sent');
  const agents = await (await request.get(api, { headers })).json();
  expect(agents.filter((agent: { name: string }) => agent.name === 'Writer without storage')).toHaveLength(0);
  await demoCheckpoint(page, test.info(), {
    title: 'Unsafe creation is stopped before sending',
    expected: 'Unavailable browser storage must prevent an unrecoverable creation request.',
    proof: 'The warning says nothing was sent. An authenticated API read confirms zero Writer without storage agents.',
    focus: page.getByRole('alert'),
  });
});

test('startup prepares private files and explains missing Plane setup without claiming work started', async ({ page, request }) => {
  const response = await request.post(api, { headers, data: {
    request_id: 'writer-setup-required', name: 'Writer awaiting Plane', purpose: 'Write a fantasy story.',
  } });
  const agent = await response.json();
  await page.goto(`/agents/${agent.id}`);
  const setup = page.getByRole('region', { name: 'Agent setup', exact: true });
  await expect(setup).toContainText('Plane setup required');
  await expect(setup).toContainText('Private files ready');
  await expect(page.getByLabel('Execution status')).toContainText('Not started');
  const retried = page.waitForResponse((response) => response.url().endsWith(`/agents/${agent.id}/setup/retry`) && response.request().method() === 'POST');
  await setup.getByRole('button', { name: 'Retry setup', exact: true }).click();
  expect((await retried).ok()).toBeTruthy();
  await expect.poll(async () => (await (await request.get(`${api}/${agent.id}`, { headers })).json()).setup.status).toBe('blocked');
  await expect(setup).toContainText('Plane setup required');
  await page.reload();
  await expect(setup).toContainText('Private files ready');
  const result = await (await request.get(`${api}/${agent.id}`, { headers })).json();
  expect(result.setup.status).toBe('blocked');
  expect(result.setup.activation_id).toBe(agent.startup.id);
  expect(result.setup.project_id).toBeNull();
  expect(JSON.stringify(result)).not.toContain('api_key');
  expect((await request.post(`${api}/${agent.id}/setup/retry`)).status()).toBe(401);
  await demoCheckpoint(page, test.info(), {
    title: 'Missing Plane setup is explained honestly',
    expected: 'Private files can be ready while planning is blocked; retry must not falsely start work.',
    proof: `After retry and reload: setup=${result.setup.status}, project=${result.setup.project_id}. Private files ready and Plane setup required remain visible.`,
    focus: setup,
  });
});

test('configured creation reaches a private planning home with one discovery task and survives reload', async ({ page, request }) => {
  await request.put('http://127.0.0.1:19219/__e2e__/plane-config', { headers, data: { enabled: true } });
  await page.goto('/agents');
  await page.getByLabel('Agent name', { exact: true }).fill('Writer with planning');
  await page.getByLabel('Purpose', { exact: true }).fill('Discover a setting, then write original fantasy stories.');
  await page.getByRole('button', { name: 'Create agent', exact: true }).click();
  const setup = page.getByRole('region', { name: 'Agent setup', exact: true });
  await expect(setup).toContainText('Workspace and planning ready', { timeout: 15000 });
  await expect(setup).toContainText('First discovery task ready');
  await expect(setup.getByRole('link', { name: 'Open planning project' })).toHaveAttribute('href', /\/an-[a-f0-9]{32}\/projects\/[a-f0-9-]+\/issues\/$/);
  await expect(page.getByLabel('Execution status')).toContainText('Not started');
  await page.reload();
  await expect(setup).toContainText('Workspace and planning ready');
  const id = page.url().split('/').pop();
  const current = await (await request.get(`${api}/${id}`, { headers })).json();
  const evidence = await (await request.get(`http://127.0.0.1:19219/__e2e__/plane-evidence/${id}`, { headers })).json();
  expect(evidence).toEqual({ workspace_count: 1, managed_project_count: 1, private: true, discovery_count: 1, discovery_id: current.setup.discovery_item_id });
  await demoCheckpoint(page, test.info(), {
    title: 'A private planning home is ready',
    expected: 'Configured creation provisions one private project and one discovery task, retained after reload.',
    proof: `Verified workspace count ${evidence.workspace_count}, managed projects ${evidence.managed_project_count}, discovery tasks ${evidence.discovery_count}, private=${evidence.private}.`,
    focus: setup,
  });
  await page.route(`**/api/agent-native/agents/${id}`, (route) => route.abort());
  await expect(page.getByRole('alert')).toContainText('Live updates are disconnected');
  await expect(setup).toContainText('Workspace and planning ready');
  await demoCheckpoint(page, test.info(), {
    title: 'Disconnection preserves confirmed setup',
    expected: 'A failed live update must show a warning while retaining the last confirmed setup state.',
    proof: 'Live updates are disconnected is visible; the prepared planning home still shows Workspace and planning ready.',
    focus: page.getByRole('alert'),
  });
});


test('owner removes an agent while retaining its history', async ({ page, request }) => {
  const created = await request.post(api, { headers, data: { request_id: crypto.randomUUID(), name: 'Remove me', purpose: 'A temporary purpose' } });
  const agent = await created.json();
  await page.goto(`/agents/${agent.id}`);
  await page.getByRole('button', { name: 'Remove agent', exact: true }).click();
  await expect(page.getByText('History, saved outputs and Plane records are retained.')).toBeVisible();
  await page.getByRole('button', { name: 'Confirm removal', exact: true }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Agent removed. Autonomous' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Chat with agent', exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole('status').filter({ hasText: 'Agent removed. Autonomous' })).toBeVisible();
  expect((await (await request.get(api, { headers })).json()).some((a: {id: string}) => a.id === agent.id)).toBe(false);
  expect((await request.post(`${api}/${agent.id}/chat`, { headers })).status()).toBe(409);
  expect((await request.delete(`${api}/${agent.id}`, { headers })).status()).toBe(200);
});
