import { mkdtempSync, readFileSync, renameSync, rmSync, statSync, symlinkSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { ManagedChatState } from '../lib/managedChatState.js'

let home: string
let file: string
const empty = { input: '', inputBuf: [], tokens: [] }

beforeEach(() => {
  home = mkdtempSync(join(tmpdir(), 'managed-chat-state-'))
  file = join(home, 'agent-a-revision-1.json')
})
afterEach(() => rmSync(home, { recursive: true, force: true }))

describe('managed native composer durable state', () => {
  it('restores full draft and immutable pending identity without mixing agent or purpose scopes', () => {
    const draft = {
      input: 'review [[ paste ]]',
      inputBuf: ['first line'],
      tokens: [{ kind: 'paste' as const, label: '[[ paste ]]', text: 'line two\nline three' }]
    }

    const store = new ManagedChatState(file)
    store.saveDraft(draft)
    const pending = store.prepare('first line\nreview line two\nline three')
    store.saveDraft(empty)
    const reopened = new ManagedChatState(file)
    expect(reopened.getDraft()).toEqual(empty)
    expect(reopened.getPending()).toEqual(pending)
    expect(reopened.prepare(pending.text).id).toBe(pending.id)
    expect(reopened.receipt(pending.id, 'unknown')).toBe(true)
    expect(new ManagedChatState(file).prepare(pending.text).id).toBe(pending.id)
    expect(new ManagedChatState(join(home, 'agent-b-revision-1.json')).getDraft()).toEqual(empty)
    expect(new ManagedChatState(join(home, 'agent-a-revision-2.json')).getPending()).toBeNull()
    expect(statSync(file).mode & 0o777).toBe(0o600)

    reopened.saveDraft(draft)
    draft.input = 'outside mutation'
    expect(new ManagedChatState(file).getDraft().input).toBe('review [[ paste ]]')
    const read = reopened.getDraft()
    read.tokens[0]!.label = 'outside mutation'
    expect(reopened.getDraft().tokens[0]!.label).toBe('[[ paste ]]')
  })

  it('keeps newer typing and unresolved sends intact until the matching receipt settles', () => {
    const store = new ManagedChatState(file)
    const first = store.prepare('first message')
    store.saveDraft({ ...empty, input: 'newer unsent typing' })
    expect(() => store.prepare('different message')).toThrow()
    expect(store.receipt('unrelated-id', 'complete')).toBe(false)
    store.receipt(first.id, 'accepted')
    expect(() => store.prepare(first.text)).toThrow()
    store.receipt(first.id, 'running')
    expect(() => store.prepare(first.text)).toThrow()
    expect(store.getDraft().input).toBe('newer unsent typing')
    store.receipt(first.id, 'error')
    const retry = store.prepare(first.text)
    expect(retry.id).not.toBe(first.id)
    expect(new ManagedChatState(file).getPending()?.id).toBe(retry.id)
    expect(store.getDraft()).toEqual(empty)
    store.saveDraft({ ...empty, input: 'newer unsent typing' })
    store.receipt(retry.id, 'complete')
    expect(new ManagedChatState(file).getPending()).toBeNull()
    expect(store.getDraft().input).toBe('newer unsent typing')
  })

  it('atomically transfers the composer into the pending envelope before renderer-side clearing', () => {
    const store = new ManagedChatState(file)
    store.saveDraft({ input: 'review [[ paste ]]', inputBuf: ['first line'],
      tokens: [{ kind: 'paste', label: '[[ paste ]]', text: 'second line' }] })
    const pending = store.prepare('first line\nreview second line')
    const reopened = new ManagedChatState(file)
    expect(reopened.getDraft()).toEqual(empty)
    expect(reopened.getPending()).toEqual(pending)
    expect(reopened.restorePendingDraft(pending.id)).toBe(true)
    expect(reopened.prepare(pending.text).id).toBe(pending.id)
    const afterRetry = new ManagedChatState(file)
    expect(afterRetry.getDraft()).toEqual(empty)
    expect(afterRetry.restorePendingDraft(pending.id)).toBe(true)
    afterRetry.receipt(pending.id, 'complete')
    expect(afterRetry.clearRecoveredDraft(pending.id)).toBe(true)
    expect(new ManagedChatState(file).getDraft()).toEqual(empty)
  })

  it('rejects messages above the gateway codepoint limit before creating a pending receipt', () => {
    const store = new ManagedChatState(file)
    const tooLong = '🐉'.repeat(32001)
    store.saveDraft({ ...empty, input: tooLong })
    const before = readFileSync(file)
    expect(() => store.prepare(tooLong)).toThrow(/32000/)
    expect(store.getPending()).toBeNull()
    expect(readFileSync(file).equals(before)).toBe(true)
    store.saveDraft({ ...empty, input: 'shorter corrected message' })
    expect(store.prepare('shorter corrected message').text).toBe('shorter corrected message')
  })

  it('matches the Python gateway length limit for astral Unicode characters', () => {
    const store = new ManagedChatState(file)
    const allowed = '🐉'.repeat(32000)
    expect(store.prepare(allowed).text).toBe(allowed)
    expect(new ManagedChatState(file).getPending()?.text).toBe(allowed)
  })

  it('acknowledges only the matching unknown attempt without discarding newer draft text', () => {
    const store = new ManagedChatState(file)
    const first = store.prepare('uncertain earlier message')
    store.saveDraft({ ...empty, input: 'new draft must survive' })

    for (const status of ['pending', 'accepted', 'running', 'error'] as const) {
      store.receipt(first.id, status)
      expect(store.acknowledgeUnknown(first.id)).toBe(false)
      expect(store.getPending()?.id).toBe(first.id)
    }

    store.receipt(first.id, 'unknown')
    expect(store.acknowledgeUnknown('different-id')).toBe(false)
    expect(store.acknowledgeUnknown(first.id)).toBe(true)
    expect(new ManagedChatState(file).getPending()).toBeNull()
    expect(store.getDraft().input).toBe('new draft must survive')
    expect(store.prepare('a new explicitly sent message').id).not.toBe(first.id)
    expect(store.acknowledgeUnknown(first.id)).toBe(false)
  })

  it('restores pending text only into an empty draft and clears untouched recovery after reopening', () => {
    const store = new ManagedChatState(file)
    const pending = store.prepare('recovered earlier message')
    expect(store.restorePendingDraft('different-id')).toBe(false)
    expect(store.restorePendingDraft(pending.id)).toBe(true)
    expect(store.getDraft()).toEqual({ ...empty, input: pending.text })
    expect(store.restorePendingDraft(pending.id)).toBe(false)
    expect(store.clearRecoveredDraft('different-id')).toBe(false)
    const reopened = new ManagedChatState(file)
    reopened.receipt(pending.id, 'complete')
    expect(reopened.getPending()).toBeNull()
    expect(reopened.clearRecoveredDraft(pending.id)).toBe(true)
    expect(new ManagedChatState(file).getDraft()).toEqual(empty)
    expect(reopened.clearRecoveredDraft(pending.id)).toBe(false)
  })

  it.each(['newer edited draft', 'recovered earlier message'])(
    'does not erase human-saved draft %j when an earlier recovery is accepted',
    edited => {
      const store = new ManagedChatState(file)
      const pending = store.prepare('recovered earlier message')
      store.saveDraft({ ...empty, inputBuf: ['still typing'] })
      expect(store.restorePendingDraft(pending.id)).toBe(false)
      store.saveDraft(empty)
      expect(store.restorePendingDraft(pending.id)).toBe(true)
      store.saveDraft({ ...empty, input: edited })
      const reopened = new ManagedChatState(file)
      reopened.receipt(pending.id, 'accepted')
      expect(reopened.clearRecoveredDraft(pending.id)).toBe(false)
      expect(new ManagedChatState(file).getDraft().input).toBe(edited)
    }
  )

  it('does not rewrite unchanged receipt state while still refusing changed disk contents', () => {
    const store = new ManagedChatState(file)
    const pending = store.prepare('one message')
    store.receipt(pending.id, 'accepted')
    const before = statSync(file)
    expect(store.receipt(pending.id, 'accepted')).toBe(true)
    const after = statSync(file)
    expect(after.ino).toBe(before.ino)
    expect(after.mtimeMs).toBe(before.mtimeMs)
    writeFileSync(file, 'changed outside this renderer')
    expect(() => store.receipt(pending.id, 'accepted')).toThrow()
    expect(() => store.prepare(pending.text)).toThrow()
    expect(() => store.saveDraft(empty)).toThrow()
    expect(readFileSync(file, 'utf8')).toBe('changed outside this renderer')
  })

  it.each(['corrupt', 'symlink', 'oversized'] as const)(
    'reports %s state without crashing or overwriting it',
    failure => {
      const target = join(home, 'untouched.json')

      if (failure === 'corrupt') {
        writeFileSync(file, '{broken')
      }

      if (failure === 'oversized') {
        writeFileSync(file, 'x'.repeat(8 * 1024 * 1024 + 1))
      }

      if (failure === 'symlink') {
        writeFileSync(target, 'private unrelated text')
        symlinkSync(target, file)
      }

      const previous = readFileSync(file)
      const store = new ManagedChatState(file)
      expect(store.error).toBeInstanceOf(Error)
      expect(store.getDraft()).toEqual(empty)
      expect(() => store.prepare('must not be sent')).toThrow()
      expect(() => store.saveDraft(empty)).toThrow()
      expect(readFileSync(file).equals(previous)).toBe(true)
    }
  )

  it('refuses oversized writes and preserves the last durable state through filesystem failure', () => {
    const store = new ManagedChatState(file)
    store.saveDraft({ ...empty, input: 'saved before failure' })
    const saved = readFileSync(file)
    expect(() => store.saveDraft({ ...empty, input: 'x'.repeat(8 * 1024 * 1024) })).toThrow()
    expect(readFileSync(file).equals(saved)).toBe(true)
    const moved = home + '-temporarily-unavailable'
    renameSync(home, moved)

    try {
      expect(() => store.prepare('cannot durably admit this send')).toThrow()
      expect(store.getPending()).toBeNull()
      expect(store.getDraft().input).toBe('saved before failure')
    } finally {
      renameSync(moved, home)
    }

    expect(readFileSync(file).equals(saved)).toBe(true)
    store.prepare('explicit send after storage recovered')
    expect(store.error).toBeNull()
  })
})
