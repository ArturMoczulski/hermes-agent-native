import { EventEmitter } from 'node:events'
import { PassThrough } from 'node:stream'

import { renderSync } from '@hermes/ink'
import React, { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'

import { TextInput } from '../components/textInput.js'

class FakeInput extends EventEmitter {
  chunks: string[] = []
  isRaw = false
  isTTY = true
  readableLength = 0

  read() {
    const next = this.chunks.shift() ?? null
    this.readableLength = this.chunks.length

    return next
  }

  ref = vi.fn()

  send(...chunks: string[]) {
    this.chunks.push(...chunks)
    this.readableLength = this.chunks.length
    this.emit('readable')
  }

  setEncoding = vi.fn()

  setRawMode = vi.fn((enabled: boolean) => {
    this.isRaw = enabled
  })

  unref = vi.fn()
}

const settle = (ms = 0) => new Promise(resolve => setTimeout(resolve, ms))

function makeStreams() {
  const stdin = new FakeInput()
  const stdout = new PassThrough()
  const stderr = new PassThrough()

  Object.assign(stdout, { columns: 80, isTTY: false, rows: 24 })
  Object.assign(stderr, { columns: 80, isTTY: false, rows: 24 })

  return { stderr, stdin, stdout }
}

describe('TextInput submit clearing', () => {
  it('accepts the parent clear after a Korean IME commit immediately followed by Enter', async () => {
    const streams = makeStreams()
    const changes: string[] = []
    const submits: string[] = []

    function Harness() {
      const [value, setValue] = useState('')

      return (
        <TextInput
          columns={80}
          onChange={next => {
            changes.push(next)
            setValue(next)
          }}
          onSubmit={text => {
            submits.push(text)
            setValue('')
          }}
          value={value}
        />
      )
    }

    const instance = renderSync(React.createElement(Harness), {
      patchConsole: false,
      stderr: streams.stderr as NodeJS.WriteStream,
      stdin: streams.stdin as unknown as NodeJS.ReadStream,
      stdout: streams.stdout as NodeJS.WriteStream
    })

    await settle()

    const prefix = '한글을 사용하면 마지막 문자가 남아있는 버그가 있어 리포트해'
    const finalSyllable = '줘'
    const full = prefix + finalSyllable

    streams.stdin.send(prefix)
    await settle(25)

    streams.stdin.send(finalSyllable, '\r')
    await settle(25)

    streams.stdin.send('x')
    await settle(25)

    instance.unmount()
    instance.cleanup()

    expect(submits).toEqual([full])
    expect(changes.at(-1)).toBe('x')
    expect(changes).not.toContain(`${full}x`)
  })
})


describe('TextInput terminal redraw', () => {
  it.each(['', 'A retained draft'])('does not insert Ctrl+L into draft %j', async draft => {
    const streams = makeStreams()
    const changes: string[] = []
    const submits: string[] = []

    function Harness() {
      const [value, setValue] = useState(draft)

      return (
        <TextInput
          columns={80}
          onChange={next => {
            changes.push(next)
            setValue(next)
          }}
          onSubmit={text => submits.push(text)}
          value={value}
        />
      )
    }

    const instance = renderSync(React.createElement(Harness), {
      patchConsole: false,
      stderr: streams.stderr as NodeJS.WriteStream,
      stdin: streams.stdin as unknown as NodeJS.ReadStream,
      stdout: streams.stdout as NodeJS.WriteStream
    })

    try {
      await settle()
      // The dashboard sends this exact byte to repaint a reattached PTY.
      streams.stdin.send('\x0c')
      await settle(25)
      expect(changes).toEqual([])

      streams.stdin.send('l')
      await settle(25)
      streams.stdin.send('\r')
      await settle(25)
      expect(submits).toEqual([draft + 'l'])
    } finally {
      instance.unmount()
      instance.cleanup()
    }
  })
})
