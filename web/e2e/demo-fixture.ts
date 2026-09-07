import { test as base, expect, type Locator, type Page, type TestInfo } from '@playwright/test'
import { writeFile } from 'node:fs/promises'

const enabled = process.env.AN_E2E_DEMO === '1'
const holdMs = 5000
const annotationId = 'agent-native-e2e-demo-annotation'

interface DemoCheckpointOptions {
  title: string
  expected: string
  /** Observed facts whose assertions have already passed. */
  proof: string
  focus?: Locator
}

interface RecordedPage {
  page: Page
  index: number
  startedAt: number
  video: string | null
}

interface CheckpointRecord {
  title: string
  expected: string
  proof: string
  pageIndex: number
  kind: 'application' | 'api-evidence'
  startedAt: string
  videoStartMs: number
  videoEndMs: number
  screenshotAtMs: number
  screenshot: string
}

interface DemoRecording {
  pages: RecordedPage[]
  checkpoints: CheckpointRecord[]
}

const recordings = new WeakMap<TestInfo, DemoRecording>()

function recordingFor(testInfo: TestInfo): DemoRecording {
  let recording = recordings.get(testInfo)
  if (!recording) {
    recording = { pages: [], checkpoints: [] }
    recordings.set(testInfo, recording)
  }
  return recording
}

function trackPage(recording: DemoRecording, page: Page): RecordedPage {
  let recorded = recording.pages.find(candidate => candidate.page === page)
  if (!recorded) {
    recorded = { page, index: recording.pages.length, startedAt: Date.now(), video: null }
    recording.pages.push(recorded)
  }
  return recorded
}

export const test = base.extend({
  context: async ({ context }, runTest, testInfo) => {
    if (!enabled) {
      await runTest(context)
      return
    }
    const recording = recordingFor(testInfo)
    const onPage = (page: Page) => { trackPage(recording, page) }
    context.pages().forEach(onPage)
    context.on('page', onPage)
    try {
      await runTest(context)
    } finally {
      context.off('page', onPage)
      for (const recorded of recording.pages) {
        recorded.video = await recorded.page.video()?.path() ?? null
      }
      const manifest = {
        schemaVersion: 1,
        title: testInfo.title,
        titlePath: testInfo.titlePath,
        file: testInfo.file,
        line: testInfo.line,
        project: testInfo.project.name,
        statusAtRecordingTeardown: testInfo.status,
        expectedStatus: testInfo.expectedStatus,
        note: 'Checkpoint captions annotate assertions already passed. The Playwright result is authoritative for final test status. Video offsets are measured from the page-created event.',
        viewport: { width: 1600, height: 1000 },
        pages: recording.pages.map(({ index, startedAt, video }) => ({ index, startedAt: new Date(startedAt).toISOString(), video })),
        checkpoints: recording.checkpoints,
      }
      const path = testInfo.outputPath('demo-manifest.json')
      await writeFile(path, `${JSON.stringify(manifest, null, 2)}\n`)
      await testInfo.attach('demo-manifest', { path, contentType: 'application/json' })
    }
  },
})

export { expect }

