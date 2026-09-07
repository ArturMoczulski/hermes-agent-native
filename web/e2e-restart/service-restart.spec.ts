import { stripVTControlCharacters } from 'node:util'
import { type APIRequestContext, type Page } from '@playwright/test'
import { test, expect, demoCheckpoint } from '../e2e/demo-fixture'

const backend = 'http://127.0.0.1:19219'
const control = 'http://127.0.0.1:19218'
const fixtureHeaders = { 'X-Hermes-Fixture-Token': 'agent-native-restart-control-e2e-only' }
const purpose = 'Write original stories about the moonlit citadel.'

async function conversation(page: Page, request: APIRequestContext, name: string) {
  // Exercise the normal HTML token injection. Fixed test tokens would conceal
  // the real authentication boundary when the service process is replaced.
  await page.goto('/agents')
  const headers = async () => ({ 'X-Hermes-Session-Token': await page.evaluate(() => window.__HERMES_SESSION_TOKEN__!) })
  const get = async (path: string) => await (await request.get(`${backend}${path}`, { headers: await headers() })).json()
  const created = await request.post(`${backend}/api/agent-native/agents`, {
    headers: await headers(), data: { request_id: crypto.randomUUID(), name, purpose },
  })
  expect(created.status()).toBe(201)
  const agent = await created.json()
  const bound = await request.post(`${backend}/api/agent-native/agents/${agent.id}/chat`, { headers: await headers() })
  expect(bound.ok()).toBe(true)
  const sessionId = (await bound.json()).session_id
  let output = ''
  page.on('websocket', socket => {
    if (new URL(socket.url()).pathname === '/api/pty') socket.on('framereceived', ({ payload }) => { output += payload.toString() })
  })
  await page.goto(`/agents/${agent.id}/chat`)
  await expect(page.getByLabel('Conversation agent')).toContainText(name)
  await expect(page.locator('.hermes-chat-xterm-host .xterm-screen')).toBeVisible()
  const ready = async () => {
    await expect.poll(async () => (await get('/__e2e__/native-chat-evidence')).managed_ready_ids, { timeout: 45000 }).toContain(agent.id)
  }
  await ready()
  const attach = await page.evaluate(() => localStorage.getItem('hermes.pty.token.chat'))
  expect(attach).toBeTruthy()
  const delivery = () => get(`/__e2e__/managed-delivery/${agent.id}?attach_token=${attach}`)
  const write = async (text: string) => {
    await page.locator('.xterm-helper-textarea').focus()
    await page.keyboard.press('Control+u')
    await page.keyboard.type(text)
    await expect.poll(async () => (await delivery()).composer?.draft?.input).toBe(text)
  }
  const send = async (text: string) => { await write(text); await page.locator('.xterm-helper-textarea').press('Enter') }
  const history = async () => ((await get(`/api/sessions/${sessionId}/messages`)).messages ?? []).filter((m: { role: string }) => ['user', 'assistant'].includes(m.role)).map((m: { content: string }) => m.content)
  return { agent, sessionId, attach, headers, get, ready, delivery, write, send, history, output: () => stripVTControlCharacters(output).replace(/\s+/g, ''), clearOutput: () => { output = '' } }
}

async function crash(request: APIRequestContext) {
  const stopped = await request.post(`${control}/__e2e__/restart/stop`, { headers: fixtureHeaders, data: { mode: 'crash' } })
  expect(stopped.ok()).toBe(true)
  const evidence = await stopped.json()
  expect(evidence.backend_alive).toBe(false)
  // Never let fixture cleanup hide an orphaned renderer or model worker.
  expect(evidence.survivors).toEqual([])
  expect(evidence.previous_processes.some((p: { role: string; alive: boolean }) => p.role === 'renderer' && !p.alive)).toBe(true)
  return evidence
}
async function start(request: APIRequestContext) {
  const started = await request.post(`${control}/__e2e__/restart/start`, { headers: fixtureHeaders, data: {} })
  expect(started.ok()).toBe(true)
  return await started.json()
}
async function requests(request: APIRequestContext) {
  return (await (await request.get(`${control}/__e2e__/model-requests`, { headers: fixtureHeaders })).json()).model_requests
}
async function freshBrowserToken(page: Page, oldToken: string) {
  // No page.goto/reload/reconnect click here: the open conversation must recover.
  await expect.poll(async () => {
    try {
      const token = await page.evaluate(() => window.__HERMES_SESSION_TOKEN__)
      return typeof token === 'string' && token.length > 0 && token !== oldToken
    } catch { return false }
  }, { timeout: 30000 }).toBe(true)
  await expect(page.locator('.hermes-chat-xterm-host .xterm-screen')).toBeVisible()
}

