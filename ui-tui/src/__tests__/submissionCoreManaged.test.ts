import { mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { SubmitPromptDeps } from '../app/submissionCore.js'
import type * as SubmissionCoreModule from '../app/submissionCore.js'
import type * as UiStoreModule from '../app/uiStore.js'
import type { GatewayClient } from '../gatewayClient.js'
import type { ManagedChatState } from '../lib/managedChatState.js'

let directory = ''
let core: typeof SubmissionCoreModule
let ui: typeof UiStoreModule
let storage: ManagedChatState

beforeEach(async () => {
  vi.resetModules()
  directory = mkdtempSync(join(tmpdir(), 'managed-submit-race-'))
  vi.stubEnv('HERMES_TUI_CHAT_STATE', join(directory, 'composer.json'))
  core = await import('../app/submissionCore.js')
  ui = await import('../app/uiStore.js')
  storage = (await import('../lib/managedChatState.js')).managedChatState!
  ui.resetUiState()
  ui.patchUiState({ sid: 'native-session-a' })
})

afterEach(() => {
  vi.unstubAllEnvs()
  rmSync(directory, { recursive: true, force: true })
})

function start() {
  let resolve!: (value: unknown) => void
  let reject!: (error: Error) => void

  const response = new Promise((yes, no) => {
    resolve = yes
    reject = no
  })

  // External transport response is delayed; state/outbox/store are real.
  const gw = { request: () => response } as unknown as GatewayClient

  const deps: SubmitPromptDeps = {
    gw,
    appendMessage: vi.fn(),
    enqueue: vi.fn(),
    expand: v => v,
    setLastUserMsg: vi.fn(),
    sys: vi.fn()
  }

  const pending = storage.prepare('First owner message')
  core.submitPrompt(pending.text, deps, true, undefined, { skipDetectDrop: true, clientMessageId: pending.id })

  return { pending, deps, resolve, reject }
}

const settle = async () => {
  await Promise.resolve()
  await Promise.resolve()
  await Promise.resolve()
}

describe('managed submission late transport responses', () => {
  it('an old timeout cannot mark a newer accepted message idle', async () => {
    const first = start()
    storage.receipt(first.pending.id, 'complete')
    const second = storage.prepare('Newer owner message')
    storage.receipt(second.id, 'running')
    storage.saveDraft({ input: 'A still newer draft', inputBuf: [], tokens: [] })
    ui.patchUiState({ busy: true, status: 'newer reply running' })
    first.reject(new Error('first acknowledgement timed out'))
    await settle()
    expect(ui.getUiState()).toMatchObject({ busy: true, status: 'newer reply running' })
    expect(storage.getPending()).toMatchObject({ id: second.id, status: 'running' })
    expect(storage.getDraft().input).toBe('A still newer draft')
    expect(first.deps.sys).not.toHaveBeenCalled()
  })

  it('a late acknowledgement for the previous native session cannot mutate its outbox', async () => {
    const first = start()
    ui.patchUiState({ sid: 'native-session-b', busy: false, status: 'other conversation ready' })
    first.resolve({ status: 'streaming', receipt: { id: first.pending.id, status: 'accepted' } })
    await settle()
    expect(storage.getPending()).toMatchObject({ status: 'pending' })
    expect(ui.getUiState()).toMatchObject({ sid: 'native-session-b', busy: false, status: 'other conversation ready' })
  })

  it('a lost acknowledgement cannot downgrade a receipt-confirmed running attempt', async () => {
    const first = start()
    storage.receipt(first.pending.id, 'running')
    ui.patchUiState({ busy: true, status: 'waiting for reply…' })
    first.reject(new Error('acknowledgement lost'))
    await settle()
    expect(ui.getUiState()).toMatchObject({ busy: true, status: 'waiting for reply…' })
    expect(storage.getPending()).toMatchObject({ id: first.pending.id, status: 'running' })
  })

  it('an older accepted acknowledgement cannot overwrite a reconciled unknown outcome', async () => {
    const first = start()
    storage.receipt(first.pending.id, 'unknown')
    first.resolve({ status: 'streaming', receipt: { id: first.pending.id, status: 'accepted' } })
    await settle()
    expect(storage.getPending()).toMatchObject({ id: first.pending.id, status: 'unknown' })
  })
})
