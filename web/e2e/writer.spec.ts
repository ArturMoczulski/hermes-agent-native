import { expect, test, demoCheckpoint } from './demo-fixture'

const backend = 'http://127.0.0.1:19219'
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' }

test('creation retains explicit work limits and waits for the real planning setup before running', async ({ page, request }) => {
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: false } })
  await page.goto('/agents')
  await page.getByLabel('Agent name', { exact: true }).fill('First working citadel writer')
  await page.getByLabel('Purpose', { exact: true }).fill('Develop an original fantasy setting and write stories about the moonlit citadel.')
  await page.getByLabel('Maximum run time (seconds)', { exact: true }).fill('300')
  await page.getByLabel('Maximum model steps', { exact: true }).fill('20')
  await page.getByRole('button', { name: 'Create agent', exact: true }).click()
  await expect(page.getByRole('main').getByRole('heading', { name: 'First working citadel writer', exact: true })).toBeVisible()
  await expect(page.getByLabel('Execution status')).toHaveText('Waiting for setup')
  const id = page.url().split('/').at(-1)
  const get = async () => (await (await request.get(`${backend}/api/agent-native/agents/${id}`, { headers })).json())
  const before = await get()
  expect(before.work).toMatchObject({ state: 'queued', limits: { timeout_seconds: 300, max_iterations: 20 } })
  expect(before.work.session_id).toBeTruthy()
  await page.reload()
  await expect(page.getByLabel('Execution status')).toHaveText('Waiting for setup')
  expect((await get()).work.id).toBe(before.work.id)
  expect((await get()).work.model_calls).toBe(0)
  await demoCheckpoint(page, test.info(), {
    title: 'Work waits for its planning setup',
    expected: 'The explicit 300-second / 20-step limits survive reload and no model call starts before setup.',
    proof: 'Waiting for setup remains visible; the same queued run has model_calls=0 and the requested limits.',
    focus: page.getByRole('region', { name: 'Agent work', exact: true }),
  })
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  await expect(page.getByLabel('Execution status')).toHaveText('Paused')
  expect((await get()).work.state).toBe('paused')
  await demoCheckpoint(page, test.info(), {
    title: 'Queued work can be paused',
    expected: 'The owner can stop waiting work before execution begins.',
    proof: 'The execution status is Paused and the persisted run state is paused.',
    focus: page.getByRole('region', { name: 'Agent work', exact: true }),
  })
})


