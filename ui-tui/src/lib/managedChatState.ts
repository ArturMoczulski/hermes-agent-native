import { randomUUID } from 'node:crypto'
import {
  closeSync,
  constants,
  fstatSync,
  fsyncSync,
  lstatSync,
  openSync,
  readFileSync,
  renameSync,
  unlinkSync,
  writeFileSync
} from 'node:fs'
import { dirname } from 'node:path'

import type { ComposerToken } from '../app/interfaces.js'

export interface ManagedChatDraft {
  input: string
  inputBuf: string[]
  tokens: ComposerToken[]
}

export type ManagedChatStatus = 'pending' | 'accepted' | 'running' | 'complete' | 'error' | 'unknown'
export interface ManagedChatPending {
  id: string
  text: string
  status: ManagedChatStatus
}

interface Snapshot {
  version: 1
  draft: ManagedChatDraft
  pending: ManagedChatPending | null
  recoveredDraftId?: string | null
}

// Match the managed gateway's Python len(text) limit (Unicode codepoints).
export const MAX_MANAGED_MESSAGE_CODE_POINTS = 32000
const MAX_BYTES = 8 * 1024 * 1024
const statuses = new Set<ManagedChatStatus>(['pending', 'accepted', 'running', 'complete', 'error', 'unknown'])
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const emptySnapshot = (): Snapshot => ({ version: 1, draft: { input: '', inputBuf: [], tokens: [] }, pending: null })
const asError = (error: unknown) => (error instanceof Error ? error : new Error(String(error)))
const missing = (error: unknown) => (error as NodeJS.ErrnoException)?.code === 'ENOENT'

const record = (value: unknown): value is Record<string, unknown> =>
  !!value && typeof value === 'object' && !Array.isArray(value)

function validate(value: unknown): asserts value is Snapshot {
  if (!record(value) || value.version !== 1 || !record(value.draft)) {
    throw new Error('Invalid managed chat state')
  }

  const draft = value.draft

  if (
    typeof draft.input !== 'string' ||
    !Array.isArray(draft.inputBuf) ||
    !draft.inputBuf.every(v => typeof v === 'string') ||
    !Array.isArray(draft.tokens)
  ) {
    throw new Error('Invalid managed chat draft')
  }

  for (const token of draft.tokens) {
    if (
      !record(token) ||
      typeof token.label !== 'string' ||
      (token.path !== undefined && typeof token.path !== 'string')
    ) {
      throw new Error('Invalid managed chat paste')
    }

    if (token.kind === 'paste' && typeof token.text === 'string') {
      continue
    }

    if (token.kind === 'image' && Number.isInteger(token.index) && typeof token.path === 'string') {
      continue
    }

    throw new Error('Invalid managed chat paste')
  }

  const pending = value.pending

  if (
    pending !== null &&
    (!record(pending) ||
      typeof pending.id !== 'string' ||
      !uuid.test(pending.id) ||
      typeof pending.text !== 'string' ||
      !statuses.has(pending.status as ManagedChatStatus))
  ) {
    throw new Error('Invalid managed chat pending message')
  }

  if (value.recoveredDraftId !== undefined && value.recoveredDraftId !== null &&
      (typeof value.recoveredDraftId !== 'string' || !uuid.test(value.recoveredDraftId))) {
    throw new Error('Invalid managed chat recovery ownership')
  }
}

/** Private renderer state; the host selects a separate path for each bound recipient/revision/browser. */
export class ManagedChatState {
  error: Error | null = null
  private loadError: Error | null = null
  private snapshot = emptySnapshot()
  private diskText: string | null = null

  constructor(private readonly file: string) {
    try {
      this.diskText = this.readDisk()

      if (this.diskText !== null) {
        const loaded: unknown = JSON.parse(this.diskText)
        validate(loaded)
        this.snapshot = loaded
      }
    } catch (error) {
      this.loadError = this.error = asError(error)
    }
  }

  getDraft(): ManagedChatDraft {
    return structuredClone(this.snapshot.draft)
  }

  getPending(): ManagedChatPending | null {
    return structuredClone(this.snapshot.pending)
  }

  saveDraft(draft: ManagedChatDraft): void {
    // Even an identical explicit edit belongs to the human, not recovery cleanup.
    this.commit({ ...this.snapshot, draft: structuredClone(draft), recoveredDraftId: null })
  }

  restorePendingDraft(id: string): boolean {
    this.assertLoaded()
    const { draft, pending } = this.snapshot

    if (pending?.id !== id || draft.input !== '' || draft.inputBuf.length || draft.tokens.length) {
      return false
    }

    this.commit({ ...this.snapshot, draft: { input: pending.text, inputBuf: [], tokens: [] }, recoveredDraftId: id })

    return true
  }

  clearRecoveredDraft(id: string): boolean {
    this.assertLoaded()

    if (this.snapshot.recoveredDraftId !== id) {
      return false
    }

    // Receipt completion may already have cleared pending; ownership survives it.
    this.commit({ ...this.snapshot, draft: { input: '', inputBuf: [], tokens: [] }, recoveredDraftId: null })

    return true
  }

