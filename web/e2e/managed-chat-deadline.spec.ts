import { stripVTControlCharacters } from 'node:util'
import { test, expect, demoCheckpoint } from './demo-fixture'

const backend = 'http://127.0.0.1:19219'
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' }

test('a managed reply deadline closes the real model request and the next message can complete', async ({ page, request }) => {
  test.setTimeout(150000)
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
  const marker = 'deadlineHold' + crypto.randomUUID().replaceAll('-', '')
  const heldPrompt = `Managed conversation test: what is your purpose? ${marker}`
  const nextPrompt = 'Managed conversation test: what is your purpose? afterDeadlineQ4'
  const lateReply = `LATE_TIMEOUT_REPLY_${marker}`
  const configured = await request.post(`${backend}/__e2e__/managed-deadline-config`, {
    headers, data: { timeout_seconds: 10 }
  })
  expect(configured.ok()).toBe(true)
  const held = await request.post(`${backend}/__e2e__/hold-model`, { headers, data: { marker } })
  expect(held.ok()).toBe(true)
  try {
    const created = await request.post(`${backend}/api/agent-native/agents`, {
      headers, data: { request_id: crypto.randomUUID(), name: 'Deadline citadel writer', purpose: 'Write original stories about the moonlit citadel.' }
    })
    expect(created.status()).toBe(201)
    const agent = await created.json()
    let output = ''
    let storedSession = ''
    page.on('websocket', socket => {
      const path = new URL(socket.url()).pathname
      socket.on('framereceived', ({ payload }) => {
        const text = typeof payload === 'string' ? payload : payload.toString('utf8')
        if (path === '/api/pty') output += text
        if (path === '/api/events') {
          try {
            const frame = JSON.parse(text)
            if (frame.params?.type === 'session.info' && frame.params.payload?.managed_agent?.id === agent.id) {
              storedSession = frame.params.payload.stored_session_id
            }
          } catch { /* Ignore unrelated non-JSON transport output. */ }
        }
      })
    })
    await page.goto(`/agents/${agent.id}/chat`)
    await expect(page.getByLabel('Conversation agent')).toContainText(agent.name)
    await expect(page.locator('.hermes-chat-xterm-host .xterm-screen')).toBeVisible()
    const native = async () => await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json()
    await expect.poll(async () => (await native()).managed_ready_ids, { timeout: 45000 }).toContain(agent.id)
    await expect.poll(() => storedSession).not.toBe('')
    const attach = await page.evaluate(() => localStorage.getItem('hermes.pty.token.chat'))
    const delivery = async () => await (await request.get(`${backend}/__e2e__/managed-delivery/${agent.id}?attach_token=${attach}`, { headers })).json()
    const hold = async () => await (await request.get(`${backend}/__e2e__/model-holds/${marker}`, { headers })).json()
    const send = async (text: string) => {
      await page.locator('.xterm-helper-textarea').focus()
      await page.keyboard.press('Control+u')
      await page.keyboard.type(text)
      // Observe native consumption before a standalone Enter; mixed text+CR is paste.
      await expect.poll(async () => (await delivery()).composer?.draft?.input).toBe(text)
      await page.locator('.xterm-helper-textarea').press('Enter')
    }

    await send(heldPrompt)
    await expect.poll(async () => (await hold()).entered, { timeout: 15000 }).toBe(true)
    const worker = async () => (await native()).managed_workers.find((w: { agent_id: string }) => w.agent_id === agent.id)
    const runningWorker = await worker()
    expect(runningWorker).toMatchObject({ running: true })
    expect(runningWorker.pid).toBeGreaterThan(0)
    await expect.poll(async () => (await delivery()).composer?.pending?.status, { timeout: 18000 }).toBe('error')
    await expect.poll(() => stripVTControlCharacters(output).replace(/\s+/g, '').toLowerCase()).toContain('timedout')
    // A timeout badge alone is insufficient: the real provider socket must close.
    await expect.poll(async () => (await hold()).client_disconnected, { timeout: 5000 }).toBe(true)
    expect((await hold()).request_count).toBe(1)
    expect(await worker()).toMatchObject({ pid: runningWorker.pid, running: false })

    expect((await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker } })).ok()).toBe(true)
    await send(nextPrompt)
    await expect.poll(async () => (await delivery()).composer?.pending, { timeout: 30000 }).toBeNull()
    expect((await worker()).pid).not.toBe(runningWorker.pid)
    const history = await (await request.get(`${backend}/api/sessions/${storedSession}/messages`, { headers })).json()
    const messages = history.messages.filter((m: { role: string }) => ['user', 'assistant'].includes(m.role))
    expect(messages.map((m: { content: string }) => m.content)).toEqual([heldPrompt, nextPrompt, `My purpose: ${agent.purpose}`])
    expect(output).not.toContain(lateReply)
    expect(JSON.stringify(history)).not.toContain(lateReply)
    const requests = (await native()).model_requests
    const heldRequests = requests.filter((r: { last_user: string }) => r.last_user === heldPrompt)
    const nextRequests = requests.filter((r: { last_user: string }) => r.last_user.endsWith(nextPrompt))
    expect(heldRequests).toHaveLength(1)
    expect(nextRequests).toHaveLength(1)
    // A replacement worker must keep the same protected model-request prefix.
    expect(nextRequests[0].system_prompt_sha256).toBe(heldRequests[0].system_prompt_sha256)
    const after = await (await request.get(`${backend}/api/agent-native/agents/${agent.id}`, { headers })).json()
    expect(after.execution).toBe('not_started')
    await expect.poll(() => stripVTControlCharacters(output).replace(/\s+/g, '')).toContain(`My purpose: ${agent.purpose}`.replace(/\s+/g, ''))
    await demoCheckpoint(page, test.info(), {
      title: 'A timed-out reply stops; a new message succeeds',
      expected: 'Terminate the stuck model request at its deadline, then allow a fresh message.',
      proof: 'The old worker and provider socket stopped. A new worker completed the next reply; history contains no late timeout reply and project work remains not started.',
      focus: page.locator('.hermes-chat-xterm-host .xterm-screen'),
    })
  } finally {
    await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker } })
    await request.post(`${backend}/__e2e__/managed-deadline-config`, { headers, data: { timeout_seconds: 90 } })
  }
})
