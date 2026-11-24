#!/usr/bin/env python3
"""Phase 2A: Shot segmentation, talking-head filtering, deictic scoring, and contact-sheet generation."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import cv2
import imagehash
import numpy as np
import typer
from PIL import Image, ImageDraw
from rich.console import Console
from scenedetect import ContentDetector, detect

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import (
    HIGH_VISUAL_CATEGORIES,
    LOW_VISUAL_CATEGORIES,
    MEDIA_DIR,
    RAW_VIDEOS_DIR,
    ROOT_DIR,
    TRANSCRIPTS_DIR,
    VISUAL_DEICTIC_CUES,
    VISUALS_RAW_DIR,
    ensure_dirs,
    filter_episodes,
    load_manifest,
    yt_timestamp_url,
)
from lib.schemas import CleanTranscript, RawVisualCandidate

console = Console()
app = typer.Typer(add_completion=False)


def _load_face_cascade() -> cv2.CascadeClassifier | None:
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    if cascade_path.exists():
        clf = cv2.CascadeClassifier(str(cascade_path))
        if not clf.empty():
            return clf
    return None


def _talking_head_score(frame_bgr: np.ndarray, face_clf: cv2.CascadeClassifier | None) -> float:
    """Estimate probability [0..1] that a frame is a pure talking-head desk shot without PiP diagrams."""
    h, w = frame_bgr.shape[:2]
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

    has_center_face = False
    if face_clf is not None:
        small = cv2.resize(gray, (320, int(320 * h / w)))
        faces = face_clf.detectMultiScale(small, scaleFactor=1.15, minNeighbors=5, minSize=(28, 28))
        for fx, fy, fw, fh in faces:
            cx = (fx + fw / 2) / small.shape[1]
            cy = (fy + fh / 2) / small.shape[0]
            if 0.28 <= cx <= 0.72 and 0.15 <= cy <= 0.65:
                has_center_face = True
                break

    if not has_center_face:
        return 0.0

    # Check if there is a high-contrast diagram/inset graphic overlay alongside Sakurai (keep if so!).
    upper = gray[: int(h * 0.78), :]
    edges = cv2.Canny(upper, 110, 220)
    # Inspect left and right thirds for crisp diagram/text borders.
    left_edge = float(np.count_nonzero(edges[:, : int(w * 0.32)])) / max(1, edges[:, : int(w * 0.32)].size)
    right_edge = float(np.count_nonzero(edges[:, int(w * 0.68) :])) / max(1, edges[:, int(w * 0.68) :].size)
    if max(left_edge, right_edge) > 0.075:
        return 0.35  # Likely PiP / diagram next to Sakurai — keep!

    return 0.9


def _read_frame_at(cap: cv2.VideoCapture, t_sec: float, fps: float) -> np.ndarray | None:
    frame_no = max(0, round(t_sec * fps))
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
    ok, frame = cap.read()
    return frame if ok and frame is not None else None


def _compute_motion_score(cap: cv2.VideoCapture, start_sec: float, end_sec: float, fps: float) -> float:
    dur = end_sec - start_sec
    if dur < 0.8:
        return 0.0
    times = np.linspace(start_sec + 0.15 * dur, end_sec - 0.15 * dur, 4)
    grays = []
    for t in times:
        fr = _read_frame_at(cap, float(t), fps)
        if fr is not None:
            # Exclude bottom subtitle strip so subtitle changes don't look like gameplay motion.
            h = fr.shape[0]
            crop = fr[: int(h * 0.76), :]
            grays.append(cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), (160, 90)))
    if len(grays) < 2:
        return 0.0
    diffs = [float(np.mean(cv2.absdiff(grays[i], grays[i + 1]))) for i in range(len(grays) - 1)]
    return round(float(np.mean(diffs)), 2)


def _transcript_window(tr: CleanTranscript | None, start_sec: float, end_sec: float, pad: float = 6.0) -> tuple[str, list[str]]:
    if tr is None:
        return "", []
    lo = max(0.0, start_sec - pad)
    hi = end_sec + pad
    snippets = [c.text for c in tr.cues if c.end_sec >= lo and c.start_sec <= hi]
    if not snippets:
        snippets = [s.text for s in tr.sections if s.end_sec >= lo and s.start_sec <= hi]
    joined = " ".join(snippets).strip()
    lower = joined.lower()
    hits = [cue for cue in VISUAL_DEICTIC_CUES if re.search(rf"\b{re.escape(cue)}\b", lower)]
    return joined[:700], hits


def _save_webp(frame_bgr: np.ndarray, out_path: Path, max_width: int = 1280) -> None:
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="WEBP", quality=82, method=4)


def _save_contact_sheet(
    cap: cv2.VideoCapture,
    start_sec: float,
    end_sec: float,
    fps: float,
    out_path: Path,
    cols: int = 3,
    rows: int = 2,
    tile_w: int = 426,
) -> bool:
    n = cols * rows
    dur = max(0.5, end_sec - start_sec)
    times = np.linspace(start_sec + 0.05 * dur, end_sec - 0.05 * dur, n)
    tiles: list[tuple[float, Image.Image]] = []
    for t in times:
        fr = _read_frame_at(cap, float(t), fps)
        if fr is None:
            continue
        rgb = cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)
        im = Image.fromarray(rgb)
        tile_h = round(im.height * (tile_w / im.width))
        im = im.resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        tiles.append((float(t), im))

    if len(tiles) < 2:
        return False

    tile_h = tiles[0][1].height
    header_h = 22
    sheet = Image.new("RGB", (cols * tile_w, rows * (tile_h + header_h)), (18, 20, 24))
    draw = ImageDraw.Draw(sheet)

    for idx, (t, im) in enumerate(tiles):
        r, c = divmod(idx, cols)
        x = c * tile_w
        y = r * (tile_h + header_h)
        mins, secs = divmod(int(t), 60)
        tenths = int((t - int(t)) * 10)
        label = f"#{idx + 1}  {mins:02d}:{secs:02d}.{tenths}"
        draw.rectangle([x, y, x + tile_w, y + header_h], fill=(28, 32, 40))
        draw.text((x + 8, y + 4), label, fill=(235, 240, 250))
        sheet.paste(im, (x, y + header_h))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_path, format="WEBP", quality=80, method=4)
    return True


def _export_webp_loop(video_path: Path, start_sec: float, end_sec: float, out_path: Path) -> bool:
    dur = min(5.0, max(1.5, end_sec - start_sec))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start_sec:.2f}",
        "-t",
        f"{dur:.2f}",
        "-i",
        str(video_path),
        "-vf",
        "fps=10,scale=480:-2:flags=lanczos",
        "-loop",
        "0",
        "-an",
        "-q:v",
        "68",
        str(out_path),
    ]
    proc = subprocess.run(cmd, check=False, capture_output=True)
    return proc.returncode == 0 and out_path.exists()


def _max_visuals_for_category(cat_code: str) -> int:
    c = cat_code.upper()
    if c in HIGH_VISUAL_CATEGORIES:
        return 14
    if c in LOW_VISUAL_CATEGORIES:
        return 5
    return 9


def extract_visuals_for_episode(
    ep: dict,
    face_clf: cv2.CascadeClassifier | None,
    max_visuals_override: int | None = None,
    export_loops: bool = False,
    force: bool = False,
) -> Path | None:
    vid = ep["video_id"]
    code = ep["code"]
    slug = ep["slug"]
    video_path = RAW_VIDEOS_DIR / f"{code}_{vid}.mp4"
    out_json = VISUALS_RAW_DIR / f"{slug}.json"

    if out_json.exists() and not force:
        console.print(f"  [dim]✓ {code} visuals already extracted ({out_json.name})[/dim]")
        return out_json

    if not video_path.exists():
        console.print(f"  [yellow]Skipping {code}: video missing ({video_path.name}).[/yellow]")
        return None

    tr_path = TRANSCRIPTS_DIR / f"{slug}.json"
    transcript = (
        CleanTranscript.model_validate_json(tr_path.read_text(encoding="utf-8"))
        if tr_path.exists()
        else None
    )

    # 1. Detect shots via PySceneDetect (fallback to 12s uniform windows if single-shot).
    scenes = detect(str(video_path), ContentDetector(threshold=26.0, min_scene_len=20))
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        console.print(f"  [red]✗ Failed to open {video_path}[/red]")
        return None

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = total_frames / fps if fps > 0 else float(ep.get("duration_sec") or 0)

    if scenes:
        intervals = [(s[0].seconds, s[1].seconds) for s in scenes]
    else:
        intervals = [(t, min(duration, t + 12.0)) for t in range(0, int(duration), 12)]

    # 2. Score each shot & deduplicate visually identical shots with dHash.
    scored_shots: list[dict] = []
    seen_hashes: list[imagehash.ImageHash] = []

    try:
        for start_s, end_s in intervals:
            dur = end_s - start_s
            if dur < 1.0:
                continue
            # Skip intro/outro bumper (~first 4s and last 6s).
            if end_s < 4.5 or start_s > max(0.0, duration - 6.0):
                continue

            mid_s = (start_s + end_s) / 2.0
            mid_frame = _read_frame_at(cap, mid_s, fps)
            if mid_frame is None:
                continue

            # Ignore nearly black/white transition frames.
            mean_luma = float(np.mean(cv2.cvtColor(mid_frame, cv2.COLOR_BGR2GRAY)))
            if mean_luma < 12 or mean_luma > 246:
                continue

            th_score = _talking_head_score(mid_frame, face_clf)
            if th_score >= 0.8:
                continue

            # Perceptual dedup on upper 76% (excluding subtitles).
            upper_rgb = cv2.cvtColor(mid_frame[: int(mid_frame.shape[0] * 0.76), :], cv2.COLOR_BGR2RGB)
            h_val = imagehash.dhash(Image.fromarray(upper_rgb))
            if any((h_val - prev) <= 6 for prev in seen_hashes):
                continue
            seen_hashes.append(h_val)

            motion = _compute_motion_score(cap, start_s, end_s, fps)
            ctx_text, deictic_hits = _transcript_window(transcript, start_s, end_s)

            # Edge density proxy for diagrams / UI / annotated overlays.
            edges = cv2.Canny(cv2.cvtColor(mid_frame[: int(mid_frame.shape[0] * 0.76), :], cv2.COLOR_BGR2GRAY), 100, 200)
            edge_density = float(np.count_nonzero(edges)) / edges.size

            score = (
                2.5 * len(deictic_hits)
                + min(4.0, dur / 4.0)
                + (2.0 if 0.03 <= edge_density <= 0.16 else 0.5)
                + (1.5 if motion >= 7.0 else 0.8)
                - (2.0 * th_score)
            )
            is_motion_demo = (
                dur >= 2.2
                and (
                    motion >= 8.5
                    or any(k in deictic_hits for k in ("slow motion", "frame by frame", "frames", "compare", "before", "after"))
                )
            )

            scored_shots.append(
                {
                    "start_sec": round(start_s, 2),
                    "end_sec": round(end_s, 2),
                    "mid_sec": round(mid_s, 2),
                    "score": round(score, 2),
                    "motion": motion,
                    "th_score": th_score,
                    "deictic_hits": deictic_hits,
                    "ctx_text": ctx_text,
                    "kind": "contact_sheet" if is_motion_demo else "keyframe",
                }
            )

        # Keep top-K shots sorted chronologically.
        budget = max_visuals_override or _max_visuals_for_category(ep["category_code"])
        selected = sorted(scored_shots, key=lambda x: x["score"], reverse=True)[:budget]
        selected.sort(key=lambda x: x["start_sec"])

        ep_media_dir = MEDIA_DIR / vid
        candidates: list[RawVisualCandidate] = []

        for item in selected:
            sec_int = round(item["start_sec"])
            asset_id = f"vis_{vid}_{sec_int:04d}"
            kind = item["kind"]
            out_img = ep_media_dir / f"{asset_id}_{'sheet' if kind == 'contact_sheet' else 'key'}.webp"

            saved = False
            if kind == "contact_sheet":
                saved = _save_contact_sheet(cap, item["start_sec"], item["end_sec"], fps, out_img)
            if not saved:
                kind = "keyframe"
                out_img = ep_media_dir / f"{asset_id}_key.webp"
                fr = _read_frame_at(cap, item["mid_sec"], fps)
                if fr is not None:
                    _save_webp(fr, out_img)
                    saved = True

            if not saved:
                continue

            loop_rel: str | None = None
            if export_loops and kind == "contact_sheet":
                loop_out = ep_media_dir / f"{asset_id}_loop.webp"
                if _export_webp_loop(video_path, item["start_sec"], item["end_sec"], loop_out):
                    loop_rel = str(loop_out.relative_to(ROOT_DIR))

            candidates.append(
                RawVisualCandidate(
                    asset_id=asset_id,
                    video_id=vid,
                    code=code,
                    start_sec=item["start_sec"],
                    end_sec=item["end_sec"],
                    kind=kind,
                    local_path=str(out_img.relative_to(ROOT_DIR)),
                    loop_path=loop_rel,
                    youtube_url=yt_timestamp_url(vid, item["start_sec"]),
                    score=item["score"],
                    deictic_hits=item["deictic_hits"],
                    transcript_context=item["ctx_text"],
                    motion_score=item["motion"],
                    talking_head_score=item["th_score"],
                )
            )
    finally:
        cap.release()

    out_json.write_text(
        json.dumps([c.model_dump() for c in candidates], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    sheets = sum(1 for c in candidates if c.kind == "contact_sheet")
    console.print(
        f"  [green]✓[/green] {code}: kept {len(candidates)} visual candidates "
        f"({sheets} contact sheets, {len(candidates) - sheets} keyframes) from {len(intervals)} shots"
    )
    return out_json


@app.command()
def main(
    pilot: bool = typer.Option(False, "--pilot"),
    episodes: str | None = typer.Option(None, "--episodes"),
    category: str | None = typer.Option(None, "--category"),
    limit: int | None = typer.Option(None, "--limit"),
    max_visuals: int | None = typer.Option(None, "--max-visuals", help="Override per-episode cap."),
    export_loops: bool = typer.Option(False, "--export-loops", help="Also generate 480p WebP motion loops."),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Extract deduplicated visual keyframes & timestamped contact sheets locally ($0)."""
    ensure_dirs()
    manifest = load_manifest()
    codes = episodes.split(",") if episodes else None
    targets = filter_episodes(manifest, codes=codes, pilot=pilot, category=category, limit=limit)

    face_clf = _load_face_cascade()
    console.print(f"[bold cyan]Phase 2A:[/bold cyan] Extracting visuals for {len(targets)} episode(s)...")
    for ep in targets:
        extract_visuals_for_episode(
            ep,
            face_clf=face_clf,
            max_visuals_override=max_visuals,
            export_loops=export_loops,
            force=force,
        )


if __name__ == "__main__":
    app()
