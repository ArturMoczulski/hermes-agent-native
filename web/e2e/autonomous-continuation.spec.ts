import { expect, test } from '@playwright/test'

const backend = 'http://127.0.0.1:19219'
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' }

test('highly autonomous agent advances to a different ready assignment without owner acceptance', async ({ page, request }) => {
  test.setTimeout(90000)
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
  const created = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Autonomous world builder',
    purpose: 'Continuously develop a coherent fantasy world setting. E2E_AUTONOMOUS_CONTINUATION',
    autonomy_level: 5, work: { timeout_seconds: 180, max_iterations: 12 },
  } })
  expect(created.status()).toBe(201)
  const { id } = await created.json()
  const api = `${backend}/api/agent-native/agents/${id}`
  const current = async () => await (await request.get(api, { headers })).json()
  try {
    await expect.poll(async () => (await current()).work.state, { timeout: 30000 }).toBe('completed')
    const first = (await current()).work
    expect(first.results[0]).toMatchObject({
      outcome: 'submitted', review: { required: false }, acceptance: 'not_evaluated',
    })
    expect(first.outputs).toHaveLength(1)
    expect((await request.post(`${api}/cadence`, { headers, data: {
      expected_revision: 1, enabled: true, interval_seconds: 2,
    } })).ok()).toBe(true)

    await expect.poll(async () => {
      const agent = await current()
      return agent.work.id !== first.id && agent.work.state === 'completed'
    }, { timeout: 30000 }).toBe(true)
    const second = (await current()).work
    expect(second.id).not.toBe(first.id)
    expect(second.session_id).not.toBe(first.session_id)
    expect(second.outputs).toHaveLength(2)
    expect(new Set(second.outputs.map((output: { item_id: string }) => output.item_id)).size).toBe(2)
    expect(second.results.map((result: { review: { required: boolean } }) => result.review.required))
      .toEqual([false, false])

    await page.goto(`/agents/${id}`)
    const direction = page.getByRole('region', { name: 'Current work overview', exact: true })
    await expect(direction.getByRole('heading', { name: 'Current milestone', exact: true })).toBeVisible()
    await expect(direction.getByRole('heading', { name: 'Working on now', exact: true })).toBeVisible()
    await expect(direction.getByRole('heading', { name: 'Up next', exact: true })).toBeVisible()
    await expect(page.getByRole('article', { name: 'Output reader', exact: true })).toBeVisible()
    await page.getByRole('region', { name: 'Recent outputs', exact: true })
      .getByRole('button', { name: 'Read output', exact: true }).first().click()
    await expect(page.getByRole('article', { name: 'Output reader', exact: true })
      .getByRole('region', { name: 'Output review', exact: true })).toHaveCount(0)

    await page.goto(`/agents/${id}?view=full`)
    const outputs = page.getByRole('region', { name: 'Saved outputs', exact: true })
    await expect(outputs).toContainText('Cosmology foundation')
    await expect(outputs).toContainText('Magic-system foundation')
    await outputs.getByRole('button', { name: 'Read output', exact: true }).first().click()
    const review = page.getByRole('region', { name: 'Output review', exact: true })
    await expect(review).toContainText('Review optional')
    await expect(review.getByRole('button', { name: /Accept|revision/i })).toHaveCount(0)
  } finally {
    await request.post(`${api}/work/pause`, { headers })
  }
})

test('explicit owner review blocks highly autonomous cadence until the exact output is accepted', async ({ page, request }) => {
  test.setTimeout(90000)
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: false } })
  const created = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Gated autonomous world builder',
    purpose: 'Continuously develop a coherent fantasy world setting. E2E_AUTONOMOUS_CONTINUATION',
    autonomy_level: 5, work: { timeout_seconds: 180, max_iterations: 12 },
  } })
  expect(created.status()).toBe(201)
  const { id } = await created.json()
  const api = `${backend}/api/agent-native/agents/${id}`
  const current = async () => await (await request.get(api, { headers })).json()
  try {
    const configured = await request.put(`${api}/autonomy`, { headers, data: {
      level: 5, require_owner_review: true, expected_revision: 1,
    } })
    expect(configured.ok()).toBe(true)
    await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })

    await expect.poll(async () => (await current()).work.state, { timeout: 30000 }).toBe('completed')
    const first = (await current()).work
    expect(first.results[0]).toMatchObject({
      outcome: 'submitted', review: { required: true, source: 'owner_policy' },
      acceptance: 'not_evaluated',
    })
    expect((await request.post(`${api}/cadence`, { headers, data: {
      expected_revision: 1, enabled: true, interval_seconds: 2,
    } })).ok()).toBe(true)

    await page.waitForTimeout(4000)
    expect((await current()).work.id).toBe(first.id)
    await page.goto(`/agents/${id}?view=full`)
    await page.getByRole('button', { name: 'Read output', exact: true }).click()
    const reader = page.getByRole('article', { name: 'Output reader', exact: true })
    await expect(reader.getByRole('region', { name: 'Output review', exact: true }))
      .toContainText('Owner approval required')
    await reader.getByRole('button', { name: 'Accept output', exact: true }).click()
    await expect(reader).toContainText('Accepted this exact output version.')

    await expect.poll(async () => {
      const agent = await current()
      return agent.work.id !== first.id && agent.work.state === 'completed'
    }, { timeout: 30000 }).toBe(true)
    const continued = (await current()).work
    expect(continued.id).not.toBe(first.id)
    expect(continued.outputs).toHaveLength(2)
  } finally {
    await request.post(`${api}/work/pause`, { headers })
  }
})
