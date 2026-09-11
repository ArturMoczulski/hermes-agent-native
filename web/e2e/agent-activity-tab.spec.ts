/**
 * AN-147: Activity tab rows surface the actual operation detail (file path,
 * argv, exit, bytes), and the compact Work tab no longer duplicates the
 * "Recent activity" section that lives on the dedicated Activity tab.
 *
 * The activity backend now persists a structured ``detail`` JSON payload on
 * every ``work.effect`` event produced by a repository tool. The dashboard
 * renders a Detail column with the path / argv / exit / byte count so an
 * owner sees what the agent actually did, not "Repository operation:
 * repository_command".
 */
import { test, expect } from './demo-fixture';

const token = 'agent-native-local-e2e-only';
const api = 'http://127.0.0.1:19219/api/agent-native/agents';
const headers = { 'X-Hermes-Session-Token': token };

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only';
  });
});

function baseAgent(id: string, soul_revision: number) {
  return {
    parent_id: null,
    child_ids: [],
    removed_at: null,
    retirement: null,
    replacement: null,
    pause: { paused: false, sources: [] },
    cadence: { enabled: false, interval_seconds: null, next_due: null },
    automatic_work: { state: 'automatic_off' as const, may_start: false, blocker: null, release_condition: null, responsible_actor: null },
    usage: { agent: { input_tokens: 0, output_tokens: 0, actual_cost_usd: 0, estimated_cost_usd: 0 },
              subtree: { input_tokens: 0, output_tokens: 0, actual_cost_usd: 0, estimated_cost_usd: 0 } },
    autonomy: { level: 3, require_owner_review: false, revision: soul_revision, updated_at: null },
    model_selection: null,
    model_activity: [],
    progress_concerns: [],
    assignment_review_policies: [],
    startup: null,
    setup: null,
  };
}

test('Activity tab shows structured detail for repository operations', async ({ page, request }) => {
  const created = await (await request.post(api, { headers, data: {
    request_id: crypto.randomUUID(),
    name: 'Activity detail writer',
    purpose: 'Run two repository operations and read the activity detail.',
  } })).json();
  const id = created.id;

  const agent = {
    ...baseAgent(id, created.soul_revision),
    id,
    name: 'Activity detail writer',
    purpose: 'Run two repository operations and read the activity detail.',
    soul_revision: created.soul_revision,
    execution: 'completed',
    created_at: '2026-09-11T10:00:00+00:00',
    project_workspace: { root: '/tmp/fantasy-game', revision: 1, active: true },
    work: {
      id: 'detail-run',
      state: 'completed',
      limits: { timeout_seconds: 180, max_iterations: 50 },
      session_id: 'detail-session',
      model_calls: 4,
      summary: 'Two repository operations completed.',
      error: null,
      stories: [],
      outputs: [],
      results: [],
      progress: [],
      output_sections: [],
      focus: null,
      purpose_evaluations: [],
      events: [
        { id: 1, kind: 'work.model', summary: 'Model step 1', detail: null, created_at: '2026-09-11T10:00:01+00:00' },
        { id: 2, kind: 'work.effect', summary: 'Wrote README.md (28 bytes)',
          detail: { operation: 'repository_file_write', path: 'README.md', bytes: 28,
                    sha256: 'b'.repeat(64), workspace: 'fantasy-game' },
          created_at: '2026-09-11T10:00:02+00:00' },
        { id: 3, kind: 'work.model', summary: 'Model step 2', detail: null, created_at: '2026-09-11T10:00:03+00:00' },
        { id: 4, kind: 'work.effect', summary: 'Ran `rg --files` in fantasy-game (exit 0)',
          detail: { operation: 'repository_command', argv: ['rg', '--files'], command: 'rg --files',
                    exit_code: 0, output_bytes: 142, truncated: false, timed_out: false,
                    workspace: 'fantasy-game' },
          created_at: '2026-09-11T10:00:04+00:00' },
      ],
    },
  };

  await page.route(`**/api/agent-native/agents/${id}`, async (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ status: 200, json: agent });
    return route.fallback();
  });

  await page.goto(`/agents/${id}?view=full&tab=activity`);
  const activity = page.getByRole('region', { name: 'Agent activity', exact: true });

  // The Activity tab now exposes a Detail column header.
  await expect(activity.getByRole('columnheader', { name: 'Detail', exact: true })).toBeVisible();

  // The repository_file_write row surfaces the path / bytes / sha / workspace.
  const writeRow = activity.locator('tbody tr', { hasText: 'Wrote README.md (28 bytes)' });
  await expect(writeRow).toBeVisible();
  await expect(writeRow.getByRole('cell', { name: 'README.md', exact: true })).toBeVisible();
  await expect(writeRow.getByText('28 bytes', { exact: true })).toBeVisible();
  await expect(writeRow.getByText('fantasy-game', { exact: true })).toBeVisible();

  // The repository_command row surfaces the argv as a code block plus the exit code badge.
  const commandRow = activity.locator('tbody tr', { hasText: 'Ran `rg --files` in fantasy-game (exit 0)' });
  await expect(commandRow).toBeVisible();
  await expect(commandRow.locator('code', { hasText: 'rg --files' })).toBeVisible();
  await expect(commandRow.getByText('exit 0', { exact: true })).toBeVisible();
});

