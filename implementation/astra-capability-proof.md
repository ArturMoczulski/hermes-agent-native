# Astra capability baseline

The first implementation increment validates the existing Hermes screenshot
pipeline before introducing persistent-agent orchestration.

## Reproduce the offline check

From the fork root, after `uv sync --frozen --extra dev --extra web`:

```sh
scripts/run_tests.sh tests/tools/test_astra_capture_pipeline.py
```

The four cases cover OpenAI and Codex provider identifiers with vision and SOM
captures. They use real configuration parsing, screenshot packaging, active-model
filtering and Responses encoding. A generated PNG replaces the physical desktop.
They assert that the original image bytes reach the encoded request, tool calls
remain paired, and SOM labels survive. Tests use the suite's isolated Hermes home.

The test configuration explicitly declares `model.supports_vision: true` for
`gpt-6-astra`. This verifies that configuration, not automatic model discovery.
No credentials, external service, model request or physical desktop is exercised.

On 2026-09-05 all four cases passed on inherited Hermes behavior. No runtime
change was needed, and no red-green implementation claim is made for this
characterization check. The two existing computer-use capture/routing suites
also passed (25 tests).

## Live acceptance still required

1. Owner chooses the OpenAI API or ChatGPT/Codex connection and configures it
   through Hermes authentication. Do not copy app credentials into the repository.
2. Use an isolated Hermes profile with native Astra vision configured. Check
   `hermes computer-use doctor`; install/configure its driver and host permissions
   if required. Never treat offline tests as evidence those permissions exist.
3. Give Hermes a disposable local browser form task: enter a specified value,
   save it, reopen it, and report the saved result using a fresh screenshot.
4. Independently verify the stored value with Playwright, record the selected
   model and tool path, and retain sanitized evidence. An agent's claim alone is
   not success. Failure should identify authentication, capture, action execution,
   image routing or task performance separately.

This live acceptance harness is not implemented yet. Neither unattended work nor
the agent-native control center is running. Preserve this boundary when reporting
progress: serialized image support does not establish parity with the Codex app.

## Live evidence — 2026-09-05

Owner chose ChatGPT Pro subscription authentication. Separate Hermes profile:
`/Users/arturmoczulski/.hermes-agent-native`; credentials are outside Git.

- Astra inference via `openai-codex` passed: `ASTRA_CONNECTION_OK`, session
  `20260905_194948_4ea567`.
- Installed cua-driver 0.23.2; after owner granted macOS permissions, Hermes
  doctor passed with active MCP session, Accessibility and Screen Recording.
- Screenshot reading passed in TextEdit, session `20260905_195537_588867`.
  The model returned the fixture code without it being included in the prompt.
  This establishes real screenshot reading through Hermes, not app-tool parity.
- An edit/save attempt stalled after capture and was interrupted; direct file
  inspection found no change. Suspected one-shot modal approval wait; this needs
  deterministic reproduction before fixing. Editing is not verified.
- No browser/Playwright acceptance has run yet.
