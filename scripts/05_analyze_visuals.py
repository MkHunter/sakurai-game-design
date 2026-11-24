#!/usr/bin/env python3
"""Phase 2B: Selective multimodal VLM analysis of keyframes & contact sheets (Gemini Flash)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import (
    DEFAULT_GEMINI_VISION_MODEL,
    ROOT_DIR,
    VISUALS_RAW_DIR,
    ensure_dirs,
    filter_episodes,
    load_manifest,
)
from lib.gemini_client import GeminiHelper, GeminiUnavailableError, is_fatal_gemini_error
from lib.schemas import RawVisualCandidate, VisualAnnotation

console = Console()
app = typer.Typer(add_completion=False)


def _heuristic_annotate(cand: RawVisualCandidate) -> VisualAnnotation:
    """Offline fallback annotation preserving transcript context & visual metadata."""
    hits = set(cand.deictic_hits)
    if cand.kind == "contact_sheet":
        if hits & {"compare", "before", "after", "side by side", "without", "with it"}:
            atype = "comparison_before_after"
        else:
            atype = "animation_breakdown"
    elif hits & {"diagram", "graph", "chart"}:
        atype = "diagram"
    else:
        atype = "annotated_gameplay"

    imp = "high" if (len(cand.deictic_hits) >= 2 or cand.score >= 8.0) else "medium"
    return VisualAnnotation(
        asset_id=cand.asset_id,
        video_id=cand.video_id,
        code=cand.code,
        start_sec=cand.start_sec,
        end_sec=cand.end_sec,
        kind=cand.kind,
        local_path=cand.local_path,
        loop_path=cand.loop_path,
        youtube_url=cand.youtube_url,
        asset_type=atype,  # type: ignore[arg-type]
        importance=imp,  # type: ignore[arg-type]
        visual_summary=(
            f"{'Sequential 6-frame contact sheet' if cand.kind == 'contact_sheet' else 'Keyframe'} "
            f"captured at {cand.start_sec:.1f}s–{cand.end_sec:.1f}s. Context: {cand.transcript_context[:260]}"
        ),
        design_detail_highlighted=", ".join(cand.deictic_hits) if cand.deictic_hits else "Visual reference",
        analysis_mode="heuristic",
    )


def _gemini_annotate(
    ep: dict,
    cand: RawVisualCandidate,
    gemini: GeminiHelper,
    model: str,
    thinking_level: str = "minimal",
) -> VisualAnnotation:
    img_path = ROOT_DIR / cand.local_path
    kind_desc = (
        "a 3x2 labeled chronological contact sheet showing motion/animation progression across timestamps"
        if cand.kind == "contact_sheet"
        else "a single keyframe screenshot"
    )
    prompt = f"""You are analyzing {kind_desc} from Masahiro Sakurai's game design video:
Episode: {ep['code']} — {ep['title']} ({ep['category_name']})
Timestamp: {cand.start_sec:.1f}s to {cand.end_sec:.1f}s
Surrounding English narration:
"{cand.transcript_context}"

Inspect the image carefully and extract ONLY grounded, directly observable visual game-design information.
If the image is generic unannotated B-roll or a plain talking-head shot with no instructional visual value, set asset_type="skip_generic_broll" and importance="low".

