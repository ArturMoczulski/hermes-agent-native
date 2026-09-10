---
name: narrated-demo
description: Produce a narrated video demonstration of an interactive or visual work output, then publish it as a verified media artifact.
---

# Narrated demonstrations

Use this skill when a result is clearer when the owner can watch it in action: a
playable increment, product feature, visual workflow, music production or animation.
Do not manufacture a video for planning-only or text-first results.

## Prepare the demonstration

Decide the smallest story that proves the output. Capture real application scenes;
when narration describes an action, show that action happening. Prepare a clean state
with useful data and no personal information, unrelated warnings, browser clutter or
clipped controls. Default to a 1440x900 CSS-pixel viewport and a 1920x1200, 30-fps
export unless the output needs another documented format.

Write short speech-oriented narration. One paragraph is one visual idea and one scene.
Keep a scene script, its rendered audio and timed captions together so later revisions
remain auditable.

## Render and assemble

Prefer local speech synthesis. When Kokoro ONNX is available, use its English
`af_heart` voice at 0.98 speed with mono 24-kHz WAV per scene. Keep its environment,
model and voice files outside the repository. If local narration is unavailable, use
an authorized alternative or report the missing capability; do not commit models or
credentials.

Use FFmpeg or an equivalent reproducible local assembler. Match scene duration to the
rendered narration, use brief transitions, keep music well below speech, and normalize
the finished program around -16 LUFS with a -1.5 dBTP ceiling. Export an MP4 with AAC
audio at 48 kHz and 192 kbps unless the output format requires another documented
choice.

## Verify and publish

Inspect the opening, every scene transition, interactive action and closing frame.
Confirm that movement matches the narration, captions match the final script, and
speech is intelligible on headphones and ordinary speakers. Keep safe source evidence
such as scene captures and narration scripts in the granted project workspace.

Publish the final video through the framework's verified media-output operation. Link
the exact output version to its work item and result. The owner can watch it in the
agent view and provide feedback against that exact version. Do not publish filesystem
paths as a substitute for a media output.
