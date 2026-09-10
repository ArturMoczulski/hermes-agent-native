# Output feedback and demonstrations

## Purpose

An output is a versioned artifact, not a dead end. An owner must be able to respond
to the exact version they are viewing, and an agent must be able to communicate
demonstrable work in a form that makes review easy.

## Exact-output feedback

Every readable saved-output version has **Give feedback** in its reader and compact
output card. The form identifies the output title, version and linked work item,
then accepts bounded owner feedback. It offers two meanings:

- **General feedback** supplies direction without blocking autonomous work.
- **Request revision** supplies actionable feedback for that output. It does not by
  itself create a required approval gate.

The feedback record binds the agent ID, output ID, output version, purpose revision,
and observed work/result context. It is visible in the output history and available
to the agent through trusted managed context. Applicable actionable feedback wakes
enabled automatic work. Feedback for a retired, removed or superseded purpose stays
in history but cannot be applied to new work.

Required output review remains a distinct operation. A required review has explicit
acceptance criteria and may block dependent work; ordinary feedback never silently
becomes one.

## Narrated demonstration outputs

Agents should prefer a concise narrated video when the output is interactive,
visual, time-based or otherwise clearer when seen in use. Examples include a
playable game increment, a product feature, music production, an animation or a
workflow. A video is not required for planning-only, text-first or nonvisual work;
agents publish the clearest durable evidence for the result.

A demonstration contains real application scenes that visibly match the narration.
It does not present static screenshots as if interaction occurred. Each scene has a
short speech-oriented script, its own narration audio, captions timed to the rendered
audio, and a known relationship to an output/work item. Sensitive or irrelevant
information must be removed before capture.

The foundational narrated-demo skill provides the operating procedure. Its default
capture target is a 1440x900 CSS-pixel MacBook-style viewport, exported as 1920x1200
at 30 fps. An agent may select a different format when the result needs it and records
why. It uses local speech synthesis where available, with dependencies and model
assets held outside the repository. It assembles scenes with reproducible local tools,
verifies playback, visual transitions, captions and intelligible audio, then publishes
the final video through the immutable media-output contract.

Published videos retain MIME type, size, checksum, producing run and linked work
context. The agent view provides an inline player, full-screen playback, download and
exact-output feedback. Source scenes, scripts and narration assets are work evidence
when safe to retain; they do not replace the published output.

## Preference and authority

The preference for demonstrations helps agents communicate results; it does not grant
permission to capture screens, access applications, use external services or install
software. The agent uses only its granted workspace, computer-use authority and
media tools. When those are unavailable, it can publish another valid output and
report the missing capability instead of fabricating a video.
