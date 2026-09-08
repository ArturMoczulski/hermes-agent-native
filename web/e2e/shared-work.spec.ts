import { expect, test, demoCheckpoint } from './demo-fixture'

const backend = 'http://127.0.0.1:19219'
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' }

// Real browser creation, planning adapter, native model loop, result store and API.
// Only the external model and Plane server are scripted, using fictional data.
test('a supplied-data analyst plans and records a report through the shared work path', async ({ page, request }) => {
  test.setTimeout(90000)
  const marker = 'E2E_ANALYST_REPORT'
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
  await page.goto('/agents')
  await page.getByLabel('Agent name', { exact: true }).fill('Supplied-data operations analyst')
  await page.getByLabel('Purpose', { exact: true }).fill(
    'Analyze this fictional operations sample: 12 fulfilled orders, revenue 150 credits, costs 90 credits. ' +
    'Report profit and margin using only this supplied sample. Do not browse or take external actions. ' + marker)
  await page.getByLabel('Maximum run time (seconds)', { exact: true }).fill('300')
  await page.getByLabel('Maximum model steps', { exact: true }).fill('20')
  await page.getByRole('button', { name: 'Create agent', exact: true }).click()
  await expect(page.getByRole('main').getByRole('heading', { name: 'Supplied-data operations analyst', exact: true })).toBeVisible()
  const id = page.url().split('/').at(-1)
  const get = async () => (await (await request.get(`${backend}/api/agent-native/agents/${id}`, { headers })).json())
  const evidence = async () => (await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json())
  await expect.poll(async () => (await evidence()).model_requests.filter((r: {system_text:string}) => r.system_text.includes(marker)).length,
    { timeout: 30000 }).toBeGreaterThan(0)
  const observed = (await evidence()).model_requests.find((r: {system_text:string}) => r.system_text.includes(marker))
  expect(observed.tools).toEqual(['output_publish', 'plane_operation_execute', 'plane_resource_inspect', 'result_record', 'work_item_select'])
  expect(observed.initial_context).not.toMatch(/fantasy story|writing task|story_publish/i)
  expect(observed.system_text).not.toContain('planning and story tools')
  await expect.poll(async () => {
    const a = await get()
    if (['failed', 'unknown'].includes(a.work.state)) throw new Error(JSON.stringify(a.work))
    return a.work.state
  }, { timeout: 60000 }).toBe('completed')
  await expect(page.getByLabel('Execution status')).toHaveText('Completed')
  const completed = await get()
  expect(completed.work.outputs).toHaveLength(1)
  expect(completed.work.results).toHaveLength(1)
  expect(completed.work.stories).toHaveLength(0)
  const output = completed.work.outputs[0]
  expect(output).toMatchObject({ title: 'Operations sample analysis', format: 'markdown', version: 1, run_id: completed.work.id })
  const response = await request.get(`${backend}/api/agent-native/agents/${id}/outputs/${output.output_id}/versions/${output.version}`, { headers })
  expect(response.status()).toBe(200)
  const saved = await response.json()
  expect(saved.content).toContain('Profit: 60 credits')
  expect(saved.content).toContain('Margin: 40%')
  expect(completed.work.results[0]).toMatchObject({
    outcome: 'submitted', outputs: [{ output_id: output.output_id, version: 1 }],
  })
  const proof = await evidence()
  expect(proof.file_content).toBe(saved.content)
  expect(proof.worker_alive).toBe(false)
  expect(proof.native_roles).toContain('tool')
  expect(proof.items.some((i: {name:string}) => i.name === 'Analyze the supplied operations sample')).toBeTruthy()
  expect(proof.cycles).toHaveLength(1)
  expect(proof.cycles[0].start_date ?? null).toBeNull()
  expect(proof.cycles[0].end_date ?? null).toBeNull()
  await expect(page.getByRole('region', { name: 'Saved outputs', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Read output', exact: true }).click()
  const reader = page.getByRole('article', { name: 'Output reader', exact: true })
  await expect(reader).toContainText('Profit: 60 credits')
  await expect(reader).toContainText('Margin: 40%')
  const outputUrl = new URL(page.url())
  expect(outputUrl.searchParams.get('output')).toBe(output.output_id)
  expect(outputUrl.searchParams.get('version')).toBe('1')
  expect([...outputUrl.searchParams.keys()].sort()).toEqual(['output', 'version'])
  const outputLink = reader.getByRole('link', { name: 'Link to this version', exact: true })
  await expect(outputLink).toHaveAttribute('href', `/agents/${id}?output=${output.output_id}&version=1`)
  const results = page.getByRole('region', { name: 'Work results', exact: true })
  await expect(results).toContainText('Submitted deliverable')
  await expect(results).toContainText('No owner decision is required')
  await expect(results.getByRole('button', { name: 'Accept result', exact: true })).toHaveCount(0)
  await expect(results).toContainText('Agent evaluation')
  await page.reload()
  await expect(reader).toContainText('Profit: 60 credits')
  const reloaded = await get()
  expect(reloaded.work.outputs).toEqual(completed.work.outputs)
  expect(reloaded.work.results).toEqual(completed.work.results)
  expect(reloaded.work.model_calls).toBe(completed.work.model_calls)
  expect((await request.get(`${backend}/api/agent-native/agents/${id}/outputs/${output.output_id}/versions/1`)).status()).toBe(401)
  await demoCheckpoint(page, test.info(), {
    title: 'The shared workflow also delivers an analyst report',
    expected: 'An analyst uses the same work tools and exact-version reader as the writer, with no duplicate work on reload.',
    proof: `The saved report shows Profit: 60 credits and Margin: 40%. Version ${output.version} survives reload; worker_alive=${proof.worker_alive}.`,
    focus: reader,
  })
  await demoCheckpoint(page, test.info(), {
    title: 'Submission is separate from acceptance',
    expected: 'A report must identify its agent evaluation without presenting it as accepted work.',
    proof: 'Submitted deliverable, Agent evaluation and No owner decision is required are all visible.',
    focus: results,
  })
  for (const suffix of ['&version=999', '']) {
    await page.goto(`/agents/${id}?output=${output.output_id}${suffix}`)
    await expect(page.getByRole('alert').filter({ hasText: 'Could not load or verify this output version' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Retry output', exact: true })).toBeVisible()
    await expect(reader).toHaveCount(0)
    await demoCheckpoint(page, test.info(), {
      title: suffix ? 'An unknown output version is rejected' : 'An incomplete output link is rejected',
      expected: 'Invalid version links must show an error instead of silently opening a different output.',
      proof: 'Could not load or verify this output version is visible, Retry output is available, and no output reader is present.',
      focus: page.getByRole('alert').filter({ hasText: 'Could not load or verify this output version' }),
    })
  }
  await page.goto(outputUrl.toString())
  await expect(reader).toContainText('Profit: 60 credits')
})

for (const outcome of ['discovery', 'waiting'] as const) {
  test(`a useful ${outcome} result survives reload without a fabricated file or task acceptance`, async ({ page, request }) => {
    test.setTimeout(90000)
    const marker = `E2E_ANALYST_${outcome.toUpperCase()}`
    await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
    await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
    await page.goto('/agents')
    const name = `Operations analyst ${outcome}`
    await page.getByLabel('Agent name', { exact: true }).fill(name)
    await page.getByLabel('Purpose', { exact: true }).fill(
      'Assess whether this fictional sample supports a growth trend: 12 fulfilled orders, revenue 150 credits, costs 90 credits. ' +
      'Only one period has been supplied. Record the missing evidence or a useful scope finding; a file is unnecessary. ' + marker)
    await page.getByText('Advanced work limits', { exact: false }).click()
    await page.getByLabel('Maximum run time (seconds)', { exact: true }).fill('300')
    await page.getByLabel('Maximum model steps', { exact: true }).fill('20')
    await page.getByRole('button', { name: 'Create agent', exact: true }).click()
    await expect(page.getByRole('main').getByRole('heading', { name, exact: true })).toBeVisible()
    const id = page.url().split('/').at(-1)
    const get = async () => (await (await request.get(`${backend}/api/agent-native/agents/${id}`, { headers })).json())
    await expect.poll(async () => {
      const a = await get()
      if (['failed', 'unknown'].includes(a.work.state)) throw new Error(JSON.stringify(a.work))
      return a.work.state
    }, { timeout: 60000 }).toBe('completed')
    const completed = await get()
    expect(completed.work.outputs).toEqual([])
    expect(completed.work.stories).toEqual([])
    expect(completed.work.results).toHaveLength(1)
    expect(completed.work.results[0]).toMatchObject({ outcome, outputs: [] })
    expect(completed.work.results[0].summary).toContain(outcome === 'discovery' ? 'no trend or forecast' : 'Waiting for the owner')
    const proof = await (await request.get(`${backend}/__e2e__/writer-evidence/${id}`, { headers })).json()
    expect(proof.file_content).toBeNull()
    expect(proof.worker_alive).toBe(false)
    expect(proof.native_roles).toContain('tool')
    expect(proof.items.every((item: {completed_at?:string|null}) => !item.completed_at)).toBe(true)
    await expect(page.getByRole('region', { name: 'Needs your decision', exact: true })).toHaveCount(0)
    await page.goto(`/agents/${id}?view=full`)
    const results = page.getByRole('region', { name: 'Work results', exact: true })
    await expect(results).toContainText(outcome === 'discovery' ? 'Discovery' : 'Waiting')
    await expect(results).toContainText(completed.work.results[0].summary)
    await expect(results).toContainText('No saved outputs for this result')
    await expect(results).toContainText('No owner decision is required')
    await expect(results.getByRole('button', { name: 'Accept result', exact: true })).toHaveCount(0)
    await expect(page.getByRole('region', { name: 'Saved outputs', exact: true })).toContainText('No output versions saved yet')
    await page.reload()
    await expect(results).toContainText(completed.work.results[0].summary)
    const reloaded = await get()
    expect(reloaded.work.results).toEqual(completed.work.results)
    expect(reloaded.work.outputs).toEqual([])
    expect(reloaded.work.model_calls).toBe(completed.work.model_calls)
    await demoCheckpoint(page, test.info(), {
      title: outcome === 'discovery' ? 'Discovery is useful without a file' : 'Waiting is recorded without pretending the task is accepted',
      expected: 'A file-free result must retain its explanation after reload, with acceptance left unevaluated.',
      proof: `Result=${outcome}; saved outputs=${reloaded.work.outputs.length}; worker_alive=${proof.worker_alive}. The result summary is retained and no Plane item was marked complete.`,
      focus: results,
    })
  })
}


test('a plain text output renders literally and reopens by exact version', async ({ page, request }) => {
  test.setTimeout(90000)
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  await request.put(`${backend}/__e2e__/plane-config`, { headers, data: { enabled: true } })
  const response = await request.post(`${backend}/api/agent-native/agents`, { headers, data: {
    request_id: 'analyst-plaintext-reader', name: 'Literal operations analyst',
    purpose: 'Record literal text notes for this fictional operations sample: revenue 150 credits, costs 90 credits. E2E_ANALYST_TEXT',
    work: { timeout_seconds: 300, max_iterations: 20 },
  } })
  expect(response.status()).toBe(201)
  const created = await response.json()
  const get = async () => (await (await request.get(`${backend}/api/agent-native/agents/${created.id}`, { headers })).json())
  await page.goto(`/agents/${created.id}`)
  await expect.poll(async () => {
    const agent = await get()
    if (['failed', 'unknown'].includes(agent.work.state)) throw new Error(JSON.stringify(agent.work))
    return agent.work.state
  }, { timeout: 60000 }).toBe('completed')
  const agent = await get()
  expect(agent.work.outputs[0].format).toBe('text')
  await page.getByRole('button', { name: 'Read output', exact: true }).click()
  const reader = page.getByRole('article', { name: 'Output reader', exact: true })
  await expect(reader.locator('pre')).toHaveText('# Literal heading\n<script>window.outputScriptRan = true</script>\n**These are literal characters.**\n')
  await expect(reader.getByRole('heading', { name: 'Literal heading', exact: true })).toHaveCount(0)
  await expect(reader.locator('script')).toHaveCount(0)
  await page.reload()
  await expect(reader.locator('pre')).toContainText('**These are literal characters.**')
  await expect(reader.locator('script')).toHaveCount(0)
  const proof = await (await request.get(`${backend}/__e2e__/writer-evidence/${created.id}`, { headers })).json()
  expect(proof.worker_alive).toBe(false)
  expect(proof.file_content).toContain('# Literal heading')
  await demoCheckpoint(page, test.info(), {
    title: 'Plain text remains literal and safe',
    expected: 'Text output must preserve Markdown and script-looking characters without interpreting them.',
    proof: 'The exact-version reader retains # Literal heading and **These are literal characters.** after reload. It contains no script element or rendered Markdown heading.',
    focus: reader,
  })
})
