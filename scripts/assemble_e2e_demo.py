#!/usr/bin/env python3
"""Assemble an honest, readable film from opt-in Playwright demo evidence.

Only final-passing reporter results are accepted. Browser frames stay unchanged;
editing adds title cards, a separate footer, labelled speed changes and longer
holds on exact checkpoint screenshots. Run with --plan-only before encoding.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys


CHAPTERS = [
    ("agents.spec.ts", "Agent creation and protected setup"),
    ("writer.spec.ts", "Managed work and stopping"),
    ("shared-work.spec.ts", "Shared results and saved outputs"),
    ("planning-work.spec.ts", "Planning and selected work"),
    ("native-chat.spec.ts", "Native Hermes conversation"),
    ("managed-chat.spec.ts", "Agent-specific conversations"),
    ("managed-chat-deadline.spec.ts", "Reply deadlines"),
    ("managed-chat-receipts.spec.ts", "Lost acknowledgement recovery"),
    ("managed-chat-recovery.spec.ts", "Draft and renderer recovery"),
    ("managed-chat-timeout-isolation.spec.ts", "Concurrent conversation isolation"),
    ("service-restart.spec.ts", "Whole-service restart recovery"),
]
WIDTH, HEIGHT, FOOTER = 1600, 1000, 120
SCOPE = (
    "Real browser, framework API, databases and native worker processes. "
    "Model and Plane responses use isolated HTTP fixtures. "
    "This verifies integration behavior, not live-model intelligence."
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> dict:
    require(path.is_file(), f"Missing evidence file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def specs_in(suite: dict):
    yield from suite.get("specs", [])
    for child in suite.get("suites", []):
        yield from specs_in(child)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def final_results(run_dirs: list[Path], expected: int) -> list[dict]:
    attempts = {}
    for run_dir in run_dirs:
        report_path = run_dir / "report.json"
        report = read_json(report_path)
        require(not report.get("errors"), f"Reporter infrastructure errors in {report_path}")
        stats = report.get("stats", {})
        run_count = 0
        for suite in report.get("suites", []):
            for spec in specs_in(suite):
                key = (Path(spec["file"]).name, spec["title"])
                tests = spec.get("tests", [])
                require(len(tests) == 1, f"Expected exactly one project result: {key}")
                test = tests[0]
                results = test.get("results", [])
                require(len(results) == 1, f"Each recording must disable automatic retries: {key}")
                result = results[0]
                passed = (spec.get("ok") is True and test.get("expectedStatus") == "passed"
                          and test.get("status") == "expected" and result.get("status") == "passed"
                          and not result.get("errors"))
                attempt = {"key": key, "spec": spec, "result": result, "run_dir": run_dir,
                           "report": report_path, "passed": passed,
                           "started_at": result.get("startTime", stats.get("startTime"))}
                require(attempt["started_at"], f"No attempt timestamp: {key}")
                attempts.setdefault(key, []).append(attempt)
                run_count += 1
        require(run_count == sum(stats.get(key, 0) for key in ("expected", "unexpected", "flaky", "skipped")),
                f"Reporter count does not match its scenarios: {report_path}")
    require(len(attempts) == expected, f"Expected {expected} unique tests, found {len(attempts)}")
    found = {}
    for key, history in attempts.items():
        history.sort(key=lambda attempt: timestamp(attempt["started_at"]))
        require(len({attempt["started_at"] for attempt in history}) == len(history),
                f"Duplicate or ambiguously ordered recordings: {key}")
        row = history[-1]
        require(row["passed"], f"Latest recorded attempt did not pass: {key}")
        attachments = row["result"].get("attachments", [])
        manifests = [Path(a["path"]) for a in attachments if a.get("name") == "demo-manifest" and a.get("path")]
        require(len(manifests) == 1, f"Expected one recorded checkpoint manifest: {key}")
        manifest = read_json(manifests[0])
        require((Path(manifest["file"]).name, manifest["title"]) == key,
                f"Manifest does not identify its reporter scenario: {key}")
        require(manifest.get("schemaVersion") == 1 and manifest.get("checkpoints"),
                f"Scenario has no supported checkpoint evidence: {key}")
        videos = [Path(a["path"]) for a in attachments if a.get("contentType") == "video/webm" and a.get("path")]
        require(videos and all(path.is_file() for path in videos), f"Missing final video: {key}")
        pages = manifest.get("pages", [])
        require(pages and len(pages) == len(videos), f"Recorded page/video count mismatch: {key}")
        video_by_page = {}
        for page in pages:
            index = page["index"]
            require(isinstance(index, int) and index >= 0 and index not in video_by_page, f"Invalid page index: {key}")
            source = Path(page["video"]) if page.get("video") else None
            if source is None or not source.is_file():
                # Playwright 1.62 saves context pages in creation order. The
                # temporary fixture path is removed after recording teardown.
                name = f"video{'-' + str(index) if index else ''}.webm"
                matches = [path for path in videos if path.name == name]
                require(len(matches) == 1, f"Cannot map page {index} to final reporter video: {key}")
                source = matches[0]
            video_by_page[index] = source
        require(set(video_by_page) == set(range(len(pages))), f"Noncontiguous page records: {key}")
        for checkpoint in manifest["checkpoints"]:
            require(checkpoint.get("pageIndex") in video_by_page, f"Checkpoint refers to an unrecorded page: {key}")
            require(Path(checkpoint.get("screenshot", "")).is_file(), f"Missing checkpoint screenshot: {key}")
            require(checkpoint.get("kind") in {"application", "api-evidence"}, f"Unknown checkpoint kind: {key}")
            require(all(isinstance(checkpoint.get(field), str) and checkpoint[field].strip()
                        for field in ("title", "expected", "proof")), f"Incomplete checkpoint caption: {key}")
            timings = [checkpoint.get(field) for field in ("videoStartMs", "screenshotAtMs", "videoEndMs")]
            require(all(isinstance(value, (int, float)) and math.isfinite(value) for value in timings)
                    and 0 <= timings[0] <= timings[1] < timings[2], f"Invalid checkpoint timing: {key}")
        found[key] = {**row, "manifest_path": manifests[0], "manifest": manifest,
                      "videos": video_by_page, "attempts": history}
    order = {name: index for index, (name, _) in enumerate(CHAPTERS)}
    require(all(key[0] in order for key in found), "A test file lacks a chapter mapping; add it explicitly")
    return sorted(found.values(), key=lambda row: (order[row["key"][0]], row["spec"].get("line", 0), row["key"][1]))


def copy_asset(source: Path, destination: Path, output: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return {"path": str(destination.relative_to(output)), "sha256": sha256(destination), "original_path": str(source)}


def video_info(path: Path, ffprobe: str) -> dict:
    result = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    info = json.loads(result.stdout)
    video = next((stream for stream in info["streams"] if stream.get("codec_type") == "video"), None)
    require(video is not None and video.get("width") == WIDTH and video.get("height") == HEIGHT,
            f"Expected unchanged 1600x1000 browser recording: {path}")
    duration = float(info["format"]["duration"])
    require(math.isfinite(duration) and duration > 0, f"Invalid video duration: {path}")
    return {"duration_seconds": duration, "width": WIDTH, "height": HEIGHT}


def without_holds(start: float, end: float, holds: list[tuple[float, float]]):
    cursor = start
    for left, right in sorted(holds):
        if right <= cursor or left >= end:
            continue
        if left > cursor:
            yield cursor, min(left, end)
        cursor = max(cursor, right)
    if cursor < end:
        yield cursor, end


def timestamp(value: str) -> float:
    from datetime import datetime
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def make_plan(rows: list[dict], output: Path, ffprobe: str) -> dict:
    from PIL import Image
    output.mkdir(parents=True, exist_ok=True)
    reports = {}
    scenarios, segments = [], []
    reruns = sum(len(row["attempts"]) > 1 for row in rows)
    failed_attempts = sum(not attempt["passed"] for row in rows for attempt in row["attempts"])

    def add(segment: dict):
        segment["start_seconds"] = round(sum(part["duration_seconds"] for part in segments), 3)
        segment["duration_seconds"] = math.ceil(segment["duration_seconds"] * 30 - 1e-9) / 30
        segments.append(segment)

    add({"kind": "card", "title": "Agent-native: end-to-end verification", "subtitle": f"{len(rows)} scenarios · final verified results passed",
         "body": [SCOPE, f"{reruns} scenarios were rerun; {failed_attempts} earlier failed attempts are retained in the evidence.", "Each result is shown after its assertions pass, then held for 8–12 seconds.",
                  "Workflow intervals are labelled with their playback speed. The retained raw clips are also available."],
         "duration_seconds": 20})
    chapter_labels = dict(CHAPTERS)
    for number, row in enumerate(rows, 1):
        file, title = row["key"]
        digest = hashlib.sha256(f"{file}\n{title}".encode()).hexdigest()[:10]
        destination = output / "raw" / f"scenario-{number:02}-{digest}"
        history = []
        for attempt_number, attempt in enumerate(row["attempts"], 1):
            attempt_report_key = str(attempt["report"])
            if attempt_report_key not in reports:
                reports[attempt_report_key] = copy_asset(attempt["report"], output / "raw" / f"report-{len(reports) + 1:02}.json", output)
            archived = {"number": attempt_number, "started_at": attempt["started_at"],
                        "status": attempt["result"].get("status"), "passed": attempt["passed"],
                        "report": reports[attempt_report_key]["path"], "attachments": []}
            for attachment_number, attachment in enumerate(attempt["result"].get("attachments", []), 1):
                source = Path(attachment["path"]) if attachment.get("path") else None
                if source and source.is_file():
                    asset = copy_asset(source, destination / "attempts" / f"{attempt_number:02}" /
                                       f"{attachment_number:02}-{source.name}", output)
                    archived["attachments"].append({"name": attachment.get("name"), **asset})
                elif source:
                    archived["attachments"].append({"name": attachment.get("name"),
                                                     "missing_original_path": str(source)})
            history.append(archived)
        report_key = str(row["report"])
        manifest_asset = copy_asset(row["manifest_path"], destination / "demo-manifest.json", output)
        manifest = row["manifest"]
        pages = {}
        for index, source in row["videos"].items():
            asset = copy_asset(source, destination / f"page-{index}.webm", output)
            asset.update(video_info(output / asset["path"], ffprobe))
            asset["started_at"] = next(page["startedAt"] for page in manifest["pages"] if page["index"] == index)
            pages[index] = asset
        scenario = {"number": number, "file": file, "title": title, "status": "passed",
                    "chapter": chapter_labels[file], "report": reports[report_key]["path"],
                    "manifest": manifest_asset, "pages": pages, "checkpoints": [], "attempts": history,
                    "verification": "passed after rerun" if len(history) > 1 else "passed on first recorded attempt"}
        scenario["start_seconds"] = round(sum(part["duration_seconds"] for part in segments), 3)
        add({"kind": "card", "scenario": number, "title": chapter_labels[file],
             "subtitle": f"Scenario {number:02} / {len(rows)} · {scenario['verification'].upper()} · {file}", "body": [title],
             "duration_seconds": 5})
        # Omit every raw checkpoint hold, including one spent on another page.
        global_holds = []
        for checkpoint in manifest["checkpoints"]:
            page_start = timestamp(pages[checkpoint["pageIndex"]]["started_at"])
            global_holds.append((page_start + checkpoint["videoStartMs"] / 1000,
                                 page_start + checkpoint["videoEndMs"] / 1000))
        cursors = {index: 0.0 for index in pages}
        for index, checkpoint in enumerate(manifest["checkpoints"], 1):
            page_index = checkpoint["pageIndex"]
            page = pages[page_index]
            page_start = timestamp(page["started_at"])
            holds = [(left - page_start, right - page_start) for left, right in global_holds]
            end = min(checkpoint["videoStartMs"] / 1000, page["duration_seconds"])
            if checkpoint["kind"] == "application":
                for start, finish in without_holds(cursors[page_index], end, holds):
                    length = finish - start
                    if length < 0.35:
                        continue
                    speed = max(1.0, length / 6.0)
                    add({"kind": "workflow", "scenario": number, "checkpoint": index, "source": page["path"],
                         "source_start_seconds": round(start, 3), "source_duration_seconds": round(length, 3),
                         "speed": round(speed, 6), "duration_seconds": length / speed,
                         "title": f"Scenario {number:02}/{len(rows)} · {chapter_labels[file]}",
                         "footer": f"Actual workflow footage · {speed:.1f}× speed · Result holds are shown separately"})
            cursors[page_index] = checkpoint["videoEndMs"] / 1000
            screenshot = copy_asset(Path(checkpoint["screenshot"]), destination / f"checkpoint-{index:02}.png", output)
            with Image.open(output / screenshot["path"]) as image:
                require(image.size == (WIDTH, HEIGHT), f"Unexpected screenshot dimensions: {screenshot['path']}")
            words = len(f"{checkpoint['title']} {checkpoint['expected']} {checkpoint['proof']}".split())
            duration = math.ceil(max(8.0, min(12.0, 5.0 + words / 8.0)) * 30) / 30
            cp = {**checkpoint, "screenshot": screenshot, "hold_seconds": duration,
                  "start_seconds": round(sum(part["duration_seconds"] for part in segments), 3)}
            scenario["checkpoints"].append(cp)
            add({"kind": "checkpoint", "scenario": number, "checkpoint": index,
                 "source": screenshot["path"], "duration_seconds": duration,
                 "title": f"Scenario {number:02}/{len(rows)} · PASS · {checkpoint['title']}",
                 "footer": "API-only assertion evidence · exact checkpoint screenshot" if checkpoint["kind"] == "api-evidence"
                           else "Exact screenshot after assertions passed · unchanged application pixels"})
        scenarios.append(scenario)
    count = sum(len(scenario["checkpoints"]) for scenario in scenarios)
    add({"kind": "card", "title": f"{len(rows)} scenarios passed · {count} verified checkpoints",
         "subtitle": "What this evidence establishes", "body": [
             f"{reruns} scenarios were rerun; all final recorded attempts passed. {failed_attempts} failed attempts remain archived.",
             "The implemented workflows passed against real framework services, storage and native processes.",
             "The provider and Plane were scripted at their external HTTP boundaries. This is repeatable integration evidence.",
             "It does not establish live-model judgement, scheduled autonomy, or features not yet implemented.",
             "Retained raw clips, screenshots, reporter results, chapters and the edit plan accompany this video."],
         "duration_seconds": 20})
    return {"schema_version": 1, "status": "validated-not-encoded", "scope": SCOPE,
            "test_count": len(rows), "checkpoint_count": count, "rerun_scenarios": reruns,
            "failed_attempts": failed_attempts, "reports": list(reports.values()),
            "resolution": [WIDTH, HEIGHT + FOOTER], "audio": "none; captioned",
            "raw_video_offsets": "Approximate from page-created events; exact proof is the retained screenshot.",
            "duration_seconds": round(sum(segment["duration_seconds"] for segment in segments), 3),
            "scenarios": scenarios, "segments": segments}


def font_paths() -> tuple[Path, Path]:
    candidates = [
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for normal, bold in candidates:
        if Path(normal).is_file() and Path(bold).is_file():
            return Path(normal), Path(bold)
    raise ValueError("Arial or DejaVu Sans fonts are required to render readable evidence cards")


def wrapped(text: str, font, width: int) -> list[str]:
    lines, current = [], ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if font.getlength(candidate) <= width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_card(segment: dict, target: Path, footer_only: bool = False):
    from PIL import Image, ImageDraw, ImageFont
    normal, bold = font_paths()
    image = Image.new("RGB", (WIDTH, FOOTER if footer_only else HEIGHT + FOOTER), "#101827")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, WIDTH, 4), fill="#5eead4")
    if footer_only:
        size = 26
        while ImageFont.truetype(str(bold), size).getlength(segment["title"]) > WIDTH - 64 and size > 15:
            size -= 1
        draw.text((32, 20), segment["title"], font=ImageFont.truetype(str(bold), size), fill="#f8fafc")
        draw.text((32, 73), segment["footer"], font=ImageFont.truetype(str(normal), 23), fill="#a5b4c8")
    else:
        y = 110
        draw.text((80, y), "AGENT-NATIVE · AUTOMATED BROWSER VERIFICATION", font=ImageFont.truetype(str(bold), 23), fill="#5eead4")
        y += 90
        for line in wrapped(segment["title"], ImageFont.truetype(str(bold), 48), WIDTH - 160):
            draw.text((80, y), line, font=ImageFont.truetype(str(bold), 48), fill="#f8fafc")
            y += 60
        y += 25
        for line in wrapped(segment["subtitle"], ImageFont.truetype(str(bold), 29), WIDTH - 160):
            draw.text((80, y), line, font=ImageFont.truetype(str(bold), 29), fill="#a7f3d0")
            y += 40
        y += 30
        for paragraph in segment["body"]:
            for line in wrapped(paragraph, ImageFont.truetype(str(normal), 31), WIDTH - 160):
                draw.text((80, y), line, font=ImageFont.truetype(str(normal), 31), fill="#cbd5e1")
                y += 43
            y += 25
        require(y < HEIGHT + FOOTER - 50, f"Evidence card text overflows: {segment['title']}")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)


def encode(plan: dict, output: Path, ffmpeg: str, ffprobe: str):
    edit = output / "edit"
    edit.mkdir(exist_ok=True)
    clips = []
    elapsed = 0.0
    for index, segment in enumerate(plan["segments"]):
        target = edit / f"segment-{index:04}.mp4"
        image = edit / f"card-{index:04}.png"
        command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-filter_threads", "2", "-filter_complex_threads", "2"]
        frame_count = round(segment["duration_seconds"] * 30)
        if segment["kind"] == "card":
            render_card(segment, image)
            command += ["-loop", "1", "-framerate", "30", "-i", str(image),
                        "-vf", "format=yuv420p"]
        else:
            render_card(segment, image, footer_only=True)
            source = output / segment["source"]
            if segment["kind"] == "checkpoint":
                command += ["-loop", "1", "-framerate", "30", "-i", str(source)]
                speed = 1
            else:
                command += ["-ss", str(segment["source_start_seconds"]), "-t", str(segment["source_duration_seconds"]), "-i", str(source)]
                speed = segment["speed"]
            command += ["-i", str(image), "-filter_complex",
                        f"[0:v]setpts=(PTS-STARTPTS)/{speed},fps=30,tpad=stop_mode=clone:stop_duration=1,pad={WIDTH}:{HEIGHT + FOOTER}:0:0:color=0x101827,setsar=1[base];"
                        f"[base][1:v]overlay=0:{HEIGHT},format=yuv420p[out]", "-map", "[out]"]
        command += ["-frames:v", str(frame_count), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-threads", "2", "-movflags", "+faststart", str(target)]
        subprocess.run(command, check=True)
        measured = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,nb_frames,width,height", "-of", "json", str(target)],
                                  check=True, capture_output=True, text=True)
        measurement = json.loads(measured.stdout)
        stream = next(item for item in measurement["streams"] if item["codec_type"] == "video")
        require(int(stream["nb_frames"]) == frame_count, f"Wrong encoded frame count: {target}")
        require((stream["width"], stream["height"]) == (WIDTH, HEIGHT + FOOTER), f"Wrong encoded dimensions: {target}")
        segment["encoded_frames"] = frame_count
        segment["measured_container_duration_seconds"] = float(measurement["format"]["duration"])
        segment["duration_seconds"] = frame_count / 30
        require(segment["kind"] != "checkpoint" or segment["duration_seconds"] >= 8,
                "An encoded proof screenshot is shorter than 8 seconds")
        segment["start_seconds"] = round(elapsed, 3)
        elapsed += segment["duration_seconds"]
        if segment["kind"] == "card" and segment.get("scenario"):
            plan["scenarios"][segment["scenario"] - 1]["start_seconds"] = segment["start_seconds"]
        if segment["kind"] == "checkpoint":
            checkpoint = plan["scenarios"][segment["scenario"] - 1]["checkpoints"][segment["checkpoint"] - 1]
            checkpoint["start_seconds"] = segment["start_seconds"]
            checkpoint["hold_seconds"] = segment["duration_seconds"]
        clips.append(target)
        print(f"Encoded {index + 1}/{len(plan['segments'])}: {segment['kind']}", flush=True)
    concat = edit / "concat.txt"
    concat.write_text("".join(f"file '{clip.name}'\n" for clip in clips))
    target = output / "agent-native-e2e-demo.mp4"
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(concat), "-c", "copy", "-movflags", "+faststart", str(target)], check=True)
    measured = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration:stream=codec_type,nb_frames",
                               "-of", "json", str(target)], check=True, capture_output=True, text=True)
    measurement = json.loads(measured.stdout)
    stream = next(item for item in measurement["streams"] if item["codec_type"] == "video")
    require(int(stream["nb_frames"]) == sum(segment["encoded_frames"] for segment in plan["segments"]),
            "Concatenated video lost or added frames")
    actual_duration = float(measurement["format"]["duration"])
    require(abs(actual_duration - elapsed) <= 1 / 30 + 0.002, "Concatenated video duration differs from the edit plan")
    plan["duration_seconds"] = round(elapsed, 3)
    plan["measured_video_duration_seconds"] = actual_duration
    plan["status"] = "encoded"
    plan["video"] = {"path": target.name, "sha256": sha256(target)}


def timecode(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 3600:02}:{seconds // 60 % 60:02}:{seconds % 60:02}"


def write_evidence(plan: dict, output: Path):
    (output / "evidence.json").write_text(json.dumps(plan, indent=2) + "\n")
    lines = ["# Agent-native end-to-end verification", "", SCOPE, "",
             f"{plan['test_count']} passing scenarios; {plan['checkpoint_count']} proof checkpoints. "
             "Every exact result screenshot is held for at least 8 seconds. No audio.", "",
             "| Time | Scenario | Final result |", "| --- | --- | --- |"]
    for scenario in plan["scenarios"]:
        title = scenario["title"].replace("|", "\\|")
        lines.append(f"| {timecode(scenario['start_seconds'])} | {scenario['number']:02}. {title} | {scenario['verification']} |")
    lines += ["", f"{plan['rerun_scenarios']} scenarios were rerun. {plan['failed_attempts']} earlier failed attempts are preserved.",
              "", "Reporter JSON is authoritative. Raw assets are preserved under `raw/`; "
              "`evidence.json` records hashes, source timings, playback speeds and screenshot holds.", "",
              "Video offsets are approximate page-event timings. Exact screenshots, not inferred video frames, "
              "provide the final checkpoint evidence.", ""]
    (output / "chapters.md").write_text("\n".join(lines))
    buttons = []
    for scenario in plan["scenarios"]:
        buttons.append(f'<button data-seek="{scenario["start_seconds"]}"><span>{timecode(scenario["start_seconds"])}</span> '
                       f'{scenario["number"]:02}. {html.escape(scenario["title"])} '
                       f'<em>{html.escape(scenario["verification"])}</em></button>')
    document = f'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent-native end-to-end verification</title>
<style>
body{{margin:0;background:#101827;color:#e2e8f0;font:17px/1.5 system-ui,sans-serif}}
main{{max-width:1440px;margin:auto;padding:32px}}h1{{font-size:32px;color:#f8fafc}}p{{max-width:1100px;color:#b7c6d8}}
video{{width:100%;max-height:75vh;background:#050b14;border:1px solid #46576b;border-radius:12px}}
nav{{display:grid;gap:8px;margin-top:24px}}button{{text-align:left;background:#17263a;color:#e2e8f0;border:1px solid #334b66;padding:14px;border-radius:7px;font:inherit;cursor:pointer}}
button:hover{{border-color:#5eead4}}span{{color:#5eead4;margin-right:12px;font-variant-numeric:tabular-nums}}em{{display:block;margin-left:85px;font-size:14px;color:#a7f3d0}}a{{color:#5eead4}}
</style><main><h1>Agent-native: end-to-end verification</h1>
<p>{html.escape(SCOPE)}</p><p>{plan["test_count"]} final passing scenarios; {plan["checkpoint_count"]} proof checkpoints.
{plan["rerun_scenarios"]} scenarios were rerun; {plan["failed_attempts"]} failed attempts remain archived.</p>
<video controls preload="metadata" src="agent-native-e2e-demo.mp4"></video>
<p>Every exact checkpoint screenshot is held for at least 8 seconds. No audio.
<a href="evidence.json">Evidence and edit plan</a> · <a href="chapters.md">Chapter list</a></p>
<nav aria-label="Video chapters">{"".join(buttons)}</nav></main>
<script>const video=document.querySelector('video');document.querySelectorAll('[data-seek]').forEach(button=>button.addEventListener('click',()=>{{video.currentTime=Number(button.dataset.seek);video.play();video.scrollIntoView({{block:'start',behavior:'smooth'}});}}));</script>
</html>'''
    (output / "index.html").write_text(document, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, action="append", required=True, help="Completed demo output directory containing report.json; repeat for restart")
    parser.add_argument("--output-dir", type=Path, required=True, help="Ignored artifact destination, separate from run directories")
    parser.add_argument("--expected-tests", type=int, default=30)
    parser.add_argument("--plan-only", action="store_true", help="Validate and preserve assets, write edit plan; do not encode")
    args = parser.parse_args()
    try:
        run_dirs = [path.resolve() for path in args.run_dir]
        output = args.output_dir.resolve()
        require(args.expected_tests > 0, "Expected test count must be positive")
        require(len(set(run_dirs)) == len(run_dirs), "Duplicate source run directory")
        require(all(output != path and path not in output.parents and output not in path.parents for path in run_dirs),
                "Output must be separate from source run directories")
        ffprobe = shutil.which("ffprobe")
        require(ffprobe is not None, "ffprobe must be installed")
        rows = final_results(run_dirs, args.expected_tests)
        plan = make_plan(rows, output, ffprobe)
        write_evidence(plan, output)
        if not args.plan_only:
            ffmpeg = shutil.which("ffmpeg")
            require(ffmpeg is not None, "ffmpeg must be installed")
            encode(plan, output, ffmpeg, ffprobe)
            write_evidence(plan, output)
        print(json.dumps({"status": plan["status"], "tests": plan["test_count"], "checkpoints": plan["checkpoint_count"],
                          "duration_seconds": plan["duration_seconds"], "output": str(output)}))
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Cannot assemble demo: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