test('a writer purpose uses shared output and result records without a chat prompt', async ({ page, request }) => {
  test.setTimeout(90000)
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
  await page.goto('/agents')
  await page.getByLabel('Agent name', { exact: true }).fill('Working glass dragon writer')
  await page.getByLabel('Purpose', { exact: true }).fill('Write original fantasy stories about a glass dragon and a moonlit citadel.')
  await page.getByLabel('Autonomy', { exact: true }).selectOption('1')
  await page.getByText('Advanced work limits', { exact: false }).click()
  await page.getByLabel('Maximum run time (seconds)', { exact: true }).fill('300')
  await page.getByLabel('Maximum model steps', { exact: true }).fill('20')
  await page.getByRole('button', { name: 'Create agent', exact: true }).click()
  await expect(page.getByRole('main').getByRole('heading', { name: 'Working glass dragon writer', exact: true })).toBeVisible()
  const id = page.url().split('/').at(-1)
  const get = async () => (await (await request.get(`${backend}/api/agent-native/agents/${id}`, { headers })).json())
  await expect.poll(async () => {
    const a = await get()
    if (['failed','unknown'].includes(a.work.state)) throw new Error(JSON.stringify(a.work))
    return a.work.state
  }, { timeout: 60000 }).toBe('completed')
  await expect(page.getByLabel('Execution status')).toHaveText('Automatic work off')
  const a = await get()
  expect(a.work.model_calls).toBeGreaterThan(5)
  expect(a.work.model_calls).toBeLessThanOrEqual(20)
  expect(a.work.outputs).toHaveLength(1)
  expect(a.work.results).toHaveLength(1)
  expect(a.work.stories).toHaveLength(0)
  expect(a.work.events.some((e: {kind:string}) => e.kind === 'work.effect')).toBeTruthy()
  const output = a.work.outputs[0]
  const saved = await (await request.get(`${backend}/api/agent-native/agents/${id}/outputs/${output.output_id}/versions/${output.version}`, { headers })).json()
  expect(a.work.results[0]).toMatchObject({ outcome: 'submitted', outputs: [{ output_id: output.output_id, version: 1 }] })
  expect(a.work.results[0].review.required).toBe(true)
  expect(saved.content).toContain('At moonrise, Mara found a dragon')
  const decision = page.getByRole('region', { name: 'Needs your decision', exact: true })
  await expect(decision).toContainText('Awaiting owner review')
  const overview = page.getByRole('region', { name: 'Current work overview', exact: true })
  await expect(overview).toContainText('Stage: Automatic work off')
  await expect(overview.getByRole('link', { name: 'Write The Silver Gate' })).toHaveAttribute('href', /\/issues\/[0-9a-f-]+\/$/)
  expect(await decision.evaluate((attention, current) => Boolean(attention.compareDocumentPosition(current as Node) & Node.DOCUMENT_POSITION_FOLLOWING), await overview.elementHandle())).toBe(true)
  await decision.getByRole('link', { name: /Version 1/ }).click()
  const reader = page.getByRole('article', { name: 'Output reader', exact: true })
  await expect(reader).toContainText('At moonrise, Mara found a dragon')
  await expect(reader.getByRole('region', { name: 'Output review', exact: true })).toContainText('Owner approval required')
  await reader.getByRole('button', { name: 'Accept output', exact: true }).click()
  await expect(reader).toContainText('Accepted this exact output version.')
  await expect.poll(async () => (await get()).work.results[0].acceptance).toBe('accepted')
  await expect(reader.getByRole('region', { name: 'Output review', exact: true })).toContainText('Accepted by owner')
  const beforeViewSwitch = await get()
  await page.getByRole('link', { name: 'Full view', exact: true }).click()
  await expect(page.getByRole('region', { name: 'Work results', exact: true })).toContainText('accepted this exact result')
  await expect(page.getByRole('region', { name: 'Work results', exact: true }).getByRole('button', { name: /Accept/ })).toHaveCount(0)
  await page.getByRole('link', { name: 'Compact view', exact: true }).click()
  const afterViewSwitch = await get()
  expect(afterViewSwitch.work).toMatchObject({ id: beforeViewSwitch.work.id, state: beforeViewSwitch.work.state, session_id: beforeViewSwitch.work.session_id, model_calls: beforeViewSwitch.work.model_calls })
  const proof = await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json()
  expect(proof.file_content).toBe(saved.content)
  expect(proof.items.some((i: {name:string}) => i.name === 'Write The Silver Gate')).toBeTruthy()
  expect(proof.cycles).toHaveLength(1)
  expect(proof.cycles[0].start_date ?? null).toBeNull()
  expect(proof.cycles[0].end_date ?? null).toBeNull()
  expect(proof.native_roles).toContain('tool')
  expect(proof.worker_alive).toBe(false)
  await page.goto(`/agents/${id}?view=full&output=${output.output_id}&version=1`)
  await page.reload()
  await expect(reader).toContainText('At moonrise, Mara found a dragon')
  expect((await get()).work.id).toBe(a.work.id)
  expect((await get()).work.model_calls).toBe(a.work.model_calls)
  expect((await get()).work.outputs).toHaveLength(1)
  expect((await get()).work.results).toHaveLength(1)
  await demoCheckpoint(page, test.info(), {
    title: 'A writer produces a saved, readable result',
    expected: 'A purpose starts planning and writing without a chat prompt; the exact output reopens after reload.',
    proof: `The story starts “At moonrise, Mara found a dragon”. One saved output and one submitted result persist; model calls=${a.work.model_calls}, worker_alive=${proof.worker_alive}.`,
    focus: reader,
  })
})


test('requesting revision on an exact output promptly wakes long-interval cadence', async ({ page, request }) => {
  test.setTimeout(90000)
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
  const created = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: crypto.randomUUID(), name: 'Revision wake writer',
    purpose: 'Write and revise a fantasy citadel draft. E2E_REVISION_CADENCE',
    autonomy_level: 1, work: { timeout_seconds: 180, max_iterations: 12 },
  } })
  expect(created.status()).toBe(201)
  const { id } = await created.json()
  const api = `${backend}/api/agent-native/agents/${id}`
  const current = async () => await (await request.get(api, { headers })).json()
  try {
    await expect.poll(async () => (await current()).work.state, { timeout: 30000 }).toBe('completed')
    const first = (await current()).work
    expect((await request.post(`${api}/cadence`, { headers, data: {
      expected_revision: 1, enabled: true, interval_seconds: 86400,
    } })).ok()).toBe(true)
    await page.goto(`/agents/${id}?view=full`)
    await page.getByRole('button', { name: 'Read output', exact: true }).click()
    const reader = page.getByRole('article', { name: 'Output reader', exact: true })
    await expect(reader).toContainText('The citadel still falls at dawn.')
    await reader.getByLabel('Revision instructions').fill('Give the citadel a hopeful survival at dawn.')
    await reader.getByRole('button', { name: 'Request revision', exact: true }).click()
    await expect(reader).toContainText('Revision requested.')

    await expect.poll(async () => {
      const agent = await current()
      return agent.work.id !== first.id && agent.work.state === 'completed'
    }, { timeout: 30000 }).toBe(true)
    const continued = await current()
    expect(continued.work.outputs.some((output: { version: number }) => output.version === 2)).toBe(true)
    const output = continued.work.outputs.find((candidate: { version: number }) => candidate.version === 2)
    const revised = await (await request.get(
      `${api}/outputs/${output.output_id}/versions/2`, { headers })).json()
    expect(revised.content).toContain('survives at dawn')
    expect(continued.work.id).not.toBe(first.id)
  } finally {
    await request.post(`${api}/work/pause`, { headers })
  }
})


