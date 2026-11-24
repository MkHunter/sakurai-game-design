#!/usr/bin/env python3
"""Phase 1C: Reconcile OCR subtitles + auto-captions into clean English Markdown & JSON transcripts."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import (
    DEFAULT_GEMINI_CLEAN_MODEL,
    RAW_SUBS_DIR,
    TRANSCRIPTS_DIR,
    ensure_dirs,
    filter_episodes,
    format_timestamp,
    load_manifest,
    yt_timestamp_url,
)
from lib.gemini_client import GeminiHelper, GeminiUnavailableError, is_fatal_gemini_error
from lib.schemas import CleanTranscript, RawSubtitleExtraction, SubtitleCue, TranscriptSection

console = Console()
app = typer.Typer(add_completion=False)


def _deterministic_clean(ep: dict, raw: RawSubtitleExtraction) -> CleanTranscript:
    """Zero-cost deterministic cleaning & paragraph grouping when running offline."""
    cues = raw.cues if raw.cues else raw.yt_auto_en_cues
    cleaned_cues: list[SubtitleCue] = []

    for cue in cues:
        txt = re.sub(r"\s+", " ", cue.text).strip()
        txt = txt.replace(" ,", ",").replace(" .", ".").replace(" ?", "?").replace(" !", "!")
        if not txt:
            continue
        # Remove tiny 1-2 char OCR noise artifacts.
        if len(txt) <= 2 and not txt.isalnum():
            continue
        cleaned_cues.append(cue.model_copy(update={"text": txt}))

    # Group cues into topical ~45-60s paragraphs (or split at title cards / long pauses).
    card_times = sorted(tc.timestamp_sec for tc in raw.title_cards)
    card_lookup = {tc.timestamp_sec: tc.text for tc in raw.title_cards}

    sections: list[TranscriptSection] = []
    buf: list[SubtitleCue] = []
    sec_heading = "Introduction"
    card_idx = 0

    def flush(heading: str, items: list[SubtitleCue]) -> None:
        if not items:
            return
        text = " ".join(c.text for c in items)
        text = re.sub(r"\s+", " ", text).strip()
        sections.append(
            TranscriptSection(
                heading=heading,
                start_sec=items[0].start_sec,
                end_sec=items[-1].end_sec,
                text=text,
            )
        )

    for cue in cleaned_cues:
        # Advance title card if we crossed one
        while card_idx < len(card_times) and card_times[card_idx] <= cue.start_sec + 1.5:
            if buf:
                flush(sec_heading, buf)
                buf = []
            sec_heading = card_lookup[card_times[card_idx]]
            card_idx += 1

        if buf and (cue.start_sec - buf[0].start_sec >= 55.0 and buf[-1].text.endswith((".", "!", "?"))):
            flush(sec_heading, buf)
            buf = []
            sec_heading = f"Segment {len(sections) + 1}"

        buf.append(cue)

    flush(sec_heading, buf)

    full_text = "\n\n".join(s.text for s in sections)
    summary = sections[0].text[:240] + ("..." if len(sections[0].text) > 240 else "") if sections else ""

    return CleanTranscript(
        video_id=ep["video_id"],
        code=ep["code"],
        slug=ep["slug"],
        title=ep["title"],
        category_name=ep["category_name"],
        duration_sec=ep["duration_sec"],
        url=ep["url"],
        cleaning_mode="deterministic",
        summary=summary,
        sections=sections,
        full_text=full_text,
        cues=cleaned_cues,
    )


def _gemini_clean(
    ep: dict,
    raw: RawSubtitleExtraction,
    gemini: GeminiHelper,
    model: str,
    thinking_level: str = "minimal",
) -> CleanTranscript:
    ocr_lines = [
        f"[{c.start_sec:.1f}-{c.end_sec:.1f}] {c.text}" for c in raw.cues
    ]
    cards = [f"[{tc.timestamp_sec:.1f}] {tc.text}" for tc in raw.title_cards]
    ja_ref = (
        [f"[{c.start_sec:.1f}] {c.text}" for c in raw.whisper_ja_cues]
        if raw.whisper_ja_cues
        else [f"[{c.start_sec:.1f}] {c.text}" for c in raw.yt_auto_en_cues[:120]]
    )

    prompt = f"""You are editing a transcript of Masahiro Sakurai's game design video:
Episode: {ep['code']} — {ep['title']} ({ep['category_name']})

Below are timestamped OCR lines extracted from the official burned-in English subtitles (translated by 8-4 Ltd.), optional on-screen title cards, and a secondary reference track.

TASK:
1. Preserve the official English localization wording and exact game-dev terminology (e.g., hitstop, startup frames, push and pull, risk and reward).
2. Fix ONLY obvious OCR artifacts (broken letters, stray punctuation, duplicated fragments across adjacent lines). Do NOT invent content.
3. Group the transcript into 3 to 7 clean topical sections with descriptive headings and accurate start_sec/end_sec timestamps.
4. Provide a concise 2-sentence episode summary.

Return strict JSON matching:
{{
  "summary": "string",
  "sections": [
    {{"heading": "string", "start_sec": 0.0, "end_sec": 45.0, "text": "clean English prose..."}}
  ]
}}

ON-SCREEN TITLE CARDS:
{chr(10).join(cards) if cards else "(none)"}

OFFICIAL ENGLISH HARDSUB OCR:
{chr(10).join(ocr_lines)}

