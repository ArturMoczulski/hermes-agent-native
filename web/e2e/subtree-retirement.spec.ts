import { expect, test } from '@playwright/test';

test('a descendant retirement explains and links its parent decision', async ({ page }) => {
  const parentId = '11111111-1111-4111-8111-111111111111';
  const childId = '22222222-2222-4222-8222-222222222222';
  await page.route(`**/api/agent-native/agents/${childId}`, async route => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      id: childId, name: 'Retired specialist', purpose: 'Complete delegated research.',
      soul_revision: 2, execution: 'completed', created_at: '2026-09-08T10:00:00Z',
      parent_id: parentId, child_ids: [], removed_at: null,
      retirement: {
        evaluation_id: 'evaluation-parent', source: 'parent',
        decision_agent_id: parentId, retired_at: '2026-09-08T11:00:00Z',
      },
      startup: null, setup: null, work: null, cadence: null,
      model_selection: null, model_activity: [],
      autonomy: { level: 3, require_owner_review: false },
      progress_concerns: [], progress_concern_settings: { failure_threshold: 3 },
      assignment_review_policies: [], pause: { paused: false, sources: [] },
    }),
  }));

  await page.goto(`/agents/${childId}`);

  await expect(page.getByLabel('Execution status')).toHaveText('Retired');
  const retirement = page.getByRole('region', { name: 'Retirement decision' });
  await expect(retirement).toContainText('retired with its subtree');
  await expect(retirement.getByRole('link', { name: parentId })).toHaveAttribute('href', `/agents/${parentId}`);
  await expect(retirement).toContainText('history and outputs remain available');
});