test('Pause stops a real active worker and held model connection after navigating away and back', async ({ page, request }) => {
  test.setTimeout(60000)
  const marker = 'E2E_WRITER_HOLD_PAUSE'
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
  await page.goto('/agents')
  await page.getByLabel('Agent name', { exact: true }).fill('Pausable writer')
  await page.getByLabel('Purpose', { exact: true }).fill('Write fantasy stories. ' + marker)
  await page.getByLabel('Maximum run time (seconds)', { exact: true }).fill('300')
  await page.getByLabel('Maximum model steps', { exact: true }).fill('20')
  await page.getByRole('button', { name: 'Create agent', exact: true }).click()
  await expect(page.getByRole('main').getByRole('heading', { name: 'Pausable writer', exact: true })).toBeVisible()
  const id = page.url().split('/').at(-1)
  const get = async () => (await (await request.get(`${backend}/api/agent-native/agents/${id}`, { headers })).json())
  const hold = async () => (await (await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers })).json())
  await expect.poll(async () => (await hold()).entered, { timeout: 30000 }).toBe(true)
  const before = await get()
  expect(before.work.state).toBe('running')
  await page.goto('/agents')
  expect((await get()).work.id).toBe(before.work.id)
  await page.goto(`/agents/${id}`)
  await page.getByRole('button', { name: 'Pause', exact: true }).click()
  await expect(page.getByLabel('Execution status')).toHaveText('Paused')
  await expect.poll(async () => (await hold()).client_disconnected).toBe(true)
  const proof = await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json()
  expect(proof.worker_alive).toBe(false)
  const after = await get()
  expect(after.work.stories).toHaveLength(0)
  expect(after.work.model_calls).toBe(before.work.model_calls)
  await page.reload()
  expect((await get()).work.state).toBe('paused')
  expect((await get()).work.id).toBe(before.work.id)
  await expect(page.getByLabel('Execution status')).toHaveText('Paused')
  await demoCheckpoint(page, test.info(), {
    title: 'Pause stops the real worker',
    expected: 'After leaving and returning, Pause must terminate execution and the held model connection.',
    proof: `The same run stays paused after reload. worker_alive=${proof.worker_alive}; the model socket disconnected and model calls stayed at ${after.work.model_calls}.`,
    focus: page.getByRole('region', { name: 'Agent work', exact: true }),
  })
})

for (const limit of ['time', 'steps'] as const) {
  test(`the configured ${limit} limit ends work without another provider call`, async ({ page, request }) => {
    test.setTimeout(60000)
    await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
    await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
    const marker = 'E2E_WRITER_HOLD_TIME'
    const response = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
      request_id: crypto.randomUUID(), name: `Writer ${limit} limit`,
      purpose: 'Write a fantasy story. ' + (limit === 'time' ? marker : ''),
      work: { timeout_seconds: limit === 'time' ? 8 : 300, max_iterations: limit === 'steps' ? 2 : 20 },
    } })
    expect(response.status()).toBe(201)
    const created = await response.json()
    const get = async () => (await (await request.get(`${backend}/api/agent-native/agents/${created.id}`, { headers })).json())
    await page.goto(`/agents/${created.id}`)
    if (limit === 'time') {
      await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers })).json()).entered,
        { timeout: 15000 }).toBe(true)
    }
    await expect.poll(async () => (await get()).work.state, { timeout: 20000 }).toBe(limit === 'time' ? 'limit_reached' : 'failed')
    const final = await get()
    expect(final.work.model_calls).toBe(limit === 'time' ? 1 : 2)
    expect(final.work.stories).toHaveLength(0)
    const proof = await (await request.get(`${backend}/__e2e__/writer-evidence/${created.id}`, { headers })).json()
    expect(proof.worker_alive).toBe(false)
    if (limit === 'time') {
      await expect.poll(async () => (await (await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers })).json()).client_disconnected).toBe(true)
    }
    await page.reload()
    expect((await get()).work.model_calls).toBe(final.work.model_calls)
    await expect(page.getByLabel('Execution status')).toHaveText(limit === 'time' ? 'Run limit reached' : 'Failed')
    await demoCheckpoint(page, test.info(), {
      title: limit === 'time' ? 'The time limit interrupts a held call' : 'The step limit prevents another model call',
      expected: limit === 'time' ? 'An 8-second limit must stop the active worker and close the pending model connection.' : 'A 2-step limit must prevent a third provider call.',
      proof: `Persisted state=${final.work.state}; model_calls=${final.work.model_calls}; worker_alive=${proof.worker_alive}. Reload did not start another call.`,
      focus: page.getByRole('region', { name: 'Agent work', exact: true }),
    })
  })
}