SECONDARY REFERENCE TRACK (use only to disambiguate garbled OCR words):
{chr(10).join(ja_ref[:150])}
"""
    data = gemini.generate_json(
        prompt=prompt, model=model, temperature=0.1, thinking_level=thinking_level
    )
    sections = [TranscriptSection(**s) for s in data.get("sections", [])]
    full_text = "\n\n".join(s.text for s in sections)
    return CleanTranscript(
        video_id=ep["video_id"],
        code=ep["code"],
        slug=ep["slug"],
        title=ep["title"],
        category_name=ep["category_name"],
        duration_sec=ep["duration_sec"],
        url=ep["url"],
        cleaning_mode="gemini",
        summary=data.get("summary", ""),
        sections=sections,
        full_text=full_text,
        cues=raw.cues,
    )


def render_markdown(tr: CleanTranscript) -> str:
    lines = [
        "---",
        f"code: {tr.code}",
        f"video_id: {tr.video_id}",
        f'title: "{tr.title.replace(chr(34), chr(39))}"',
        f'category: "{tr.category_name}"',
        f"duration_sec: {tr.duration_sec}",
        f"url: {tr.url}",
        f"cleaning_mode: {tr.cleaning_mode}",
        "---",
        "",
        f"# {tr.code}: {tr.title}",
        "",
        f"**Category:** {tr.category_name} · **Duration:** {format_timestamp(tr.duration_sec)} · **Source:** [YouTube]({tr.url})",
        "",
    ]
    if tr.summary:
        lines.extend(["## Summary", "", tr.summary, ""])

    lines.append("## Transcript")
    lines.append("")
    for sec in tr.sections:
        ts = format_timestamp(sec.start_sec)
        link = yt_timestamp_url(tr.video_id, sec.start_sec)
        lines.append(f"### [{ts}]({link}) {sec.heading}")
        lines.append("")
        lines.append(sec.text)
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


@app.command()
def main(
    pilot: bool = typer.Option(False, "--pilot", help="Run on the 10-episode pilot set."),
    episodes: str | None = typer.Option(None, "--episodes", help="Comma-separated episode codes/IDs."),
    category: str | None = typer.Option(None, "--category"),
    limit: int | None = typer.Option(None, "--limit"),
    offline: bool = typer.Option(False, "--offline", help="Force local deterministic cleanup ($0)."),
    model: str = typer.Option(DEFAULT_GEMINI_CLEAN_MODEL, "--model"),
    thinking_level: str = typer.Option("minimal", "--thinking-level"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Clean and organize raw OCR transcripts into Markdown + structured JSON."""
    ensure_dirs()
    manifest = load_manifest()
    codes = episodes.split(",") if episodes else None
    targets = filter_episodes(manifest, codes=codes, pilot=pilot, category=category, limit=limit)
    gemini = GeminiHelper()

    use_gemini = (not offline) and gemini.available
    if not use_gemini:
        console.print("[yellow]Running in local deterministic mode (pass GEMINI_API_KEY for LLM polish).[/yellow]")

    for ep in targets:
        vid = ep["video_id"]
        code = ep["code"]
        slug = ep["slug"]
        raw_path = RAW_SUBS_DIR / f"{code}_{vid}_extracted.json"
        json_out = TRANSCRIPTS_DIR / f"{slug}.json"
        md_out = TRANSCRIPTS_DIR / f"{slug}.md"

        if json_out.exists() and md_out.exists() and not force:
            existing_mode = CleanTranscript.model_validate_json(
                json_out.read_text(encoding="utf-8")
            ).cleaning_mode
            if existing_mode == "gemini" or not use_gemini:
                console.print(f"  [dim]✓ {code} transcript ready [{existing_mode}] ({md_out.name})[/dim]")
                continue
            console.print(f"  [cyan]↑[/cyan] Upgrading {code} transcript from {existing_mode} -> gemini...")

        if not raw_path.exists():
            console.print(f"  [yellow]Skipping {code}: missing OCR file ({raw_path.name}).[/yellow]")
            continue

        raw = RawSubtitleExtraction.model_validate_json(raw_path.read_text(encoding="utf-8"))
        cleaned: CleanTranscript
        if use_gemini and raw.cues:
            try:
                cleaned = _gemini_clean(ep, raw, gemini, model, thinking_level=thinking_level)
            except (GeminiUnavailableError, Exception) as exc:  # noqa: BLE001
                if is_fatal_gemini_error(exc):
                    console.print(f"  [red]✗ Fatal Gemini error on {code}:[/red] {exc}")
                    raise typer.Exit(1)
                console.print(f"  [yellow]⚠ Transient Gemini error on {code} ({exc}); falling back to local clean.[/yellow]")
                cleaned = _deterministic_clean(ep, raw)
        else:
            cleaned = _deterministic_clean(ep, raw)

        json_out.write_text(cleaned.model_dump_json(indent=2), encoding="utf-8")
        md_out.write_text(render_markdown(cleaned), encoding="utf-8")
        cost_note = f" | cum=${gemini.usage.cost_usd:.4f}" if gemini.usage.calls > 0 else ""
        console.print(
            f"  [green]✓[/green] {code} [{cleaned.cleaning_mode}]: "
            f"{len(cleaned.sections)} sections, {len(cleaned.full_text.split())} words -> {md_out.name}{cost_note}"
        )

    if gemini.usage.calls > 0:
        console.print(f"[bold cyan]Phase 1C Gemini spend ({model}):[/bold cyan] {gemini.format_usage_summary()}")


if __name__ == "__main__":
    app()
