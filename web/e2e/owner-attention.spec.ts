import { expect, test } from '@playwright/test';

const agentId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';

const agent = {
  id: agentId,
  name: 'Fantasy builder',
  purpose: 'Build a fantasy game.',
  parent_id: null,
  child_ids: [],
  soul_revision: 1,
  execution: 'completed',
  created_at: '2026-09-11T00:00:00Z',
  removed_at: null,
  retirement: null,
  replacement: null,
  pause: { paused: false, sources: [] },
  autonomy: { level: 3, require_owner_review: false, revision: 1, updated_at: null },
  cadence: { enabled: true, interval_seconds: 60, next_due: null },
  automatic_work: {
    state: 'waiting_owner_answer',
    may_start: false,
    blocker: 'Choose the next design direction.',
    release_condition: 'Answer the agent question.',
    responsible_actor: 'owner',
  },
  progress_concerns: [],
  progress_concern_settings: { failure_threshold: 3 },
  usage: {
    agent: { record_count: 0, api_calls: 0, input_tokens: 0, output_tokens: 0, cache_read_tokens: 0, cache_write_tokens: 0, reasoning_tokens: 0, estimated_cost_usd: null, actual_cost_usd: null, cost_kind: 'unavailable' },
    subtree: { record_count: 0, api_calls: 0, input_tokens: 0, output_tokens: 0, cache_read_tokens: 0, cache_write_tokens: 0, reasoning_tokens: 0, estimated_cost_usd: null, actual_cost_usd: null, cost_kind: 'unavailable' },
  },
  setup: null,
  startup: null,
  work: {
    id: 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
    state: 'completed',
    summary: 'The run recorded its design question and is waiting for an answer.',
    error: null,
    focus: null,
    limits: { timeout_seconds: 900, max_iterations: 50 },
    session_id: 'an_work_test',
    model_calls: 1,
    events: [],
    progress: [],
    outputs: [],
    media_outputs: [],
    stories: [],
    results: [],
    usage: null,
    usage_by_run: {},
    purpose_evaluations: [],
  },
};

test('compact owner attention exposes the exact question and response control', async ({ page }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await page.route(`**/api/agent-native/agents/${agentId}`, route => route.fulfill({ json: agent }));
  let answered = false;
  await page.route(`**/api/agent-native/agents/${agentId}/questions`, route => route.fulfill({ json: answered ? [] : [{
    id: 'question-1', item_id: 'item-1', question: 'Choose the next design direction.', answer: null, applicable: true,
  }] }));
  await page.route(`**/api/agent-native/agents/${agentId}/questions/question-1/answer`, async route => {
    answered = true;
    await route.fulfill({ json: agent });
  });
  await page.goto(`/agents/${agentId}`);

  const attention = page.getByRole('region', { name: 'Needs your answer', exact: true });
  await expect(attention).toContainText('Choose the next design direction.');
  await expect(attention).toContainText('Answer it here or open the affected Plane work item.');
  await expect(attention.getByRole('textbox', { name: 'Your answer' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry failed work', exact: true })).toHaveCount(0);
  await attention.getByRole('textbox', { name: 'Your answer' }).fill('Continue with the hopeful direction.');
  await attention.getByRole('button', { name: 'Send answer', exact: true }).click();
});
