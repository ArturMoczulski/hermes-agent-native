import { type APIRequestContext } from '@playwright/test'
import { expect, test, demoCheckpoint } from './demo-fixture'

const backend = 'http://127.0.0.1:19219'
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' }
const api = (id: string) => `${backend}/api/agent-native/agents/${id}`

async function create(request: APIRequestContext, name: string, marker = '') {
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
  const response = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name, purpose: `Write original fantasy stories. ${marker}`,
    ...(marker ? { work: { timeout_seconds: 300, max_iterations: 20 } } : {}),
  } })
  expect(response.status()).toBe(201)
  const agent = await response.json()
  await expect.poll(async () => (await (await request.get(api(agent.id), { headers })).json()).setup?.status,
    { timeout: 30000 }).toBe('ready')
  return agent.id as string
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
})

test('planning does not present a discovery task as the selected current work', async ({ page, request }) => {
  const id = await create(request, 'Planning without selection')
  await page.goto(`/agents/${id}`)
  const planning = page.getByRole('region', { name: 'Work planning', exact: true })
  await expect(planning).toBeVisible()
  await expect(planning).toContainText('No work item selected')
  await expect(planning).toContainText('Initial review pending')
  await expect(planning.getByRole('heading', { name: 'Current work item', exact: true })).toHaveCount(0)
  await expect(planning.getByRole('link', { name: 'Open project in Plane', exact: true })).toHaveAttribute('href', /\/projects\/[^/]+\/issues\/$/)
  await expect(page.getByLabel('Execution status')).toHaveText('Not started')
  await demoCheckpoint(page, test.info(), {
    title: 'A backlog task is not an active assignment',
    expected: 'A prepared project must not invent current work before the agent explicitly selects an item.',
    proof: 'No work item selected and Initial review pending are visible. Execution is Not started, with a real Plane project link.',
    focus: planning,
  })
})

async function control(request: APIRequestContext, id: string, data: Record<string, unknown>) {
  const response = await request.patch(`${backend}/__e2e__/planning-control/${id}`, { headers, data })
  expect(response.ok()).toBe(true)
  return response.json()
}

async function heldWriter(request: APIRequestContext, marker: string) {
  const id = await create(request, `Planning ${marker}`, marker)
  await expect.poll(async () => {
    const current = await (await request.get(api(id), { headers })).json()
    if (['completed', 'failed', 'unknown', 'paused'].includes(current.work.state)) throw new Error(JSON.stringify(current.work))
    const response = await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers })
    return response.ok() ? (await response.json()).entered : false
  }, { timeout: 30000 }).toBe(true)
  const agent = await (await request.get(api(id), { headers })).json()
  expect(agent.work.focus.item_id).toBeTruthy()
  return agent
}

async function stop(request: APIRequestContext, id: string, marker: string) {
  await request.post(`${api(id)}/work/pause`, { headers })
  await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker } })
}

