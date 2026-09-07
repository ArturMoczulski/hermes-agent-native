import { defineConfig } from '@playwright/test'
import { resolve } from 'node:path'
import base from './playwright.config'

// A separate destination keeps a selected pilot from replacing the full recording.
const outputDir = resolve(import.meta.dirname, process.env.AN_E2E_DEMO_OUTPUT_DIR ?? './test-results/e2e-demo/default')

export default defineConfig(base, {
  name: 'framework-demo',
  workers: 1,
  retries: 0,
  outputDir,
  reporter: [['list'], ['json', { outputFile: resolve(outputDir, 'report.json') }]],
  use: {
    ...base.use,
    viewport: { width: 1600, height: 1000 },
    video: { mode: 'on', size: { width: 1600, height: 1000 } },
  },
})
