import { expect, test } from '@playwright/test';

const agentId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';

const agent = {
  id: agentId,
  name: 'Failed fantasy builder',
  purpose: 'Build a fantasy game.',
  parent_id: null,
  child_ids: [],
  soul_revision: 1,
  execution: 'failed',
  created_at: '2026-09-11T00:00:00Z',
  removed_at: null,
  retirement: null,
  replacement: null,
  pause: { paused: false, sources: [] },
  autonomy: { level: 3, require_owner_review: false, revision: 1, updated_at: null },
  cadence: { enabled: true, interval_seconds: 60, next_due: null },
  automatic_work: {
    state: 'owner_attention',
    may_start: false,
    blocker: 'The latest attempt failed.',
    release_condition: 'Review the failure and retry the work.',
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
    state: 'failed',
    summary: 'The run ended without a recorded result. Saved outputs remain available.',
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

test('compact owner attention explains a failed attempt and exposes recovery', async ({ page }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'; });
  await page.route(`**/api/agent-native/agents/${agentId}`, route => route.fulfill({ json: agent }));
  await page.route(`**/api/agent-native/agents/${agentId}/questions`, route => route.fulfill({ json: [] }));
  await page.goto(`/agents/${agentId}`);

  const attention = page.getByRole('region', { name: 'Needs your attention', exact: true });
  await expect(attention).toContainText('The latest attempt failed.');
  await expect(attention).toContainText('The run ended without a recorded result. Saved outputs remain available.');
  await expect(attention).toContainText('Review the failure and retry the work.');
  await expect(attention.getByRole('link', { name: 'Open activity and diagnostics', exact: true })).toBeVisible();

  await page.route(`**/api/agent-native/agents/${agentId}/work/retry`, route => route.fulfill({ json: { recovery_run_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc', agent } }));
  await attention.getByRole('button', { name: 'Retry failed work', exact: true }).click();
  await expect(attention.getByRole('status')).toContainText('Recovery requested');
});