test('selected work shows brief, cycle and criteria; explicit refresh reveals changed criteria and stale outages', async ({ page, request }) => {
  test.setTimeout(90000)
  const marker = 'E2E_PLAN_HOLD_DETAILS'
  const agent = await heldWriter(request, marker)
  const id = agent.id
  try {
    await page.goto(`/agents/${id}`)
    const planning = page.getByRole('region', { name: 'Work planning', exact: true })
    await expect(planning.getByRole('heading', { name: 'Current work item', exact: true })).toBeVisible()
    await expect(planning).toContainText('Write The Silver Gate')
    await expect(planning).toContainText('Write an original, complete fantasy story')
    await expect(planning).toContainText('First complete fantasy story')
    await expect(planning).toContainText('identifiable protagonist')
    await expect(planning.getByRole('link', { name: 'Open selected work item in Plane' })).toHaveAttribute('href', new RegExp(`/issues/${agent.work.focus.item_id}/$`))
    await expect(planning.getByRole('link', { name: 'Open cycle in Plane' })).toHaveAttribute('href', new RegExp(`/cycles/${agent.work.focus.cycle_id}/$`))
    const checked = planning.getByLabel('Planning checked time')
    const initialCheck = await checked.getAttribute('datetime')
    await demoCheckpoint(page, test.info(), {
      title: 'Current work connects purpose, plan and requirements',
      expected: 'The running agent exposes its explicitly selected task, cycle and acceptance criteria.',
      proof: 'Write The Silver Gate is current work; First complete fantasy story is its cycle at selection, with an identifiable protagonist required. Both links identify the selected records.',
      focus: planning.getByRole('heading', { name: 'Current work item', exact: true }),
    })
    await control(request, id, { item_id: agent.work.focus.item_id,
      description_html: '<p>Acceptance criteria: include a named cartographer.</p><script>window.planningScriptRan = true</script><img src="/untrusted-planning-image" onerror="window.planningScriptRan = true"><a href="javascript:alert(1)">Unsafe link text</a>' })
    let imageRequests = 0
    page.on('request', (req) => { if (req.url().includes('untrusted-planning-image')) imageRequests += 1 })
    await planning.getByRole('button', { name: 'Refresh planning', exact: true }).click()
    await expect(planning).toContainText('Requirements differ from the last Plane check.')
    await expect(planning).toContainText('include a named cartographer')
    await expect(planning).toContainText('identifiable protagonist')
    await expect(checked).not.toHaveAttribute('datetime', initialCheck!)
    expect(await page.evaluate(() => Object.hasOwn(window, 'planningScriptRan'))).toBe(false)
    expect(imageRequests).toBe(0)
    const originalViewport = page.viewportSize()
    await page.setViewportSize({ width: 1280, height: 1500 })
    await planning.screenshot({ path: test.info().outputPath('planning-work.png') })
    if (originalViewport) await page.setViewportSize(originalViewport)
    await expect(planning.locator('img, script, a[href^="javascript:"]')).toHaveCount(0)
    await demoCheckpoint(page, test.info(), {
      title: 'Refreshed criteria stay distinct from the selection snapshot',
      expected: 'Refresh must reveal changed Plane requirements while preserving what was selected earlier.',
      proof: 'Named cartographer is in the refreshed details; identifiable protagonist remains in the selection snapshot. The checked time advanced, with zero injected image requests or script elements.',
      focus: planning.getByText('Requirements differ from the last Plane check.', { exact: true }),
    })
    const goodCheck = await checked.getAttribute('datetime')
    const before = await control(request, id, { outage: true })
    await planning.getByRole('button', { name: 'Refresh planning', exact: true }).click()
    await expect(planning.getByRole('alert')).toContainText('Showing stale planning data')
    await expect(checked).toHaveAttribute('datetime', goodCheck!)
    await expect(planning).toContainText('include a named cartographer')
    const after = await control(request, id, {})
    expect(after.project_gets).toBeGreaterThan(before.project_gets)
    // Local agent polling must not repeatedly request the external planning snapshot.
    let localReads = 0
    page.on('response', (r) => { if (new URL(r.url()).pathname === `/api/agent-native/agents/${id}` && r.request().method() === 'GET') localReads += 1 })
    await expect.poll(() => localReads, { timeout: 15000 }).toBeGreaterThanOrEqual(3)
    expect((await control(request, id, {})).project_gets).toBe(after.project_gets)
    await demoCheckpoint(page, test.info(), {
      title: 'A planning outage is visible without losing evidence',
      expected: 'An unavailable Plane server must keep the last confirmed snapshot and timestamp, labeled stale.',
      proof: 'Showing stale planning data is visible and the last checked time is unchanged. Three further local status polls made no extra Plane project reads.',
      focus: planning.getByRole('alert'),
    })
    await control(request, id, { outage: false })
    await page.getByRole('button', { name: 'Pause', exact: true }).click()
    await expect(page.getByLabel('Execution status')).toHaveText('Paused')
    await expect(planning.getByRole('heading', { name: 'Last selected work item', exact: true })).toBeVisible()
    await expect(planning.getByRole('heading', { name: 'Current work item', exact: true })).toHaveCount(0)
    await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers })).json()).client_disconnected).toBe(true)
    const proof = await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json()
    expect(proof.worker_alive).toBe(false)
    await demoCheckpoint(page, test.info(), {
      title: 'Paused work becomes the last selection',
      expected: 'After the worker stops, the task must be labeled Last selected work item rather than current work.',
      proof: `The screen shows Paused and Last selected work item; no Current work item heading remains. worker_alive=${proof.worker_alive}.`,
      focus: planning.getByRole('heading', { name: 'Last selected work item', exact: true }),
    })
  } finally { await control(request, id, { outage: false }); await stop(request, id, marker) }
})

