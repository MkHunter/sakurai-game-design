#!/usr/bin/env python3
"""Phase 1B: Extract official burned-in English subtitles via ffmpeg bottom-ROI pipe + RapidOCR.

Sakurai's @sora_sakurai_en videos place official 8-4 Ltd. English subtitles inside a dedicated
dark letterbox strip at the bottom ~14% of the frame (y=0.858..0.996). Streaming ONLY that
cropped strip at 2 fps through ffmpeg makes extraction ~10x faster than full-frame decoding.
Optionally runs GPU-accelerated faster-whisper on Japanese audio (--whisper) for dual-track check.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
import typer
from rapidocr_onnxruntime import RapidOCR
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import (
    RAW_SUBS_DIR,
    RAW_VIDEOS_DIR,
    ensure_dirs,
    filter_episodes,
    load_manifest,
)
from lib.schemas import RawSubtitleExtraction, SubtitleCue

console = Console()
app = typer.Typer(add_completion=False)


def _init_ocr(device: str = "auto", cpu_threads: int = 4) -> tuple[RapidOCR, bool]:
    """Initialize RapidOCR with CUDA GPU acceleration when available, and bounded CPU threads."""
    ort.set_default_logger_severity(3)  # Silence harmless WSL /sys/class/drm probe warnings.
    if device in ("auto", "cuda") and hasattr(ort, "preload_dlls"):
        try:
            ort.preload_dlls()
        except (OSError, RuntimeError) as exc:
            console.print(f"[yellow]CUDA DLL preload warning: {exc}[/yellow]")

    providers = ort.get_available_providers()
    use_cuda = device == "cuda" or (device == "auto" and "CUDAExecutionProvider" in providers)

    ocr = RapidOCR(
        det_use_cuda=use_cuda,
        rec_use_cuda=use_cuda,
        use_cls=False,  # Official English subtitles are always horizontal; skip 180-deg angle net.
        intra_op_num_threads=cpu_threads,
        inter_op_num_threads=max(1, cpu_threads // 2),
    )
    active = ocr.text_det.infer.session.get_providers()
    gpu_active = "CUDAExecutionProvider" in active
    if gpu_active:
        console.print(
            f"[bold green]RapidOCR active on GPU (CUDAExecutionProvider + NVDEC, cpu_threads={cpu_threads})[/bold green]"
        )
    else:
        console.print(f"[yellow]RapidOCR active on CPU (cpu_threads={cpu_threads})[/yellow]")
    return ocr, gpu_active


def _normalize_ocr_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _similar(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _parse_yt_json3(path: Path, source: str) -> list[SubtitleCue]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    cues: list[SubtitleCue] = []
    for ev in data.get("events", []):
        segs = ev.get("segs")
        if not segs:
            continue
        text = re.sub(r"\s+", " ", "".join(s.get("utf8", "") for s in segs)).strip()
        if not text:
            continue
        start_ms = ev.get("tStartMs", 0)
        dur_ms = ev.get("dDurationMs", 2000)
        cues.append(
            SubtitleCue(
                start_sec=round(start_ms / 1000.0, 2),
                end_sec=round((start_ms + dur_ms) / 1000.0, 2),
                text=text,
                confidence=0.8,
                source=source,  # type: ignore[arg-type]
            )
        )
    return cues


def _probe_dimensions(video_path: Path) -> tuple[int, int]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1280)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 720)
    cap.release()
    return w, h


def _subtitle_mask(roi_bgr: np.ndarray) -> np.ndarray:
    """Isolate bright white subtitle glyphs inside the dark bottom letterbox strip."""
    gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 185, 255, cv2.THRESH_BINARY)
    return cv2.GaussianBlur(mask, (3, 3), 0)


def _ocr_lines(ocr: RapidOCR, roi_bgr: np.ndarray, min_conf: float = 0.55) -> tuple[str, float]:
    # Upscale 1.6x so descenders (g, y, p, q) and thin punctuation OCR cleanly.
    up = cv2.resize(roi_bgr, None, fx=1.6, fy=1.6, interpolation=cv2.INTER_CUBIC)
    res, _ = ocr(up)
    if not res:
        return "", 0.0

    lines: list[tuple[float, float, str, float]] = []
    for box, text, score in res:
        conf = float(score)
        if conf < min_conf:
            continue
        cleaned = _normalize_ocr_text(str(text))
        if not cleaned:
            continue
        ys = [pt[1] for pt in box]
        xs = [pt[0] for pt in box]
        lines.append((sum(ys) / len(ys), min(xs), cleaned, conf))

    if not lines:
        return "", 0.0

    lines.sort(key=lambda item: item[0])
    rows: list[list[tuple[float, float, str, float]]] = []
    for item in lines:
        if not rows or abs(item[0] - rows[-1][0][0]) > 26:
            rows.append([item])
        else:
            rows[-1].append(item)

    parts: list[str] = []
    confs: list[float] = []
    for row in rows:
        row.sort(key=lambda item: item[1])
        parts.append(" ".join(x[2] for x in row))
        confs.extend(x[3] for x in row)

    return _normalize_ocr_text(" ".join(parts)), round(sum(confs) / len(confs), 3)


def _run_whisper_ja(video_path: Path, model_name: str = "large-v3-turbo") -> list[SubtitleCue]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        console.print(
            "[yellow]faster-whisper not installed. Run `uv sync --extra gpu` to enable --whisper.[/yellow]"
        )
        return []

    console.print(f"    [cyan]Whisper ({model_name})[/cyan] transcribing Japanese audio on GPU...")
    model = WhisperModel(model_name, device="auto", compute_type="float16")
    segments, _ = model.transcribe(str(video_path), language="ja", vad_filter=True)
    return [
        SubtitleCue(
            start_sec=round(seg.start, 2),
            end_sec=round(seg.end, 2),
            text=seg.text.strip(),
            confidence=0.95,
            source="whisper_ja",
        )
        for seg in segments
        if seg.text.strip()
    ]


def extract_episode_hardsubs(
    ep: dict,
    ocr: RapidOCR,
    sample_fps: float = 2.0,
    roi_y0: float = 0.858,
    roi_y1: float = 0.996,
    roi_x0: float = 0.05,
    roi_x1: float = 0.95,
    change_threshold: float = 4.5,
    use_whisper: bool = False,
    whisper_model: str = "large-v3-turbo",
    use_hwaccel_cuda: bool = False,
    force: bool = False,
) -> Path | None:
    vid = ep["video_id"]
    code = ep["code"]
    video_path = RAW_VIDEOS_DIR / f"{code}_{vid}.mp4"
    out_path = RAW_SUBS_DIR / f"{code}_{vid}_extracted.json"

    if out_path.exists() and not force:
        console.print(f"  [dim]✓ {code} OCR already extracted ({out_path.name})[/dim]")
        return out_path

    if not video_path.exists():
        console.print(f"  [yellow]Skipping {code}: video not downloaded yet ({video_path.name}).[/yellow]")
        return None

    w, h = _probe_dimensions(video_path)
    x0 = int(w * roi_x0)
    y0 = int(h * roi_y0)
    crop_w = int(w * (roi_x1 - roi_x0))
    crop_h = int(h * (roi_y1 - roi_y0))
    # Ensure even dimensions for ffmpeg safety
    crop_w -= crop_w % 2
    crop_h -= crop_h % 2

    hwaccel_args = ["-hwaccel", "cuda"] if use_hwaccel_cuda else []
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        *hwaccel_args,
        "-threads",
        "2",
        "-i",
        str(video_path),
        "-vf",
        f"fps={sample_fps},crop={crop_w}:{crop_h}:{x0}:{y0}",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "bgr24",
        "-",
    ]

    frame_bytes = crop_w * crop_h * 3
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    cues: list[SubtitleCue] = []
    prev_mask: np.ndarray | None = None
    ocr_calls = 0
    sampled = 0

    try:
        assert proc.stdout is not None
        while True:
            buf = proc.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break

            roi = np.frombuffer(buf, dtype=np.uint8).reshape((crop_h, crop_w, 3))
            t_sec = round(sampled / sample_fps, 2)
            sampled += 1

            mask = _subtitle_mask(roi)
            bright_ratio = float(np.count_nonzero(mask > 180)) / mask.size

            should_ocr = False
            if bright_ratio > 0.002:
                if prev_mask is None:
                    should_ocr = True
                else:
                    diff = float(np.mean(cv2.absdiff(mask, prev_mask)))
                    if diff >= change_threshold:
                        should_ocr = True
            else:
                prev_mask = mask

            if should_ocr:
                ocr_calls += 1
                text, conf = _ocr_lines(ocr, roi)
                prev_mask = mask
                if text and len(text) >= 2:
                    if (
                        cues
                        and _similar(cues[-1].text, text) >= 0.86
                        and (t_sec - cues[-1].end_sec) <= 2.5
                    ):
                        cues[-1].end_sec = round(t_sec + (1.0 / sample_fps), 2)
                        if len(text) > len(cues[-1].text) and conf >= cues[-1].confidence - 0.05:
                            cues[-1].text = text
                            cues[-1].confidence = max(cues[-1].confidence, conf)
                    else:
                        cues.append(
                            SubtitleCue(
                                start_sec=t_sec,
                                end_sec=round(t_sec + (1.0 / sample_fps), 2),
                                text=text,
                                confidence=conf,
                                source="hardsub_ocr",
                            )
                        )
            elif cues and bright_ratio > 0.002 and (t_sec - cues[-1].end_sec) <= (1.5 / sample_fps + 0.1):
                cues[-1].end_sec = round(t_sec + (1.0 / sample_fps), 2)
    finally:
        if proc.stdout:
            proc.stdout.close()
        proc.wait()

    yt_auto_en = _parse_yt_json3(RAW_SUBS_DIR / f"{code}_{vid}.en.json3", source="yt_auto_en")
    whisper_ja = _run_whisper_ja(video_path, whisper_model) if use_whisper else []

    payload = RawSubtitleExtraction(
        video_id=vid,
        code=code,
        fps_sampled=sample_fps,
        roi_box=[roi_y0, roi_y1, roi_x0, roi_x1],
        cues=cues,
        title_cards=[],
        whisper_ja_cues=whisper_ja,
        yt_auto_en_cues=yt_auto_en,
    )
    out_path.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
    console.print(
        f"  [green]✓[/green] {code}: {len(cues)} hardsub cues "
        f"({ocr_calls} OCR calls / {sampled} sampled frames), {len(yt_auto_en)} yt-auto cues"
    )
    return out_path


@app.command()
def main(
    pilot: bool = typer.Option(False, "--pilot", help="Run on the 10-episode pilot set."),
    episodes: str | None = typer.Option(None, "--episodes", help="Comma-separated episode codes/IDs."),
    category: str | None = typer.Option(None, "--category", help="Filter by category code (A-N)."),
    limit: int | None = typer.Option(None, "--limit", help="Max episodes to process."),
    sample_fps: float = typer.Option(2.0, "--fps", help="Sampling rate for ROI change detection."),
    roi_y0: float = typer.Option(0.858, "--roi-y0", help="Top fraction of subtitle ROI."),
    roi_y1: float = typer.Option(0.996, "--roi-y1", help="Bottom fraction of subtitle ROI."),
    change_threshold: float = typer.Option(4.5, "--change-threshold", help="Pixel diff trigger."),
    whisper: bool = typer.Option(False, "--whisper", help="Also run local GPU faster-whisper on JA audio."),
    whisper_model: str = typer.Option("large-v3-turbo", "--whisper-model"),
    device: str = typer.Option("auto", "--device", help="OCR execution device: auto, cuda, or cpu."),
    cpu_threads: int = typer.Option(4, "--cpu-threads", help="Cap CPU threads to prevent system lag."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing extractions."),
) -> None:
    """Extract burned-in English subtitles from downloaded videos using ffmpeg pipe + RapidOCR."""
    ensure_dirs()
    manifest = load_manifest()
    codes = episodes.split(",") if episodes else None
    targets = filter_episodes(manifest, codes=codes, pilot=pilot, category=category, limit=limit)
    if not targets:
        console.print("[yellow]No matching episodes found.[/yellow]")
        return

    console.print(f"[bold cyan]Phase 1B:[/bold cyan] Initializing RapidOCR for {len(targets)} episode(s)...")
    ocr, gpu_active = _init_ocr(device=device, cpu_threads=cpu_threads)
    for ep in targets:
        extract_episode_hardsubs(
            ep,
            ocr=ocr,
            sample_fps=sample_fps,
            roi_y0=roi_y0,
            roi_y1=roi_y1,
            change_threshold=change_threshold,
            use_whisper=whisper,
            whisper_model=whisper_model,
            use_hwaccel_cuda=gpu_active,
            force=force,
        )


if __name__ == "__main__":
    app()