Return strict JSON:
{{
  "asset_type": "diagram|comparison_before_after|animation_breakdown|ui_callout|annotated_gameplay|principle_slide|skip_generic_broll",
  "importance": "high|medium|low",
  "visual_summary": "1-3 concrete sentences describing what is visually shown and why Sakurai crafted this visual.",
  "design_detail_highlighted": "The specific subtle craft/animation/UI/timing detail demonstrated (or empty string if generic).",
  "before_after_delta": "If showing a comparison (Good vs Bad, With vs Without), state the exact observable difference; otherwise empty string.",
  "on_screen_text": "Transcribe any diagram labels, callouts, numbers, or headings (ignore bottom subtitles).",
  "mermaid_or_ascii": "If this is a diagram, chart, timeline, or state flow, reconstruct it cleanly in Mermaid or compact ASCII so text-only AI agents can read it; otherwise empty string."
}}
"""
    data = gemini.generate_json(
        prompt=prompt,
        model=model,
        image_paths=[img_path],
        temperature=0.1,
        thinking_level=thinking_level,
    )
    valid_types = {
        "diagram",
        "comparison_before_after",
        "animation_breakdown",
        "ui_callout",
        "annotated_gameplay",
        "principle_slide",
        "skip_generic_broll",
    }
    atype = data.get("asset_type", "annotated_gameplay")
    if atype not in valid_types:
        atype = "annotated_gameplay"
    imp = data.get("importance", "medium")
    if imp not in ("high", "medium", "low"):
        imp = "medium"

    return VisualAnnotation(
        asset_id=cand.asset_id,
        video_id=cand.video_id,
        code=cand.code,
        start_sec=cand.start_sec,
        end_sec=cand.end_sec,
        kind=cand.kind,
        local_path=cand.local_path,
        loop_path=cand.loop_path,
        youtube_url=cand.youtube_url,
        asset_type=atype,
        importance=imp,
        visual_summary=str(data.get("visual_summary", "")).strip(),
        design_detail_highlighted=str(data.get("design_detail_highlighted", "")).strip(),
        before_after_delta=str(data.get("before_after_delta", "")).strip(),
        on_screen_text=str(data.get("on_screen_text", "")).strip(),
        mermaid_or_ascii=str(data.get("mermaid_or_ascii", "")).strip(),
        analysis_mode="gemini",
    )


@app.command()
def main(
    pilot: bool = typer.Option(False, "--pilot"),
    episodes: str | None = typer.Option(None, "--episodes"),
    category: str | None = typer.Option(None, "--category"),
    limit: int | None = typer.Option(None, "--limit"),
    offline: bool = typer.Option(False, "--offline", help="Use local heuristic metadata ($0)."),
    model: str = typer.Option(DEFAULT_GEMINI_VISION_MODEL, "--model"),
    thinking_level: str = typer.Option("minimal", "--thinking-level"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Analyze extracted visual keyframes & contact sheets with Gemini Flash (or offline fallback)."""
    ensure_dirs()
    manifest = load_manifest()
    codes = episodes.split(",") if episodes else None
    targets = filter_episodes(manifest, codes=codes, pilot=pilot, category=category, limit=limit)
    gemini = GeminiHelper()
    use_gemini = (not offline) and gemini.available
    if not use_gemini:
        console.print("[yellow]Phase 2B running in offline heuristic mode (set GEMINI_API_KEY for VLM vision).[/yellow]")

    for ep in targets:
        slug = ep["slug"]
        code = ep["code"]
        raw_path = VISUALS_RAW_DIR / f"{slug}.json"
        ann_path = VISUALS_RAW_DIR / f"{slug}_annotated.json"

        if ann_path.exists() and not force:
            prev_rows = json.loads(ann_path.read_text(encoding="utf-8"))
            already_gemini = bool(prev_rows) and all(r.get("analysis_mode") == "gemini" for r in prev_rows)
            if already_gemini or not use_gemini:
                console.print(f"  [dim]✓ {code} visuals already annotated ({ann_path.name})[/dim]")
                continue
            console.print(f"  [cyan]↑[/cyan] Upgrading {code} visuals from heuristic -> gemini ({model})...")
        if not raw_path.exists():
            console.print(f"  [yellow]Skipping {code}: run 04_extract_visuals.py first.[/yellow]")
            continue

        raw_list = [RawVisualCandidate(**row) for row in json.loads(raw_path.read_text(encoding="utf-8"))]
        annotations: list[VisualAnnotation] = []
        for cand in raw_list:
            if use_gemini:
                try:
                    ann = _gemini_annotate(ep, cand, gemini, model, thinking_level=thinking_level)
                except (GeminiUnavailableError, Exception) as exc:  # noqa: BLE001
                    if is_fatal_gemini_error(exc):
                        console.print(f"  [red]✗ Fatal Gemini error on {cand.asset_id}:[/red] {exc}")
                        raise typer.Exit(1)
                    console.print(f"  [yellow]⚠ Transient VLM error on {cand.asset_id} ({exc}); falling back.[/yellow]")
                    ann = _heuristic_annotate(cand)
            else:
                ann = _heuristic_annotate(cand)
            annotations.append(ann)

        kept = [a for a in annotations if a.asset_type != "skip_generic_broll" and a.importance != "low"]
        ann_path.write_text(
            json.dumps([a.model_dump() for a in annotations], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        cost_note = f" | cum=${gemini.usage.cost_usd:.4f}" if gemini.usage.calls > 0 else ""
        console.print(
            f"  [green]✓[/green] {code}: annotated {len(annotations)} visuals "
            f"({len(kept)} high/medium retained){cost_note}"
        )

    if gemini.usage.calls > 0:
        console.print(f"[bold cyan]Phase 2B Gemini spend ({model}):[/bold cyan] {gemini.format_usage_summary()}")


if __name__ == "__main__":
    app()
