#!/usr/bin/env python3
"""Phase 1A: Resumable downloader for 720p MP4 videos and YouTube auto-captions."""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import (
    RAW_SUBS_DIR,
    RAW_VIDEOS_DIR,
    ROOT_DIR,
    ensure_dirs,
    filter_episodes,
    load_manifest,
)

console = Console()
app = typer.Typer(add_completion=False)


def _node_runtime_args() -> list[str]:
    node_path = shutil.which("node")
    if node_path:
        return ["--js-runtimes", f"node:{node_path}", "--remote-components", "ejs:github"]
    return []


def _resolve_cookie_args(cookies_file: str | None, cookies_from_browser: str | None) -> list[str]:
    if cookies_file:
        return ["--cookies", cookies_file]
    if cookies_from_browser:
        return ["--cookies-from-browser", cookies_from_browser]
    default_cookies = ROOT_DIR / "cookies.txt"
    if default_cookies.exists():
        return ["--cookies", str(default_cookies)]
    return []


def download_episode(
    ep: dict,
    skip_video: bool = False,
    max_height: int = 720,
    sleep_min: int = 4,
    sleep_max: int = 8,
    cookies_file: str | None = None,
    cookies_from_browser: str | None = None,
    force: bool = False,
) -> Path | None:
    vid = ep["video_id"]
    code = ep["code"]
    url = ep["url"]
    video_path = RAW_VIDEOS_DIR / f"{code}_{vid}.mp4"
    sub_prefix = RAW_SUBS_DIR / f"{code}_{vid}"

    runtime_args = _node_runtime_args()
    cookie_args = _resolve_cookie_args(cookies_file, cookies_from_browser)

    # 1. Grab auto-captions (en + ja-orig) as secondary cross-check signal (skip if video already cached).
    en_sub = RAW_SUBS_DIR / f"{code}_{vid}.en.json3"
    if (force or not en_sub.exists()) and (skip_video or not video_path.exists()):
        sub_cmd = [
            "yt-dlp",
            *runtime_args,
            *cookie_args,
            "--skip-download",
            "--write-auto-subs",
            "--sub-langs",
            "en,ja-orig",
            "--sub-format",
            "json3",
            "--no-warnings",
            "-o",
            str(sub_prefix),
            url,
        ]
        subprocess.run(sub_cmd, capture_output=True, text=True, check=False)

    if skip_video:
        return video_path if video_path.exists() else None

    if video_path.exists() and not force:
        console.print(f"  [dim]✓ {code} video cached ({video_path.name})[/dim]")
        return video_path

    fmt = (
        f"bestvideo[height<={max_height}][ext=mp4]+bestaudio[ext=m4a]/"
        f"best[height<={max_height}][ext=mp4]/best[height<={max_height}]"
    )
    attempts = [
        ("default", []),
        ("tv_web", ["--extractor-args", "youtube:player_client=tv,web"]),
        ("android_vr", ["--extractor-args", "youtube:player_client=android_vr"]),
    ]
    console.print(f"  [cyan]↓[/cyan] Downloading {code} — {ep['title']} ({ep['duration_sec']}s)...")
    last_err = ""
    for idx, (label, extra) in enumerate(attempts):
        vid_cmd = [
            "yt-dlp",
            *runtime_args,
            *cookie_args,
            *extra,
            "-f",
            fmt,
            "--retries",
            "3",
            "--fragment-retries",
            "3",
            "--merge-output-format",
            "mp4",
            "--sleep-interval",
            str(sleep_min),
            "--max-sleep-interval",
            str(sleep_max),
            "--no-warnings",
            "-o",
            str(video_path),
            url,
        ]
        proc = subprocess.run(vid_cmd, check=False, capture_output=True, text=True)
        if proc.returncode == 0 and video_path.exists():
            console.print(f"  [green]✓[/green] Saved {video_path.name}")
            return video_path
        last_err = proc.stderr.strip()[:300]
        is_bot_gate = "Sign in to confirm" in last_err or "not a bot" in last_err
        is_403 = "403" in last_err
        if not (is_403 or is_bot_gate) or idx == len(attempts) - 1:
            break
        wait_s = 30 if is_bot_gate else 5
        console.print(
            f"  [yellow]↻ {code} hit {'bot check' if is_bot_gate else 'HTTP 403'} "
            f"on {label}; waiting {wait_s}s and trying next client...[/yellow]"
        )
        time.sleep(wait_s)

    console.print(f"  [red]✗ Failed {code}:[/red] {last_err}")
    return None


@app.command()
def main(
    pilot: bool = typer.Option(False, "--pilot", help="Download only the 10-episode pilot set."),
    episodes: str | None = typer.Option(
        None, "--episodes", help="Comma-separated episode codes or video IDs (e.g., A01,B01,G01)."
    ),
    category: str | None = typer.Option(None, "--category", help="Single category letter (e.g., G)."),
    limit: int | None = typer.Option(None, "--limit", help="Maximum number of episodes to download."),
    max_height: int = typer.Option(720, "--max-height", help="Max video height in pixels."),
    sleep_min: int = typer.Option(4, "--sleep-min", help="Min polite delay (sec) between requests."),
    sleep_max: int = typer.Option(8, "--sleep-max", help="Max polite delay (sec) between requests."),
    skip_video: bool = typer.Option(False, "--skip-video", help="Fetch auto-captions only."),
    cookies: str | None = typer.Option(
        None, "--cookies", help="Path to Netscape cookies.txt (auto-detected if ./cookies.txt exists)."
    ),
    cookies_from_browser: str | None = typer.Option(
        None, "--cookies-from-browser", help="Optional browser name for yt-dlp cookies."
    ),
    force: bool = typer.Option(False, "--force", help="Re-download existing files."),
) -> None:
    """Download 720p videos and YouTube auto-captions for selected episodes."""
    ensure_dirs()
    manifest = load_manifest()
    if not manifest:
        console.print("[red]Manifest missing. Run scripts/00_discover_catalog.py first.[/red]")
        raise typer.Exit(1)

    codes = episodes.split(",") if episodes else None
    targets = filter_episodes(manifest, codes=codes, pilot=pilot, category=category, limit=limit)
    console.print(f"[bold cyan]Phase 1A:[/bold cyan] Processing {len(targets)} episode(s)...")

    ok = 0
    for ep in targets:
        res = download_episode(
            ep,
            skip_video=skip_video,
            max_height=max_height,
            sleep_min=sleep_min,
            sleep_max=sleep_max,
            cookies_file=cookies,
            cookies_from_browser=cookies_from_browser,
            force=force,
        )
        if res is not None or skip_video:
            ok += 1
    console.print(f"[green]Phase 1A complete: {ok}/{len(targets)} ready.[/green]")


if __name__ == "__main__":
    app()
