import { useEffect, useRef } from 'react'

import { introMsg, toTranscriptMessages } from '../domain/messages.js'
import type { GatewayClient } from '../gatewayClient.js'
import type { ManagedMessageReceipt, SessionResumeResponse } from '../gatewayTypes.js'
import { managedChatState } from '../lib/managedChatState.js'
import type { Msg } from '../types.js'

import type { ComposerActions, StateSetter } from './interfaces.js'
import { turnController } from './turnController.js'
import { getUiState, patchUiState } from './uiStore.js'

/** Reconcile a saved native submission; this hook never sends a model prompt. */
export function useManagedChatRecovery(
  gw: GatewayClient,
  sid: string | null,
  actions: ComposerActions,
  setHistory: StateSetter<Msg[]>,
  sys: (text: string) => void
) {
  const callbacks = useRef({ actions, setHistory, sys })
  callbacks.current = { actions, setHistory, sys }
  useEffect(() => {
    const state = managedChatState

    if (!state || !sid) {
      return
    }

    let active = true
    let timer: ReturnType<typeof setTimeout> | undefined
    let announced = ''

    const restore = (id: string) => {
      if (state.restorePendingDraft(id)) {
        callbacks.current.actions.restoreDraft(state.getDraft())
      }
    }

    const clearRecovered = (id: string) => {
      if (state.clearRecoveredDraft(id)) {
        callbacks.current.actions.restoreDraft(state.getDraft())
      }
    }

    const notice = (key: string, text: string) => {
      if (announced !== key) {
        callbacks.current.sys(text)
      }

      announced = key
    }

    const check = async () => {
      try {
        if (state.error) {
          notice('storage', `Conversation draft storage is unavailable: ${state.error.message}. Sending is disabled.`)

          return
        }

        const pending = state.getPending()

        if (!pending || !getUiState().info?.managed_agent) {
          return
        }

        const result = await gw.request<{ receipt: ManagedMessageReceipt | null }>('prompt.receipt', {
          session_id: sid,
          client_message_id: pending.id
        })

        if (!active || state.getPending()?.id !== pending.id) {
          return
        }

        const receipt = result.receipt

        if (!receipt) {
          restore(pending.id)
          patchUiState({ busy: false, status: 'message not received' })
          notice(pending.id + ':missing', 'Your saved message has not been received. Retry that same message before sending another.')

          return
        }

        if (receipt.id !== pending.id) {
          throw new Error('Message receipt identity mismatch')
        }

        if (receipt.status === 'complete') {
          const history = await gw.request<Pick<SessionResumeResponse, 'messages'>>('session.history', {
            session_id: sid
          })

          if (!active || state.getPending()?.id !== pending.id) {
            return
          }

          if (!history.messages?.length) {
            throw new Error('Completed message history is not available')
          }

          const info = getUiState().info
          const messages = toTranscriptMessages(history.messages)
          clearRecovered(receipt.id)
          state.receipt(receipt.id, receipt.status)
          callbacks.current.setHistory(info ? [introMsg(info), ...messages] : messages)
          turnController.idle()
          patchUiState({ busy: false, status: 'ready' })

          return
        }

        state.receipt(receipt.id, receipt.status)

        if (receipt.status === 'accepted' || receipt.status === 'running') {
          clearRecovered(receipt.id)
          patchUiState({ busy: true, status: 'waiting for reply…' })
        } else {
          restore(pending.id)
          patchUiState({ busy: false, status: receipt.status === 'error' ? 'reply failed' : 'delivery uncertain' })
          notice(
            pending.id + ':' + receipt.status,
            receipt.status === 'error'
              ? `The previous attempt failed. Its text is retained; you can edit your draft or retry explicitly. ${receipt.reason ?? ''}`
              : `The previous attempt has an uncertain outcome. Check its saved history. Replace the composer text with /acknowledge to close this uncertain attempt and write a new message; it will not resend the old one. ${receipt.reason ?? ''}`
          )
        }
      } catch (error) {
        if (active && state.getPending()) {
          notice(
            'connection',
            `Could not confirm message delivery; your saved message is retained. ${error instanceof Error ? error.message : String(error)}`
          )
        }
      } finally {
        if (active) {
          timer = setTimeout(() => {
            void check()
          }, 1000)
        }
      }
    }

    void check()

    return () => {
      active = false
      clearTimeout(timer)
    }
  }, [gw, sid])
}
