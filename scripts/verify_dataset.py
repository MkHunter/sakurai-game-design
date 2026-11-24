#!/usr/bin/env python3
"""Integrity verification suite for transcripts, visual assets, citations, taxonomy, and index."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import (
    EDGES_PATH,
    GRAPH_JSON_PATH,
    INDEX_DB_PATH,
    ROOT_DIR,
    TECHNIQUES_PATH,
    TRANSCRIPTS_DIR,
    VISUALS_PATH,
    load_manifest,
    read_jsonl,
    taxonomy_lookup,
)

console = Console()
app = typer.Typer(add_completion=False)


@app.command()
def main() -> None:
    """Validate dataset integrity across manifest, transcripts, visuals, graph, and SQLite index."""
    errors: list[str] = []
    warnings: list[str] = []

    manifest = load_manifest()
    if not manifest:
        errors.append("Manifest is empty or missing.")
    ep_by_code = {e["code"]: e for e in manifest}
    majors, sub_to_major = taxonomy_lookup()

    techniques = read_jsonl(TECHNIQUES_PATH)
    visuals = read_jsonl(VISUALS_PATH)
    edges = read_jsonl(EDGES_PATH)
    vis_by_id = {v["asset_id"]: v for v in visuals}

    # 1. Verify visual files exist on disk and timestamps are within duration.
    ep_by_vid = {e["video_id"]: e for e in manifest}
    for v in visuals:
        p = ROOT_DIR / v["local_path"]
        if not p.exists():
            errors.append(f"Missing visual file on disk: {v['local_path']} ({v['asset_id']})")
        ep = ep_by_vid.get(v["video_id"])
        if ep and ep["duration_sec"] > 0 and v["start_sec"] > ep["duration_sec"] + 5:
            errors.append(f"Visual {v['asset_id']} start_sec {v['start_sec']} exceeds duration {ep['duration_sec']}")

    # 2. Verify technique taxonomy compliance and citations.
    for t in techniques:
        if t["major_topic"] not in majors:
            errors.append(f"Technique {t['id']} has unknown major_topic: {t['major_topic']}")
        for s in t.get("subtopics", []):
            if s not in sub_to_major:
                errors.append(f"Technique {t['id']} has unknown subtopic: {s}")
        for c in t.get("citations", []):
            if c["episode_code"] not in ep_by_code:
                errors.append(f"Technique {t['id']} cites unknown episode code: {c['episode_code']}")
            for vid in c.get("visual_asset_ids", []):
                if vid not in vis_by_id:
                    warnings.append(f"Technique {t['id']} references filtered/missing visual_asset_id: {vid}")

    # 3. Verify graph.json and SQLite DB exist and are readable.
    if not GRAPH_JSON_PATH.exists():
        errors.append("knowledge/graph.json missing.")
    else:
        g = json.loads(GRAPH_JSON_PATH.read_text(encoding="utf-8"))
        node_ids = {n["id"] for n in g.get("nodes", [])}
        for e in g.get("edges", []):
            if e["source"] not in node_ids or e["target"] not in node_ids:
                errors.append(f"Dangling graph edge: {e['source']} -> {e['target']} ({e['edge_type']})")

    if not INDEX_DB_PATH.exists():
        errors.append("knowledge/index.db missing.")
    else:
        conn = sqlite3.connect(INDEX_DB_PATH)
        try:
            n_tech = conn.execute("SELECT COUNT(*) FROM techniques").fetchone()[0]
            if n_tech != len(techniques):
                errors.append(f"SQLite techniques count ({n_tech}) != techniques.jsonl ({len(techniques)})")
        finally:
            conn.close()

    n_transcripts = len(list(TRANSCRIPTS_DIR.glob("*.md")))
    console.print(
        f"[bold cyan]Dataset Verification Summary[/bold cyan]\n"
        f"  Catalog episodes : {len(manifest)}\n"
        f"  Transcripts (.md): {n_transcripts}\n"
        f"  Techniques       : {len(techniques)}\n"
        f"  Visual assets    : {len(visuals)}\n"
        f"  Graph edges      : {len(edges)}\n"
        f"  Warnings         : {len(warnings)}\n"
        f"  Errors           : {len(errors)}"
    )

    for w in warnings[:10]:
        console.print(f"  [yellow]WARN:[/yellow] {w}")
    for err in errors[:20]:
        console.print(f"  [red]ERR :[/red] {err}")

    if errors:
        raise typer.Exit(1)
    console.print("[bold green]✓ All integrity checks passed![/bold green]")


if __name__ == "__main__":
    app()
