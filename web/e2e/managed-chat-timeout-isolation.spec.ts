import { type APIRequestContext, type Page } from './fixtures'
import { test, expect, demoCheckpoint } from './demo-fixture'

const backend = 'http://127.0.0.1:19219'
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' }
type Agent = { id: string; name: string; purpose: string }
type Receipt = { id: string; status: string; reason?: string }

async function openConversation(page: Page, request: APIRequestContext, agent: Agent) {
  let storedSession = ''
  let output = ''
  await page.addInitScript(() => { window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only' })
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
  await expect.poll(() => storedSession, { timeout: 15000 }).not.toBe('')
  const attach = await page.evaluate(() => localStorage.getItem('hermes.pty.token.chat'))
  expect(attach).toBeTruthy()
  const delivery = async () => await (await request.get(
    `${backend}/__e2e__/managed-delivery/${agent.id}?attach_token=${attach}`, { headers }
  )).json()
  const receipt = (messageId: string, retryText?: string) => page.evaluate(
    ({ agentId, sessionId, messageId, retryText, backend }) => new Promise<Receipt>((resolve, reject) => {
      const socket = new WebSocket(
        `${backend.replace('http:', 'ws:')}/api/ws?agent=${agentId}&purpose_revision=1&token=agent-native-local-e2e-only`
      )
      const timer = setTimeout(() => {
        socket.close()
        reject(new Error('Native receipt request timed out'))
      }, 10000)
      socket.onopen = () => socket.send(JSON.stringify({
        id: 'resume', method: 'session.resume', params: { session_id: sessionId }
      }))
      socket.onmessage = event => {
        const frame = JSON.parse(String(event.data))
        if (frame.id !== 'resume' && frame.id !== 'receipt') return
        if (frame.error) {
          clearTimeout(timer)
          socket.close()
          reject(new Error(frame.error.message))
          return
        }
        if (frame.id === 'resume') {
          socket.send(JSON.stringify({
            id: 'receipt', method: retryText === undefined ? 'prompt.receipt' : 'prompt.submit',
            params: {
              session_id: frame.result.session_id, client_message_id: messageId,
              ...(retryText === undefined ? {} : { text: retryText })
            }
          }))
        } else {
          clearTimeout(timer)
          socket.close()
          resolve(frame.result.receipt)
        }
      }
    }),
    { agentId: agent.id, sessionId: storedSession, messageId, retryText, backend }
  )
  return {
    delivery, receipt, output: () => output, session: () => storedSession,
    send: async (text: string) => {
      await page.locator('.xterm-helper-textarea').focus()
      await page.keyboard.type(text)
      // Native PTY consumption must precede Enter; mixed text+CR is paste.
      await expect.poll(async () => (await delivery()).composer?.draft?.input).toBe(text)
      await page.locator('.xterm-helper-textarea').press('Enter')
      await expect.poll(async () => (await delivery()).composer?.pending?.id).toBeTruthy()
      return (await delivery()).composer.pending.id as string
    }
  }
}

test('one managed timeout leaves another held conversation alive and able to finish', async ({ page, context, request }) => {
  test.setTimeout(150000)
  const markerA = 'isolationA' + crypto.randomUUID().replaceAll('-', '')
  const markerB = 'isolationB' + crypto.randomUUID().replaceAll('-', '')
  const promptA = `Managed conversation test: what is your purpose? ${markerA}`
  const promptB = `Managed conversation test: what is your purpose? ${markerB}`
  const configure = async (timeout_seconds: number) => {
    expect((await request.post(`${backend}/__e2e__/managed-deadline-config`, {
      headers, data: { timeout_seconds }
    })).ok()).toBe(true)
  }
  const hold = async (marker: string) => await (await request.get(
    `${backend}/__e2e__/model-holds/${marker}`, { headers }
  )).json()
  const secondPage = await context.newPage()
  try {
    for (const marker of [markerA, markerB]) {
      expect((await request.post(`${backend}/__e2e__/hold-model`, { headers, data: { marker } })).ok()).toBe(true)
    }
    await configure(10)
    const create = async (name: string, purpose: string): Promise<Agent> => {
      const response = await request.post(`${backend}/api/agent-native/agents`, {
        headers, data: { request_id: crypto.randomUUID(), name, purpose }
      })
      expect(response.status()).toBe(201)
      return await response.json()
    }
    const agentA = await create('Timeout isolation citadel writer', 'Write original stories about the moonlit citadel.')
    const agentB = await create('Timeout isolation ocean writer', 'Write original stories about the glass ocean.')
    // Prepare both renderers without starting work. Cold UI startup must not
    // consume the deliberate ten-second overlap between these provider calls.
    const chatA = await openConversation(page, request, agentA)
    const chatB = await openConversation(secondPage, request, agentB)
    expect(chatA.session()).not.toBe(chatB.session())
    const idA = await chatA.send(promptA)
    await expect.poll(async () => (await hold(markerA)).entered, { timeout: 10000 }).toBe(true)
    expect(await chatA.receipt(idA)).toMatchObject({ id: idA, status: 'running' })

    await configure(30)
    const idB = await chatB.send(promptB)
    await expect.poll(async () => (await hold(markerB)).entered, { timeout: 10000 }).toBe(true)
    // Prove genuine overlap, not merely that a second agent starts after A dies.
    expect((await hold(markerA)).client_disconnected).toBe(false)
    expect(await chatB.receipt(idB)).toMatchObject({ id: idB, status: 'running' })
    await expect.poll(async () => (await chatA.receipt(idA)).status, { timeout: 18000 }).toBe('error')
    await expect.poll(async () => (await hold(markerA)).client_disconnected, { timeout: 5000 }).toBe(true)
    expect((await chatA.receipt(idA)).reason?.toLowerCase()).toContain('tim')
    expect(await hold(markerB)).toMatchObject({ entered: true, client_disconnected: false, request_count: 1, released: false })
    expect(await chatB.receipt(idB)).toMatchObject({ id: idB, status: 'running' })

    expect((await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: markerB } })).ok()).toBe(true)
    await expect.poll(async () => (await chatB.receipt(idB)).status, { timeout: 10000 }).toBe('complete')
    await expect.poll(async () => (await chatB.delivery()).composer?.pending, { timeout: 10000 }).toBeNull()
    const lateB = `LATE_TIMEOUT_REPLY_${markerB}`
    await expect.poll(chatB.output).toContain(lateB)
    expect((await hold(markerB)).write_succeeded).toBe(true)

    // Releasing A and explicitly retrying its immutable UUID cannot resurrect it.
    expect((await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker: markerA } })).ok()).toBe(true)
    expect(await chatA.receipt(idA, promptA)).toMatchObject({ id: idA, status: 'error' })
    const history = async (session: string) => await (await request.get(
      `${backend}/api/sessions/${session}/messages`, { headers }
    )).json()
    const historyA = await history(chatA.session())
    const historyB = await history(chatB.session())
    const conversation = (data: { messages: { role: string; content: string }[] }) => data.messages
      .filter(m => ['user', 'assistant'].includes(m.role)).map(m => m.content)
    expect(conversation(historyA)).toEqual([promptA])
    expect(conversation(historyB)).toEqual([promptB, lateB])
    const lateA = `LATE_TIMEOUT_REPLY_${markerA}`
    expect(chatA.output()).not.toContain(lateA)
    expect(chatB.output()).not.toContain(lateA)
    expect(JSON.stringify(historyA)).not.toContain(lateA)
    expect(await hold(markerA)).toMatchObject({ request_count: 1, write_succeeded: false })
    expect(await hold(markerB)).toMatchObject({ request_count: 1, write_succeeded: true })
    const native = await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json()
    for (const prompt of [promptA, promptB]) {
      expect(native.model_requests.filter((r: { last_user: string }) => r.last_user === prompt)).toHaveLength(1)
    }
    // Both deadline-sensitive branches are settled before recording either hold.
    await demoCheckpoint(page, test.info(), {
      title: 'A timeout stays isolated to its conversation',
      expected: 'The citadel agent times out without terminating the other agent’s concurrent reply.',
      proof: 'This conversation has an error receipt and only its user message in history. Its worker socket closed, and retrying the same message ID did not restart it.',
      focus: page.locator('.hermes-chat-xterm-host .xterm-screen'),
    })
    await demoCheckpoint(secondPage, test.info(), {
      title: 'The other concurrent conversation finishes',
      expected: 'The ocean agent remains alive while the citadel agent times out, then completes normally.',
      proof: 'This terminal shows the released test reply. Its receipt is complete and history contains its own exchange; one model request occurred for each agent, with no cross-agent late reply.',
      focus: secondPage.locator('.hermes-chat-xterm-host .xterm-screen'),
    })
  } finally {
    for (const marker of [markerA, markerB]) {
      await request.post(`${backend}/__e2e__/release-model`, { headers, data: { marker } })
    }
    await configure(90)
    await secondPage.close()
  }
})
