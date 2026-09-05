import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  workers: 1,
  use: { baseURL: 'http://127.0.0.1:19220', trace: 'retain-on-failure', launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH } },
  webServer: [
    { command: '../.venv/bin/python e2e/backend.py', url: 'http://127.0.0.1:19219/api/health', timeout: 60000, reuseExistingServer: false },
    { command: 'npm run dev -- --host 127.0.0.1 --port 19220 --strictPort', url: 'http://127.0.0.1:19220', env: { HERMES_DASHBOARD_URL: 'http://127.0.0.1:19219' }, timeout: 60000, reuseExistingServer: false },
  ],
});
