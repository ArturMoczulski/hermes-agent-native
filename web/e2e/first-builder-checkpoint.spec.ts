import { test, expect } from './demo-fixture';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
});

test('prepares the First Builder but leaves launch held for the final test', async ({ page }) => {
  const agent = { id: 'builder-id', name: 'First Builder', purpose: 'Build agent-native.', soul_revision: 1,
    execution: 'not_started', created_at: '2026-09-09T08:00:00Z', parent_id: null, child_ids: [], startup: null,
    setup: null, work: { state: 'queued' }, cadence: null, pause: { paused: false }, retirement: null,
    removed_at: null, model_selection: { provider: 'openai-codex', model: 'gpt-5.6-sol', reasoning_effort: 'low', revision: 1, source: 'override', updated_at: '2026-09-09T08:00:00Z' },
    model_activity: [], autonomy: { level: 3, revision: 1, require_owner_review: false }, progress_concerns: [], assignment_review_policies: [] };
  let prepared = false;
  await page.route('**/api/agent-native/first-builder', route => route.fulfill({ status: prepared ? 200 : 404, contentType: 'application/json',
    body: prepared ? JSON.stringify({ registration: { agent_id: agent.id, launch_state: 'held_for_owner_test' }, agent }) : JSON.stringify({ detail: 'not prepared' }) }));
  await page.route('**/api/agent-native/first-builder/prepare', route => { prepared = true; return route.fulfill({ status: 201, contentType: 'application/json',
    body: JSON.stringify({ registration: { agent_id: agent.id, launch_state: 'held_for_owner_test' }, agent }) }); });
  await page.goto('/agents');
  const checkpoint = page.getByLabel('First Builder launch checkpoint');
  await checkpoint.getByRole('button', { name: 'Prepare First Builder' }).click();
  await expect(checkpoint).toContainText('Waiting for final test');
  await expect(checkpoint).toContainText('OpenAI GPT-5.6 Sol · Low reasoning');
  await expect(checkpoint).toContainText('It cannot start until the final ordinary test-agent evidence is recorded.');
  await expect(checkpoint.getByRole('button', { name: /launch/i })).toHaveCount(0);
});