/** Presentation only: call after the product assertions, never instead of them. */
export async function demoCheckpoint(page: Page, testInfo: TestInfo, options: DemoCheckpointOptions): Promise<void> {
  if (!enabled) return
  if (testInfo.errors.length > 0) {
    throw new Error('Cannot present a verified demo checkpoint after a failed assertion.')
  }
  // Presentation time is not part of the product's timing contract.
  if (testInfo.timeout > 0) testInfo.setTimeout(testInfo.timeout + holdMs + 3000)
  const recording = recordingFor(testInfo)
  const recorded = trackPage(recording, page)
  const apiEvidence = page.url() === 'about:blank'
  let focusBox = null
  if (options.focus) {
    await options.focus.evaluate(element => element.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'instant' }))
    focusBox = await options.focus.boundingBox()
  }
  const startedAt = Date.now()
  const screenshot = testInfo.outputPath(`demo-checkpoint-${String(recording.checkpoints.length + 1).padStart(2, '0')}.png`)
  try {
    await page.evaluate(({ id, title, expected, proof, focus, api }) => {
      document.getElementById(id)?.remove()
      const host = document.createElement('div')
      host.id = id
      host.setAttribute('aria-hidden', 'true')
      host.style.cssText = 'position:fixed;inset:0;z-index:2147483647;pointer-events:none;'
      // A closed shadow keeps test annotations out of application text locators.
      const shadow = host.attachShadow({ mode: 'closed' })
      const style = document.createElement('style')
      style.textContent = `
        * { box-sizing: border-box; }
        .card { position: absolute; left: 28px; right: 28px; bottom: 24px;
          max-width: 1280px; margin: 0 auto; padding: 22px 28px;
          font-family: Arial, sans-serif; color: #f8fafc; background: rgba(13,22,36,.98);
          border: 1px solid #5eead4; border-radius: 14px; box-shadow: 0 10px 48px #0008; }
        .tag { font-size: 14px; font-weight: 700; color: #5eead4;
          text-transform: uppercase; letter-spacing: .13em; margin-bottom: 9px; }
        h2 { margin: 0 0 13px; font-size: 27px; line-height: 1.15; }
        .row { display: grid; grid-template-columns: 106px 1fr; gap: 16px;
          font-size: 18px; line-height: 1.4; margin-top: 7px; }
        .label { color: #a5b4c8; font-weight: 700; }
        .verified { color: #a7f3d0; }
        .footer { color: #91a0b6; font-size: 13px; margin-top: 14px; }
        .api { position: absolute; inset: 0; background: #101827; }
        .api .card { top: 50%; bottom: auto; transform: translateY(-50%); max-width: 1120px; padding: 44px; }
        .focus { position: absolute; border: 3px solid #fbbf24;
          border-radius: 7px; box-shadow: 0 0 0 3px #10182799; }
      `
      shadow.append(style)
      const surface = document.createElement('div')
      if (api) surface.className = 'api'
      if (focus && !api) {
        const highlight = document.createElement('div')
        highlight.className = 'focus'
        highlight.style.left = `${Math.max(3, focus.x - 5)}px`
        highlight.style.top = `${Math.max(3, focus.y - 5)}px`
        highlight.style.width = `${Math.min(innerWidth - Math.max(3, focus.x - 5) - 3, focus.width + 10)}px`
        highlight.style.height = `${Math.min(innerHeight - Math.max(3, focus.y - 5) - 3, focus.height + 10)}px`
        surface.append(highlight)
      }
      const card = document.createElement('section')
      card.className = 'card'
      if (focus && !api && focus.y + focus.height / 2 > innerHeight / 2) {
        card.style.top = '24px'
        card.style.bottom = 'auto'
      }
      const tag = document.createElement('div')
      tag.className = 'tag'
      tag.textContent = api ? 'Test annotation · API evidence · no application screen' : 'Test annotation · verified checkpoint'
      const heading = document.createElement('h2')
      heading.textContent = title
      card.append(tag, heading)
      for (const [label, value] of [['Expected', expected], ['Verified', proof]]) {
        const row = document.createElement('div')
        row.className = 'row'
        const key = document.createElement('div')
        key.className = 'label'
        key.textContent = label
        const text = document.createElement('div')
        if (label === 'Verified') text.className = 'verified'
        text.textContent = value
        row.append(key, text)
        card.append(row)
      }
      const footer = document.createElement('div')
      footer.className = 'footer'
      footer.textContent = 'Assertions passed before this checkpoint. Framework and storage are real; model and Plane are isolated HTTP fixtures.'
      card.append(footer)
      surface.append(card)
      shadow.append(surface)
      document.body.append(host)
    }, { id: annotationId, title: options.title, expected: options.expected, proof: options.proof, focus: focusBox, api: apiEvidence })
    await page.screenshot({ path: screenshot, animations: 'disabled' })
    const screenshotAtMs = Date.now() - recorded.startedAt
    await testInfo.attach(options.title, { path: screenshot, contentType: 'image/png' })
    // Deliberate, opt-in human viewing time, after all product assertions.
    await page.waitForTimeout(holdMs)
    recording.checkpoints.push({
      title: options.title,
      expected: options.expected,
      proof: options.proof,
      pageIndex: recorded.index,
      kind: apiEvidence ? 'api-evidence' : 'application',
      startedAt: new Date(startedAt).toISOString(),
      videoStartMs: startedAt - recorded.startedAt,
      videoEndMs: Date.now() - recorded.startedAt,
      screenshotAtMs,
      screenshot,
    })
  } finally {
    if (!page.isClosed()) await page.evaluate(id => document.getElementById(id)?.remove(), annotationId)
  }
}
