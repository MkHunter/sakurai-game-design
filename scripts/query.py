#!/usr/bin/env python3
"""Fast query CLI over knowledge/index.db for humans and downstream AI agents."""

from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import INDEX_DB_PATH, load_taxonomy

console = Console()
app = typer.Typer(add_completion=False)


def _conn() -> sqlite3.Connection:
    if not INDEX_DB_PATH.exists():
        console.print(f"[red]Index missing at {INDEX_DB_PATH}. Run scripts/08_build_index.py first.[/red]")
        raise typer.Exit(1)
    c = sqlite3.connect(INDEX_DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _fts_safe_query(raw: str) -> str:
    """Quote hyphenated/punctuated user terms so FTS5 never interprets '-' as NOT/column."""
    tokens = [tok.strip().replace('"', "") for tok in raw.split() if tok.strip()]
    if not tokens:
        return '""'
    return " ".join(f'"{t}"' for t in tokens)


@app.command()
def search(
    query: str = typer.Argument(..., help="FTS5 search query (e.g., 'hitstop', 'risk reward', 'menu')."),
    limit: int = typer.Option(10, "--limit"),
    as_json: bool = typer.Option(False, "--json"),
) -> None:
    """Full-text search across techniques, transcripts, and visual descriptions."""
    conn = _conn()
    fts_q = _fts_safe_query(query)
    try:
        tech_rows = conn.execute(
            """
            SELECT t.* FROM fts_techniques f
            JOIN techniques t ON t.id = f.id
            WHERE fts_techniques MATCH ?
            ORDER BY rank LIMIT ?
            """,
            (fts_q, limit),
        ).fetchall()

        vis_rows = conn.execute(
            """
            SELECT v.* FROM fts_visuals f
            JOIN visuals v ON v.asset_id = f.asset_id
            WHERE fts_visuals MATCH ?
            ORDER BY rank LIMIT ?
            """,
            (fts_q, limit),
        ).fetchall()

        tr_rows = conn.execute(
            """
            SELECT code, title, category_name, snippet(fts_transcripts, 4, '[', ']', '...', 24) AS snip
            FROM fts_transcripts
            WHERE fts_transcripts MATCH ?
            ORDER BY rank LIMIT ?
            """,
            (fts_q, limit),
        ).fetchall()
    finally:
        conn.close()

    if as_json:
        print(
            json.dumps(
                {
                    "techniques": [dict(r) for r in tech_rows],
                    "visuals": [dict(r) for r in vis_rows],
                    "transcripts": [dict(r) for r in tr_rows],
                },
                indent=2,
            )
        )
        return

    console.print(f"\n[bold cyan]Techniques matching '{query}' ({len(tech_rows)}):[/bold cyan]")
    for r in tech_rows:
        console.print(f"  • [bold]{r['name']}[/bold] ([dim]{r['id']}[/dim] · {r['major_topic']})")
        console.print(f"    {r['summary']}")

    console.print(f"\n[bold cyan]Visual References matching '{query}' ({len(vis_rows)}):[/bold cyan]")
    for v in vis_rows:
        console.print(f"  • [bold]{v['asset_id']}[/bold] ({v['code']} · {v['asset_type']}): {v['visual_summary'][:140]}")
        console.print(f"    File: {v['local_path']} | {v['youtube_url']}")

    console.print(f"\n[bold cyan]Transcript Snippets matching '{query}' ({len(tr_rows)}):[/bold cyan]")
    for tr in tr_rows:
        console.print(f"  • [bold]{tr['code']}[/bold] — {tr['title']}: {tr['snip']}")


@app.command()
def neighbors(
    tech_id: str = typer.Argument(..., help="Technique ID to inspect graph neighborhood."),
) -> None:
    """Show a technique's rules, visuals, and 1-hop graph neighbors."""
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM techniques WHERE id = ?", (tech_id,)).fetchone()
        if not row:
            console.print(f"[red]Technique '{tech_id}' not found.[/red]")
            raise typer.Exit(1)
        edges = conn.execute(
            "SELECT * FROM edges WHERE source = ? OR target = ?", (tech_id, tech_id)
        ).fetchall()
    finally:
        conn.close()

    console.print(f"\n[bold green]{row['name']}[/bold green] ({row['id']})")
    console.print(row["summary"])
    for r in json.loads(row["rules_json"]):
        console.print(f"  [green]+[/green] {r}")
    for a in json.loads(row["anti_patterns_json"]):
        console.print(f"  [red]-[/red] {a}")
    console.print("\n[bold cyan]Graph Edges:[/bold cyan]")
    for e in edges:
        other = e["target"] if e["source"] == tech_id else e["source"]
        console.print(f"  {e['edge_type']:<16} -> {other}  [dim]{e['rationale']}[/dim]")


@app.command("skill-audit")
def skill_audit(min_techniques: int = typer.Option(1, "--min", help="Min techniques per subtopic.")) -> None:
    """Phase 6 helper: rank subtopic clusters by density & visual coverage for AI skill authoring."""
    conn = _conn()
    tax = load_taxonomy()
    sub_names = {
        s["id"]: (m["name"], s["name"])
        for m in tax["major_topics"]
        for s in m["subtopics"]
    }
    try:
        rows = conn.execute("SELECT * FROM techniques").fetchall()
    finally:
        conn.close()

    counts: Counter[str] = Counter()
    rule_counts: Counter[str] = Counter()
    vis_counts: Counter[str] = Counter()
    for r in rows:
        rules = json.loads(r["rules_json"])
        cites = json.loads(r["citations_json"])
        n_vis = sum(len(c.get("visual_asset_ids", [])) for c in cites)
        for s in json.loads(r["subtopics_json"]):
            counts[s] += 1
            rule_counts[s] += len(rules)
            vis_counts[s] += n_vis

    table = Table(title="Phase 6 Skill Candidate Clusters (Subtopic Density Audit)")
    table.add_column("Subtopic ID", style="cyan")
    table.add_column("Major Topic")
    table.add_column("Techniques", justify="right", style="green")
    table.add_column("Rules", justify="right")
    table.add_column("Linked Visuals", justify="right")

    for sub_id, cnt in counts.most_common():
        if cnt < min_techniques:
            continue
        major_name, sub_name = sub_names.get(sub_id, ("Unknown", sub_id))
        table.add_row(f"{sub_id} ({sub_name})", major_name, str(cnt), str(rule_counts[sub_id]), str(vis_counts[sub_id]))

    console.print(table)


if __name__ == "__main__":
    app()
