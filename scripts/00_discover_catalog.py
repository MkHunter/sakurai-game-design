#!/usr/bin/env python3
"""Phase 0: Discover all unique Sakurai episodes and map them to official A-N playlists."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import (
    CATALOG_DIR,
    CHANNEL_URL,
    MANIFEST_PATH,
    PLAYLISTS_URL,
    ensure_dirs,
    write_jsonl,
)
from lib.schemas import Episode

console = Console()
app = typer.Typer(add_completion=False)

LETTER_PLAYLIST_RE = re.compile(r"^\[([A-N]):\s*(.+?)\]$")
SPECIAL_PLAYLIST_RE = re.compile(r"^\[S:\s*(.+?)\]$", re.IGNORECASE)
NEWS_PLAYLIST_RE = re.compile(r"^\[news\]$", re.IGNORECASE)


def _yt_dlp_flat(url: str) -> list[dict[str, Any]]:
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--no-warnings",
        url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(proc.stdout)
    return data.get("entries") or []


def _slugify(text: str, max_len: int = 48) -> str:
    clean = re.sub(r"\[[^\]]+\]", "", text).strip().lower()
    clean = re.sub(r"[^a-z0-9]+", "_", clean).strip("_")
    return clean[:max_len].rstrip("_") or "episode"


def _is_compilation(title: str) -> bool:
    return "(Category Compilation)" in title or "Category Compilation" in title


@app.command()
def main(
    force: bool = typer.Option(False, "--force", help="Re-fetch catalog even if manifest exists."),
) -> None:
    """Fetch @sora_sakurai_en playlists & uploads, exclude compilations, write manifest.jsonl."""
    ensure_dirs()
    if MANIFEST_PATH.exists() and not force:
        console.print(f"[yellow]Manifest already exists at {MANIFEST_PATH}. Use --force to refresh.[/yellow]")
        return

    console.print("[bold cyan]Phase 0:[/bold cyan] Fetching channel playlists...")
    playlists = _yt_dlp_flat(PLAYLISTS_URL)

    # Map video_id -> (category_code, category_name, playlist_index)
    membership: dict[str, tuple[str, str, int]] = {}
    playlist_meta: list[dict[str, Any]] = []

    for pl in playlists:
        title = (pl.get("title") or "").strip()
        pl_id = pl.get("id")
        if not pl_id:
            continue

        cat_code: str | None = None
        cat_name: str | None = None

        m_letter = LETTER_PLAYLIST_RE.match(title)
        if m_letter:
            cat_code = m_letter.group(1).upper()
            cat_name = f"{cat_code}: {m_letter.group(2).strip()}"
        elif SPECIAL_PLAYLIST_RE.match(title):
            cat_code = "S"
            cat_name = "S: Special"
        elif NEWS_PLAYLIST_RE.match(title):
            cat_code = "NEWS"
            cat_name = "News"
        else:
            # Skip [Category Compilation] and generic Uploads playlists.
            continue

        pl_url = f"https://www.youtube.com/playlist?list={pl_id}"
        entries = _yt_dlp_flat(pl_url)
        playlist_meta.append(
            {"id": pl_id, "category_code": cat_code, "category_name": cat_name, "count": len(entries)}
        )
        console.print(f"  [green]✓[/green] {cat_name:<28} ({len(entries)} videos)")
        for idx, item in enumerate(entries, start=1):
            vid = item.get("id")
            if not vid:
                continue
            # Prefer A-N over NEWS if a video appears in both.
            if vid not in membership or membership[vid][0] == "NEWS":
                membership[vid] = (cat_code, cat_name, idx)

    console.print("[bold cyan]Phase 0:[/bold cyan] Fetching full channel video list...")
    all_videos = _yt_dlp_flat(CHANNEL_URL)

    episodes: list[Episode] = []
    excluded_compilations: list[dict[str, Any]] = []
    misc_counter = 0

    for item in all_videos:
        vid = item.get("id")
        title = (item.get("title") or "").strip()
        duration = int(item.get("duration") or 0)
        if not vid:
            continue

        if _is_compilation(title):
            excluded_compilations.append({"video_id": vid, "title": title, "duration_sec": duration})
            continue

        if vid in membership:
            cat_code, cat_name, pl_idx = membership[vid]
            code = f"{cat_code}{pl_idx:02d}"
        else:
            misc_counter += 1
            cat_code = "MISC"
            cat_name = "Misc / Uncategorized"
            pl_idx = misc_counter
            code = f"MISC{misc_counter:02d}"

        slug = f"{code}_{_slugify(title)}"
        episodes.append(
            Episode(
                video_id=vid,
                code=code,
                slug=slug,
                title=title,
                category_code=cat_code,
                category_name=cat_name,
                playlist_index=pl_idx,
                duration_sec=duration,
                url=f"https://www.youtube.com/watch?v={vid}",
            )
        )

    # Sort deterministically: A01..N99, then S01.., NEWS01.., MISC01..
    order_map = {chr(ord("A") + i): i for i in range(14)}
    order_map.update({"S": 20, "NEWS": 21, "MISC": 22})
    episodes.sort(key=lambda e: (order_map.get(e.category_code, 99), e.playlist_index or 999, e.code))

    # Deduplicate codes if any playlist had duplicate positions
    seen_codes: Counter[str] = Counter()
    for ep in episodes:
        seen_codes[ep.code] += 1
        if seen_codes[ep.code] > 1:
            ep.code = f"{ep.code}_{seen_codes[ep.code]}"
            ep.slug = f"{ep.code}_{_slugify(ep.title)}"

    write_jsonl(MANIFEST_PATH, [e.model_dump() for e in episodes])

    summary = {
        "total_channel_uploads": len(all_videos),
        "excluded_compilations": len(excluded_compilations),
        "unique_episodes": len(episodes),
        "total_unique_duration_sec": sum(e.duration_sec for e in episodes),
        "total_unique_duration_hrs": round(sum(e.duration_sec for e in episodes) / 3600, 2),
        "by_category": dict(Counter(e.category_name for e in episodes)),
        "playlists": playlist_meta,
    }
    (CATALOG_DIR / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (CATALOG_DIR / "excluded_compilations.json").write_text(
        json.dumps(excluded_compilations, indent=2), encoding="utf-8"
    )

    table = Table(title="Sakurai Channel Catalog Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Episodes", justify="right", style="green")
    table.add_column("Duration (min)", justify="right")

    by_cat_eps: dict[str, list[Episode]] = {}
    for ep in episodes:
        by_cat_eps.setdefault(ep.category_name, []).append(ep)
    for cat_name, eps in by_cat_eps.items():
        mins = sum(e.duration_sec for e in eps) / 60.0
        table.add_row(cat_name, str(len(eps)), f"{mins:.1f}")
    table.add_section()
    table.add_row(
        "[bold]TOTAL UNIQUE[/bold]",
        f"[bold]{len(episodes)}[/bold]",
        f"[bold]{summary['total_unique_duration_hrs']:.2f} hrs[/bold]",
    )
    console.print(table)
    console.print(
        f"[green]Saved {len(episodes)} unique episodes to {MANIFEST_PATH} "
        f"(excluded {len(excluded_compilations)} category compilations).[/green]"
    )


if __name__ == "__main__":
    app()