test('compact Work tab no longer renders the duplicate Recent activity section', async ({ page, request }) => {
  const created = await (await request.post(api, { headers, data: {
    request_id: crypto.randomUUID(),
    name: 'Compact view',
    purpose: 'Verify the Recent activity panel is gone from the Work tab.',
  } })).json();
  const id = created.id;

  const agent = {
    ...baseAgent(id, created.soul_revision),
    id,
    name: 'Compact view',
    purpose: 'Verify the Recent activity panel is gone from the Work tab.',
    soul_revision: created.soul_revision,
    execution: 'completed',
    created_at: '2026-09-11T10:00:00+00:00',
    work: {
      id: 'compact-run',
      state: 'completed',
      limits: { timeout_seconds: 180, max_iterations: 50 },
      session_id: 'compact-session',
      model_calls: 2,
      summary: 'Two model steps recorded.',
      error: null,
      stories: [],
      outputs: [],
      results: [],
      progress: [],
      output_sections: [],
      focus: null,
      purpose_evaluations: [],
      events: [
        { id: 1, kind: 'work.model', summary: 'Model step 1', detail: null, created_at: '2026-09-11T10:00:01+00:00' },
        { id: 2, kind: 'work.effect', summary: 'Ran `rg --files` in fantasy-game (exit 0)',
          detail: { operation: 'repository_command', argv: ['rg', '--files'], command: 'rg --files',
                    exit_code: 0, output_bytes: 142, truncated: false, timed_out: false,
                    workspace: 'fantasy-game' },
          created_at: '2026-09-11T10:00:02+00:00' },
      ],
    },
  };

  await page.route(`**/api/agent-native/agents/${id}`, async (route) => {
    if (route.request().method() === 'GET') return route.fulfill({ status: 200, json: agent });
    return route.fallback();
  });

  // Default landing: the Work tab in compact view.
  await page.goto(`/agents/${id}`);
  await expect(page.getByRole('region', { name: 'Current work overview' })).toBeVisible();

  // The duplicate "Recent activity" panel is gone — owners go to the Activity tab.
  await expect(page.getByRole('region', { name: 'Recent activity', exact: true })).toHaveCount(0);

  // The Activity tab still works and shows the same event the panel used to show.
  await page.getByRole('link', { name: 'Activity', exact: true }).click();
  const activity = page.getByRole('region', { name: 'Agent activity', exact: true });
  await expect(activity.getByRole('columnheader', { name: 'Detail', exact: true })).toBeVisible();
  await expect(activity.locator('tbody tr', { hasText: 'Ran `rg --files` in fantasy-game (exit 0)' })).toBeVisible();
});
