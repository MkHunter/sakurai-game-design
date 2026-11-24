#!/usr/bin/env python3
"""Force-add only the visual assets referenced by knowledge/graph.json to git.

data/media/ is gitignored (≈200 MB of WebP keyframes/contact sheets). The viewer only renders
visuals attached to technique nodes, so we track exactly those files and nothing else.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import GRAPH_JSON_PATH, ROOT_DIR

console = Console()
app = typer.Typer(add_completion=False)


@app.command()
def main(dry_run: bool = typer.Option(False, "--dry-run", help="List files without git-adding.")) -> None:
    """Stage every visual referenced by graph.json (and untrack stale ones)."""
    graph = json.loads(GRAPH_JSON_PATH.read_text(encoding="utf-8"))
    wanted = sorted(
        {v["local_path"] for n in graph["nodes"] for v in n.get("visuals", []) if v.get("local_path")}
    )
    present = [p for p in wanted if (ROOT_DIR / p).exists()]
    missing = len(wanted) - len(present)
    size_mb = sum((ROOT_DIR / p).stat().st_size for p in present) / 1e6

    console.print(
        f"[cyan]{len(present)} referenced visuals ({size_mb:.1f} MB)[/cyan]"
        + (f" [yellow]· {missing} missing on disk[/yellow]" if missing else "")
    )
    if dry_run:
        return

    # Untrack media files no longer referenced by the graph.
    tracked = subprocess.run(
        ["git", "ls-files", "data/media"], cwd=ROOT_DIR, capture_output=True, text=True, check=True
    ).stdout.split()
    stale = sorted(set(tracked) - set(present))
    if stale:
        subprocess.run(["git", "rm", "--cached", "--quiet", *stale], cwd=ROOT_DIR, check=True)
        console.print(f"[yellow]Untracked {len(stale)} stale visuals[/yellow]")

    for i in range(0, len(present), 400):
        subprocess.run(["git", "add", "-f", *present[i : i + 400]], cwd=ROOT_DIR, check=True)
    console.print("[green]✓ Staged referenced visuals[/green]")


if __name__ == "__main__":
    app()
