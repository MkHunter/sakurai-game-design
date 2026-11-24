#!/usr/bin/env python3
"""Single-command orchestrator to run the Sakurai pipeline end-to-end (pilot or full corpus)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()
app = typer.Typer(add_completion=False)
SCRIPTS_DIR = Path(__file__).resolve().parent


def _run(script: str, extra_args: list[str]) -> None:
    cmd = [sys.executable, str(SCRIPTS_DIR / script), *extra_args]
    console.rule(f"[bold cyan]Running {script}[/bold cyan]")
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        console.print(f"[red]✗ Step failed: {script} (exit {proc.returncode})[/red]")
        raise typer.Exit(proc.returncode)


@app.command()
def main(
    pilot: bool = typer.Option(False, "--pilot", help="Run on the 10-episode stratified pilot."),
    episodes: str | None = typer.Option(None, "--episodes", help="Comma-separated episode codes (e.g., A01,B01,G01)."),
    category: str | None = typer.Option(None, "--category", help="Filter by category code (A-N)."),
    limit: int | None = typer.Option(None, "--limit", help="Max episodes to process."),
    offline: bool = typer.Option(False, "--offline", help="Run without Gemini API calls ($0)."),
    whisper: bool = typer.Option(False, "--whisper", help="Enable RTX GPU faster-whisper JA dual-track."),
    export_loops: bool = typer.Option(False, "--export-loops", help="Export 480p WebP motion loops."),
    skip_catalog: bool = typer.Option(False, "--skip-catalog", help="Skip Phase 0 if manifest exists."),
    force: bool = typer.Option(False, "--force", help="Force re-computation of cached outputs."),
) -> None:
    """Run Phases 0 -> 4 sequentially with full checkpointing."""
    sel_args: list[str] = []
    if pilot:
        sel_args.append("--pilot")
    if episodes:
        sel_args.extend(["--episodes", episodes])
    if category:
        sel_args.extend(["--category", category])
    if limit is not None:
        sel_args.extend(["--limit", str(limit)])

    force_args = ["--force"] if force else []
    offline_args = ["--offline"] if offline else []

    if not skip_catalog:
        _run("00_discover_catalog.py", force_args)

    _run("01_download_media.py", [*sel_args, *force_args])
    _run("02_extract_hardsubs.py", [*sel_args, *(["--whisper"] if whisper else []), *force_args])
    _run("03_clean_transcripts.py", [*sel_args, *offline_args, *force_args])
    _run("04_extract_visuals.py", [*sel_args, *(["--export-loops"] if export_loops else []), *force_args])
    _run("05_analyze_visuals.py", [*sel_args, *offline_args, *force_args])
    _run("06_extract_knowledge.py", [*sel_args, *offline_args, *force_args])
    _run("07_build_graph.py", [])
    _run("08_build_index.py", [])
    _run("verify_dataset.py", [])

    console.rule("[bold green]Pipeline Complete[/bold green]")
    console.print(
        "Browse the interactive graph locally:\n"
        "  [cyan]python3 -m http.server 8765[/cyan]\n"
        "  then open [underline]http://localhost:8765/viewer/[/underline]"
    )


if __name__ == "__main__":
    app()
