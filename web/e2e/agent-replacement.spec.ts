import { expect, test } from '@playwright/test';

const backend = 'http://127.0.0.1:19219';
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' };

test('owner replaces an agent and sees the successor handoff', async ({ page, request }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: false } });
  const predecessorResponse = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Original strategist',
    purpose: 'Develop the ongoing strategy.', work: { timeout_seconds: 180, max_iterations: 50 },
  } });
  expect(predecessorResponse.ok()).toBeTruthy();
  const predecessor = await predecessorResponse.json();
  const childResponse = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Original researcher', parent_id: predecessor.id,
    purpose: 'Research for the original strategy.', work: { timeout_seconds: 180, max_iterations: 50 },
  } });
  expect(childResponse.ok()).toBeTruthy();
  const child = await childResponse.json();

  await page.goto(`/agents/${predecessor.id}?view=full`);
  await page.getByRole('button', { name: 'Replace agent', exact: true }).click();
  const form = page.getByRole('form', { name: 'Replace agent' });
  await form.getByLabel('Successor name').fill('Strategy lead v2');
  await form.getByLabel('Successor purpose').fill('Lead the ongoing strategy with a clean operating context.');
  await form.getByLabel('Reason for replacement').fill('The owner selected a new operating approach.');
  await form.getByLabel('Selected handoff').fill('Review the retained strategy brief and continue the open market analysis.');
  await form.getByRole('button', { name: 'Create successor and retire old subtree' }).click();

  await expect(page).toHaveURL(/\/agents\/[0-9a-f-]+$/);
  const successorId = page.url().split('/').pop()!;
  expect(successorId).not.toBe(predecessor.id);
  const handoff = page.getByRole('region', { name: 'Replacement handoff' });
  await expect(handoff).toContainText('clean agent identity');
  await expect(handoff.getByRole('link', { name: predecessor.id })).toHaveAttribute('href', `/agents/${predecessor.id}`);
  await expect(handoff).toContainText('The owner selected a new operating approach.');
  await expect(handoff).toContainText('Review the retained strategy brief and continue the open market analysis.');

  const oldState = await (await request.get(`${backend}/api/agent-native/agents/${predecessor.id}`, { headers })).json();
  const childState = await (await request.get(`${backend}/api/agent-native/agents/${child.id}`, { headers })).json();
  expect(oldState.retirement).toMatchObject({ source: 'owner', replacement_id: oldState.replacement.id });
  expect(childState.retirement).toMatchObject({ source: 'parent', replacement_id: oldState.replacement.id });
});