  prepare(text: string): ManagedChatPending {
    this.assertLoaded()

    if (!text.trim()) {
      throw new Error('Message must contain text')
    }

    if (Array.from(text).length > MAX_MANAGED_MESSAGE_CODE_POINTS) {
      throw new Error(`Message must contain at most ${MAX_MANAGED_MESSAGE_CODE_POINTS} characters`)
    }

    const pending = this.snapshot.pending

    if (pending && pending.status !== 'error' && pending.status !== 'complete') {
      if (pending.text !== text) {
        throw new Error('Resolve the previous message before sending another')
      }

      if (pending.status === 'accepted' || pending.status === 'running') {
        throw new Error('Previous message is already accepted')
      }

      // Transfer the displayed draft in the same durable write as its receipt.
      // Retrying an uncertain submission keeps exactly the same identity.
      this.commit({ ...this.snapshot, draft: { input: '', inputBuf: [], tokens: [] }, recoveredDraftId: null })

      return structuredClone(pending)
    }

    const next: ManagedChatPending = { id: randomUUID(), text, status: 'pending' }
    this.commit({ ...this.snapshot, pending: next, draft: { input: '', inputBuf: [], tokens: [] }, recoveredDraftId: null })

    return structuredClone(next)
  }

  receipt(id: string, status: ManagedChatStatus): boolean {
    this.assertLoaded()

    if (!statuses.has(status)) {
      throw new Error('Invalid managed chat receipt status')
    }

    if (this.snapshot.pending?.id !== id) {
      return false
    }

    if (this.snapshot.pending.status === status) {
      // Polling an unchanged receipt verifies storage without replacing/fsyncing it.
      try {
        if (this.readDisk() !== this.diskText) {
          throw new Error('Managed chat state changed on disk; reopen this conversation')
        }

        this.error = null

        return true
      } catch (error) {
        this.error = asError(error)
        throw this.error
      }
    }

    this.commit({ ...this.snapshot, pending: status === 'complete' ? null : { ...this.snapshot.pending, status } })

    return true
  }

  acknowledgeUnknown(id: string): boolean {
    this.assertLoaded()

    if (this.snapshot.pending?.id !== id || this.snapshot.pending.status !== 'unknown') {
      return false
    }

    this.commit({ ...this.snapshot, pending: null })

    return true
  }

  private assertLoaded(): void {
    if (this.loadError) {
      throw this.loadError
    }
  }

  private readDisk(): string | null {
    const parent = lstatSync(dirname(this.file))

    if (!parent.isDirectory() || parent.isSymbolicLink()) {
      throw new Error('Managed chat state directory must not be a symlink')
    }

    try {
      const entry = lstatSync(this.file)

      if (!entry.isFile() || entry.isSymbolicLink()) {
        throw new Error('Managed chat state must be a regular file')
      }
    } catch (error) {
      if (missing(error)) {
        return null
      }

      throw error
    }

    const fd = openSync(this.file, constants.O_RDONLY | constants.O_NOFOLLOW)

    try {
      const entry = fstatSync(fd)

      if (!entry.isFile() || entry.size > MAX_BYTES) {
        throw new Error('Managed chat state exceeds its storage limit')
      }

      return readFileSync(fd, 'utf8')
    } finally {
      closeSync(fd)
    }
  }

  private commit(next: Snapshot): void {
    this.assertLoaded()
    let temporary: string | null = null
    let fd: number | null = null

    try {
      validate(next)
      const serialized = JSON.stringify(next)

      if (Buffer.byteLength(serialized, 'utf8') > MAX_BYTES) {
        throw new Error('Managed chat state exceeds its storage limit')
      }

      // Do not overwrite a changed/corrupt file or a second renderer's newer draft.
      if (this.readDisk() !== this.diskText) {
        throw new Error('Managed chat state changed on disk; reopen this conversation')
      }

      temporary = `${this.file}.${randomUUID()}.tmp`
      fd = openSync(temporary, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | constants.O_NOFOLLOW, 0o600)
      writeFileSync(fd, serialized, 'utf8')
      fsyncSync(fd)
      closeSync(fd)
      fd = null

      if (this.readDisk() !== this.diskText) {
        throw new Error('Managed chat state changed on disk; reopen this conversation')
      }

      renameSync(temporary, this.file)
      temporary = null
      this.snapshot = structuredClone(next)
      this.diskText = serialized
      this.error = null
    } catch (error) {
      this.error = asError(error)
      throw this.error
    } finally {
      if (fd !== null) {
        closeSync(fd)
      }

      if (temporary !== null) {
        try {
          unlinkSync(temporary)
        } catch {
          /* Preserve the original write failure. */
        }
      }
    }
  }
}

export const managedChatState: ManagedChatState | null = process.env.HERMES_TUI_CHAT_STATE
  ? new ManagedChatState(process.env.HERMES_TUI_CHAT_STATE)
  : null