test('saved conversation and unsent draft recover across a whole service crash without resubmission', async ({ page, request }) => {
  test.setTimeout(150000)
  const c = await conversation(page, request, 'Restart draft writer')
  const prompt = 'Managed conversation test: what is your purpose? beforeServiceRestartQ9'
  await c.send(prompt)
  await expect.poll(c.history, { timeout: 45000 }).toEqual([prompt, `My purpose: ${purpose}`])
  await expect.poll(async () => (await c.delivery()).composer?.pending).toBeNull()
  const draft = 'Unsent service restart draft moonlitDraftQ9'
  await c.write(draft)
  const beforeCount = (await requests(request)).length
  const oldToken = (await c.headers())['X-Hermes-Session-Token']
  c.clearOutput()
  const stopped = await crash(request)
  const started = await start(request)
  expect(started.home_id).toBe(stopped.home_id)
  expect(started.generation).toBeGreaterThan(stopped.generation)
  expect((await request.get(`${backend}/api/agent-native/agents`, { headers: { 'X-Hermes-Session-Token': oldToken } })).status()).toBe(401)
  await freshBrowserToken(page, oldToken)
  await c.ready()
  c.clearOutput()
  expect(await page.evaluate(() => localStorage.getItem('hermes.pty.token.chat'))).toBe(c.attach)
  await expect.poll(async () => (await c.delivery()).composer?.draft?.input).toBe(draft)
  await page.locator('.xterm-helper-textarea').focus()
  await page.keyboard.press('Control+l')
  await expect.poll(c.output).toContain('moonlitDraftQ9')
  expect(await c.history()).toEqual([prompt, `My purpose: ${purpose}`])
  expect((await requests(request)).length).toBe(beforeCount)
  await demoCheckpoint(page, test.info(), {
    title: 'The whole service restarts without losing your draft',
    expected: 'Recover the open chat, saved conversation and unsent draft after an actual service crash.',
    proof: 'moonlitDraftQ9 is restored in the composer. The browser refreshed its expired owner token automatically; history is unchanged and no model request was replayed.',
    focus: page.locator('.hermes-chat-xterm-host .xterm-screen'),
  })
  await c.send('Managed conversation test: remember our conversation?')
  await expect.poll(c.history, { timeout: 45000 }).toEqual([prompt, `My purpose: ${purpose}`, 'Managed conversation test: remember our conversation?', 'Our conversation is retained.'])
  await expect.poll(async () => (await c.delivery()).composer?.pending).toBeNull()
  expect((await requests(request)).length).toBe(beforeCount + 1)
  await expect.poll(c.output).toContain('Ourconversationisretained.')
  expect((await c.get(`/api/agent-native/agents/${c.agent.id}`)).execution).toBe('not_started')
  await demoCheckpoint(page, test.info(), {
    title: 'Recovered chat can continue the same conversation',
    expected: 'After service recovery, send a follow-up and retain the previous exchange.',
    proof: 'The saved conversation now contains “Our conversation is retained”. Exactly one fresh model request followed the restart; project work did not start.',
    focus: page.locator('.hermes-chat-xterm-host .xterm-screen'),
  })
})