test('polling keeps exactly one work panel and Pause control for an active writer', async ({ page, request }) => {
  test.setTimeout(60000)
  const marker = 'E2E_WRITER_HOLD_POLLING'
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
  const response = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: 'writer-polling-controls', name: 'Writer with stable controls',
    purpose: 'Write fantasy stories. ' + marker,
    work: { timeout_seconds: 300, max_iterations: 20 },
  } })
  expect(response.status()).toBe(201)
  const created = await response.json()
  const endpoint = `/api/agent-native/agents/${created.id}`
  const hold = async () => (await (await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers })).json())
  let activePolls = 0
  page.on('response', async (result) => {
    if (result.request().method() !== 'GET' || new URL(result.url()).pathname !== endpoint || !result.ok()) return
    const agent = await result.json().catch(() => null)
    if (agent?.work?.state === 'running') activePolls += 1
  })
  try {
    await page.goto(`/agents/${created.id}`)
    await expect.poll(async () => (await hold()).entered, { timeout: 30000 }).toBe(true)
    await expect.poll(() => activePolls, { timeout: 20000 }).toBeGreaterThanOrEqual(6)
    await expect(page.getByLabel('Execution status')).toHaveText('Running')
    await test.info().attach('actual-polling-controls.json', { contentType: 'application/json', body: JSON.stringify({
      activePolls, workPanels: await page.getByRole('region', { name: 'Agent work', exact: true }).count(),
      outputPanels: await page.getByRole('region', { name: 'Saved outputs', exact: true }).count(),
      pauseButtons: await page.getByRole('button', { name: 'Pause', exact: true }).count(),
    }) })
    await expect.soft(page.getByRole('region', { name: 'Agent work', exact: true })).toHaveCount(1)
    await expect.soft(page.getByRole('region', { name: 'Saved outputs', exact: true })).toHaveCount(1)
    await expect(page.getByRole('button', { name: 'Pause', exact: true })).toHaveCount(1)
    await demoCheckpoint(page, test.info(), {
      title: 'Live polling keeps one set of controls',
      expected: 'Repeated live updates must not duplicate the work panel, outputs panel or Pause button.',
      proof: `After ${activePolls} running-state polls: one work panel, one Saved outputs panel and one Pause control.`,
      focus: page.getByRole('region', { name: 'Agent work', exact: true }),
    })
    await page.getByRole('button', { name: 'Pause', exact: true }).click()
    await expect(page.getByLabel('Execution status')).toHaveText('Paused')
    await expect.poll(async () => (await hold()).client_disconnected).toBe(true)
    const proof = await (await request.get(`${backend}/__e2e__/writer-evidence/${created.id}`, { headers })).json()
    expect(proof.worker_alive).toBe(false)
    expect(proof.file_content).toBeNull()
    await expect(page.getByRole('region', { name: 'Agent work', exact: true })).toHaveCount(1)
    await expect(page.getByRole('region', { name: 'Saved outputs', exact: true })).toHaveCount(1)
    await expect(page.getByRole('button', { name: 'Pause', exact: true })).toHaveCount(0)
    await demoCheckpoint(page, test.info(), {
      title: 'Stopped controls reflect the actual process',
      expected: 'After Pause, the single work panel remains and its active Pause control disappears.',
      proof: `The screen shows Paused; worker_alive=${proof.worker_alive}, no output file, and zero Pause buttons.`,
      focus: page.getByRole('region', { name: 'Agent work', exact: true }),
    })
  } finally {
    await request.post(`${backend}${endpoint}/work/pause`, { headers })
    await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker } })
  }
})