test('a missing selected item retains its selection and switching agents discards a delayed planning response', async ({ page, request }) => {
  test.setTimeout(90000)
  const marker = 'E2E_PLAN_HOLD_MISSING'
  const agent = await heldWriter(request, marker)
  const id = agent.id
  const otherId = await create(request, 'Separate planning scope')
  try {
    await page.goto(`/agents/${id}`)
    const planning = page.getByRole('region', { name: 'Work planning', exact: true })
    await expect(planning).toContainText('Write The Silver Gate')
    await control(request, id, { item_id: agent.work.focus.item_id, delete_item: true })
    await planning.getByRole('button', { name: 'Refresh planning', exact: true }).click()
    await expect(planning).toContainText('The selected work item is missing')
    await expect(planning).toContainText('identifiable protagonist')
    await demoCheckpoint(page, test.info(), {
      title: 'Deleted planning items keep their original selection evidence',
      expected: 'A missing Plane item must be reported without erasing the requirements captured at selection.',
      proof: 'The selected work item is missing is visible; the original identifiable protagonist requirement remains readable.',
      focus: planning.getByText('The selected work item is missing', { exact: false }),
    })
    await control(request, id, { hold: true })
    await planning.getByRole('button', { name: 'Refresh planning', exact: true }).click()
    await expect.poll(async () => (await control(request, id, {})).hold_entered).toBe(true)
    await page.getByRole('link', { name: 'All agents', exact: true }).click()
    await page.getByRole('link', { name: 'Separate planning scope', exact: true }).click()
    await expect(page).toHaveURL(new RegExp(`/agents/${otherId}$`))
    await expect(planning).toContainText('No work item selected')
    await control(request, id, { release: true })
    await expect(planning).not.toContainText('Write The Silver Gate')
    await expect(planning.getByRole('link', { name: 'Open project in Plane', exact: true })).toHaveAttribute('href', new RegExp(`an-${otherId.replaceAll('-', '')}`))
    await demoCheckpoint(page, test.info(), {
      title: 'Switching agents discards the previous planning response',
      expected: 'A delayed response for one agent must never appear in another agent’s Work view.',
      proof: 'Separate planning scope has No work item selected and its own project link. The released response did not insert Write The Silver Gate.',
      focus: planning,
    })
  } finally { await control(request, id, { release: true }); await stop(request, id, marker) }
})

test('a new selection cannot compare its requirements with a planning check from the older selection', async ({ page, request }) => {
  test.setTimeout(90000)
  const marker = 'E2E_PLAN_RESELECT'
  const id = await create(request, 'Reselected planning requirements', marker)
  const hold = async (suffix: string) => {
    const response = await request.get(`${backend}/__e2e__/model-holds/${marker}_${suffix}`, { headers })
    return response.ok() ? (await response.json()).entered : false
  }
  try {
    await expect.poll(() => hold('BEFORE'), { timeout: 30000 }).toBe(true)
    const original = await (await request.get(api(id), { headers })).json()
    await page.goto(`/agents/${id}`)
    const planning = page.getByRole('region', { name: 'Work planning', exact: true })
    await expect(planning.getByLabel('Planning checked time')).toBeVisible()
    const checked = await planning.getByLabel('Planning checked time').getAttribute('datetime')
    await control(request, id, { item_id: original.work.focus.item_id,
      description_html: '<p>Acceptance criteria: show the cartographer resolving the dispute.</p>', outage: true })
    await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: `${marker}_BEFORE` } })
    await expect.poll(() => hold('AFTER'), { timeout: 30000 }).toBe(true)
    const selected = await (await request.get(api(id), { headers })).json()
    expect(selected.work.focus.selection_id).not.toBe(original.work.focus.selection_id)
    await expect(planning).toContainText('show the cartographer resolving the dispute')
    await expect(planning.getByRole('alert')).toContainText('Showing stale planning data')
    await expect(planning).not.toContainText('The work item changed in Plane after selection.')
    await expect(planning).not.toContainText('Latest requirements in Plane')
    await expect(planning).toContainText('This planning check belongs to an earlier work selection.')
    await expect(planning.getByLabel('Planning checked time')).toHaveAttribute('datetime', checked!)
    await demoCheckpoint(page, test.info(), {
      title: 'Reselection does not mislabel old planning data as current',
      expected: 'New selection requirements must stay distinct from a cached check belonging to the old selection.',
      proof: 'The new selection requires the cartographer resolving the dispute. The old check is explicitly labeled as belonging to an earlier work selection, with its timestamp unchanged.',
      focus: planning.getByRole('status').filter({ hasText: 'This planning check belongs to an earlier work selection.' }),
    })
    await control(request, id, { outage: false })
    await planning.getByRole('button', { name: 'Refresh planning', exact: true }).click()
    await expect(planning).not.toContainText('This planning check belongs to an earlier work selection.')
    await expect(planning).not.toContainText('Requirements differ from the last Plane check')
    await demoCheckpoint(page, test.info(), {
      title: 'A successful refresh reconciles the new selection',
      expected: 'Once Plane recovers, refresh should align the displayed planning check with the new selection.',
      proof: 'The obsolete earlier-selection warning and difference warning are gone; the new cartographer requirement remains in the Work view.',
      focus: planning,
    })
  } finally {
    await control(request, id, { outage: false })
    await request.post(`${api(id)}/work/pause`, { headers })
    for (const suffix of ['BEFORE', 'AFTER']) {
      await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: `${marker}_${suffix}` } })
    }
  }
})