test('an interrupted managed message becomes visibly uncertain after service restart and is never replayed', async ({ page, request }) => {
  test.setTimeout(150000)
  const c = await conversation(page, request, 'Restart interrupted writer')
  const marker = 'restartHold' + crypto.randomUUID().replaceAll('-', '')
  const heldPrompt = `Managed conversation test: what is your purpose? ${marker}`
  expect((await request.post(`${control}/__e2e__/hold-model`, { headers: fixtureHeaders, data: { marker } })).ok()).toBe(true)
  const hold = async () => (await (await request.get(`${control}/__e2e__/model-holds/${marker}`, { headers: fixtureHeaders })).json())
  try {
    await c.send(heldPrompt)
    await expect.poll(async () => (await hold()).entered, { timeout: 30000 }).toBe(true)
    const pending = (await c.delivery()).composer.pending
    expect(['accepted', 'running', 'pending']).toContain(pending.status)
    const oldToken = (await c.headers())['X-Hermes-Session-Token']
    const worker = (await c.get('/__e2e__/native-chat-evidence')).managed_workers.find((w: { message_id: string }) => w.message_id === pending.id)
    expect(worker).toMatchObject({ running: true })
    expect(worker.pid).toBeGreaterThan(0)
    c.clearOutput()
    const stopped = await crash(request)
    expect(stopped.previous_processes).toContainEqual(expect.objectContaining({ pid: worker.pid, role: 'managed_worker', alive: false }))
    await expect.poll(async () => (await hold()).client_disconnected, { timeout: 5000 }).toBe(true)
    await start(request)
    await freshBrowserToken(page, oldToken)
    await c.ready()
    await expect.poll(async () => (await c.delivery()).composer?.pending?.status, { timeout: 15000 }).toBe('unknown')
    const recovered = (await c.delivery()).composer
    expect(recovered.pending.id).toBe(pending.id)
    expect(recovered.pending.text).toBe(heldPrompt)
    const receipt = await c.get(`/__e2e__/native-receipt/${c.agent.id}/${pending.id}`)
    expect(receipt.session_id).toBe(c.sessionId)
    expect(receipt.receipt).toMatchObject({ id: pending.id, text: heldPrompt, status: 'unknown' })
    expect(recovered.draft.input).toBe(heldPrompt)
    await expect.poll(c.output).toContain('/acknowledge')
    expect((await hold()).request_count).toBe(1)
    expect(await c.history()).toEqual([heldPrompt])
    await demoCheckpoint(page, test.info(), {
      title: 'An interrupted message is visibly uncertain',
      expected: 'After a crash during a reply, preserve the message and require acknowledgement instead of resending it.',
      proof: 'The terminal offers /acknowledge. The same message ID has an unknown receipt, its text remains in the draft, and only its original model request exists.',
      focus: page.locator('.hermes-chat-xterm-host .xterm-screen'),
    })
    expect((await request.post(`${control}/__e2e__/release-model`, { headers: fixtureHeaders, data: { marker } })).ok()).toBe(true)
    await c.send('/acknowledge')
    await expect.poll(async () => (await c.delivery()).composer?.pending).toBeNull()
    const next = 'Managed conversation test: what is your purpose? afterServiceRestartQ8'
    await c.send(next)
    await expect.poll(c.history, { timeout: 45000 }).toEqual([heldPrompt, next, `My purpose: ${purpose}`])
    await expect.poll(async () => (await c.delivery()).composer?.pending).toBeNull()
    expect(c.output()).not.toContain(`LATE_TIMEOUT_REPLY_${marker}`)
    expect((await hold()).request_count).toBe(1)
    expect((await requests(request)).filter((r: { last_user: string }) => r.last_user.endsWith(next))).toHaveLength(1)
    await expect.poll(c.output).toContain(`My purpose: ${purpose}`.replace(/\s+/g, ''))
    expect((await c.get(`/api/agent-native/agents/${c.agent.id}`)).execution).toBe('not_started')
    await demoCheckpoint(page, test.info(), {
      title: 'Acknowledgement clears uncertainty for a new message',
      expected: 'Acknowledge the interrupted message, then send a new one without reviving the old reply.',
      proof: 'The new purpose reply is saved and the pending message is cleared. No late interrupted reply was recorded; the old request count remains one.',
      focus: page.locator('.hermes-chat-xterm-host .xterm-screen'),
    })
  } finally {
    await request.post(`${control}/__e2e__/release-model`, { headers: fixtureHeaders, data: { marker } })
  }
})
