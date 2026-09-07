import { stripVTControlCharacters } from 'node:util'
import { test, expect, demoCheckpoint } from './demo-fixture'

const backend = 'http://127.0.0.1:19219'
const headers = { 'X-Hermes-Session-Token': 'agent-native-local-e2e-only' }
const prompt = 'Managed conversation test: what is your purpose? lostAckProofQ8'
const newerDraft = 'newerUnsentDraftAckQ9'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.__HERMES_SESSION_TOKEN__ = 'agent-native-local-e2e-only'
  })
})

test('a lost native acknowledgement reconciles once and preserves a newer unsent draft', async ({
  page,
  request
}, testInfo) => {
  test.setTimeout(150000)
  const response = await request.post(`${backend}/api/agent-native/agents`, {
    headers,
    data: {
      request_id: crypto.randomUUID(),
      name: 'Receipt citadel writer',
      purpose: 'Write original stories about the moonlit citadel.'
    }
  })
  expect(response.status()).toBe(201)
  const agent = await response.json()
  let storedSession = ''
  let terminalOutput = ''
  const terminalInput: string[] = []
  page.on('websocket', socket => {
    const path = new URL(socket.url()).pathname
    if (path === '/api/pty')
      socket.on('framesent', ({ payload }) =>
        terminalInput.push(typeof payload === 'string' ? payload : payload.toString('utf8'))
      )
    socket.on('framereceived', ({ payload }) => {
      const text = typeof payload === 'string' ? payload : payload.toString('utf8')
      if (path === '/api/pty') terminalOutput += text
      if (path === '/api/events') {
        try {
          const frame = JSON.parse(text)
          if (frame.params?.type === 'session.info' && frame.params.payload?.managed_agent?.id === agent.id) {
            storedSession = frame.params.payload.stored_session_id
          }
        } catch {
          /* Ignore unrelated transport output. */
        }
      }
    })
  })
  await page.goto(`/agents/${agent.id}/chat`)
  await expect(page.getByLabel('Conversation agent')).toContainText(agent.name)
  await expect(page.locator('.hermes-chat-xterm-host .xterm-screen')).toBeVisible()
  const nativeEvidence = async () =>
    await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json()
  await expect.poll(async () => (await nativeEvidence()).managed_ready_ids, { timeout: 45000 }).toContain(agent.id)
  await expect.poll(() => storedSession, { timeout: 45000 }).not.toBe('')
  await expect.poll(() => terminalOutput).toContain('Session:')
  const attach = await page.evaluate(() => window.localStorage.getItem('hermes.pty.token.chat'))
  expect(attach).toBeTruthy()
  const evidenceUrl = `${backend}/__e2e__/managed-delivery/${agent.id}?attach_token=${attach}`
  const delivery = async () => await (await request.get(evidenceUrl, { headers })).json()
  expect(
    (await request.post(`${backend}/__e2e__/drop-next-managed-ack`, { headers, data: { agent_id: agent.id } })).ok()
  ).toBe(true)

  await page.locator('.xterm-helper-textarea').focus()
  await page.keyboard.type(prompt)
  await expect.poll(async () => (await delivery()).composer?.draft?.input).toBe(prompt)
  await page.keyboard.press('Enter')
  try {
    await expect.poll(() => terminalOutput, { timeout: 45000 }).toContain(`My purpose: ${agent.purpose}`)
  } catch (error) {
    await testInfo.attach('native-delivery-evidence', {
      body: JSON.stringify({ terminalInput, delivery: await delivery(), native: await nativeEvidence() }),
      contentType: 'application/json'
    })
    throw error
  }
  await expect.poll(async () => (await delivery()).dropped_receipts.length).toBe(1)
  await expect.poll(async () => (await delivery()).composer?.pending, { timeout: 15000 }).toBeNull()
  const messageId = (await delivery()).dropped_receipts[0]

  // Explicitly repeat the exact lost request over the real native WS protocol.
  // The gateway must return the completed receipt, not start another model turn.
  const duplicate = await page.evaluate(
    ({ agentId, sessionId, messageId, prompt, backend }) =>
      new Promise<{ id: string; status: string }>((resolve, reject) => {
        const socket = new WebSocket(
          `${backend.replace('http:', 'ws:')}/api/ws?agent=${agentId}&purpose_revision=1&token=agent-native-local-e2e-only`
        )
        const timer = setTimeout(() => {
          socket.close()
          reject(new Error('Native retry timed out'))
        }, 10000)
        socket.onopen = () =>
          socket.send(JSON.stringify({ id: 'resume', method: 'session.resume', params: { session_id: sessionId } }))
        socket.onmessage = event => {
          const frame = JSON.parse(String(event.data))
          if (frame.id === 'resume') {
            if (frame.error) {
              clearTimeout(timer)
              socket.close()
              reject(new Error(frame.error.message))
              return
            }
            socket.send(
              JSON.stringify({
                id: 'retry',
                method: 'prompt.submit',
                params: {
                  session_id: frame.result.session_id,
                  client_message_id: messageId,
                  text: prompt
                }
              })
            )
          }
          if (frame.id === 'retry') {
            clearTimeout(timer)
            socket.close()
            if (frame.error) reject(new Error(frame.error.message))
            else resolve(frame.result.receipt)
          }
        }
      }),
    { agentId: agent.id, sessionId: storedSession, messageId, prompt, backend }
  )
  expect(duplicate).toMatchObject({ id: messageId, status: 'complete' })

  await page.locator('.xterm-helper-textarea').focus()
  await page.keyboard.type(newerDraft)
  await expect.poll(async () => (await delivery()).composer?.draft?.input).toBe(newerDraft)
  const expired = await request.post(`${backend}/__e2e__/expire-managed-renderer`, {
    headers,
    data: { agent_id: agent.id, attach_token: attach }
  })
  expect(await expired.json()).toEqual({ expired: 1 })
  terminalOutput = ''
  await page.reload()
  await expect(page.locator('.hermes-chat-xterm-host .xterm-screen')).toBeVisible()
  await expect.poll(() => terminalOutput, { timeout: 30000 }).toContain(newerDraft)
  // Ink can restore spaces through cursor motion rather than literal bytes.
  // Exact content is checked against the native persisted transcript below.
  await expect
    .poll(() => stripVTControlCharacters(terminalOutput).replace(/\s+/g, ''))
    .toContain(`My purpose: ${agent.purpose}`.replace(/\s+/g, ''))
  expect((await delivery()).composer.pending).toBeNull()
  const history = await (await request.get(`${backend}/api/sessions/${storedSession}/messages`, { headers })).json()
  expect(
    history.messages
      .filter((m: { role: string }) => ['user', 'assistant'].includes(m.role))
      .map((m: { content: string }) => m.content)
  ).toEqual([prompt, `My purpose: ${agent.purpose}`])
  const evidence = await (await request.get(`${backend}/__e2e__/native-chat-evidence`, { headers })).json()
  expect(evidence.model_requests.filter((r: { last_user: string }) => r.last_user === prompt)).toHaveLength(1)
  await demoCheckpoint(page, test.info(), {
    title: 'A lost acknowledgement does not duplicate a reply',
    expected: 'Reconcile the completed message and keep a newer unsent draft after renderer restart.',
    proof: 'The original reply and newerUnsentDraftAckQ9 are restored. Retrying the same message ID returned its completed receipt; exactly one model request and one exchange were saved.',
    focus: page.locator('.hermes-chat-xterm-host .xterm-screen'),
  })
})
