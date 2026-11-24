#!/usr/bin/env python3
"""Phase 4: Build SQLite (relational + FTS5) search index and Obsidian-compatible Markdown vault."""

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
    INDEX_DB_PATH,
    TECHNIQUES_PATH,
    TRANSCRIPTS_DIR,
    VAULT_DIR,
    VISUALS_PATH,
    ensure_dirs,
    format_timestamp,
    load_manifest,
    load_taxonomy,
    read_jsonl,
)
from lib.schemas import CleanTranscript

console = Console()
app = typer.Typer(add_completion=False)


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode=WAL;
        DROP TABLE IF EXISTS episodes;
        DROP TABLE IF EXISTS techniques;
        DROP TABLE IF EXISTS visuals;
        DROP TABLE IF EXISTS edges;
        DROP TABLE IF EXISTS fts_techniques;
        DROP TABLE IF EXISTS fts_transcripts;
        DROP TABLE IF EXISTS fts_visuals;

        CREATE TABLE episodes (
            video_id TEXT PRIMARY KEY,
            code TEXT NOT NULL,
            slug TEXT NOT NULL,
            title TEXT NOT NULL,
            category_code TEXT NOT NULL,
            category_name TEXT NOT NULL,
            duration_sec INTEGER NOT NULL,
            url TEXT NOT NULL,
            summary TEXT DEFAULT '',
            full_text TEXT DEFAULT ''
        );

        CREATE TABLE techniques (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            major_topic TEXT NOT NULL,
            subtopics_json TEXT NOT NULL,
            sakurai_categories_json TEXT NOT NULL,
            summary TEXT NOT NULL,
            rules_json TEXT NOT NULL,
            anti_patterns_json TEXT NOT NULL,
            tradeoffs_json TEXT NOT NULL,
            attention_to_detail TEXT NOT NULL,
            game_examples_json TEXT NOT NULL,
            citations_json TEXT NOT NULL
        );

        CREATE TABLE visuals (
            asset_id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL,
            code TEXT NOT NULL,
            start_sec REAL NOT NULL,
            end_sec REAL NOT NULL,
            kind TEXT NOT NULL,
            local_path TEXT NOT NULL,
            loop_path TEXT,
            youtube_url TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            importance TEXT NOT NULL,
            visual_summary TEXT NOT NULL,
            design_detail_highlighted TEXT NOT NULL,
            before_after_delta TEXT NOT NULL,
            on_screen_text TEXT NOT NULL,
            mermaid_or_ascii TEXT NOT NULL
        );

        CREATE TABLE edges (
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            edge_type TEXT NOT NULL,
            weight REAL NOT NULL,
            rationale TEXT NOT NULL
        );
        CREATE INDEX idx_edges_source ON edges(source);
        CREATE INDEX idx_edges_target ON edges(target);
        CREATE INDEX idx_techniques_major ON techniques(major_topic);

        CREATE VIRTUAL TABLE fts_techniques USING fts5(
            id UNINDEXED,
            name,
            major_topic,
            subtopics,
            summary,
            rules,
            anti_patterns,
            attention_to_detail,
            game_examples
        );

        CREATE VIRTUAL TABLE fts_transcripts USING fts5(
            code UNINDEXED,
            video_id UNINDEXED,
            title,
            category_name,
            full_text
        );

        CREATE VIRTUAL TABLE fts_visuals USING fts5(
            asset_id UNINDEXED,
            code UNINDEXED,
            asset_type,
            visual_summary,
            design_detail_highlighted,
            before_after_delta,
            on_screen_text
        );
        """
    )


def _export_obsidian_vault(
    techniques: list[dict],
    visuals_by_id: dict[str, dict],
    edges: list[dict],
    tax: dict,
) -> int:
    topics_dir = VAULT_DIR / "Topics"
    tech_dir = VAULT_DIR / "Techniques"
    topics_dir.mkdir(parents=True, exist_ok=True)
    tech_dir.mkdir(parents=True, exist_ok=True)

    # Index semantic neighbors
    neighbors: dict[str, list[tuple[str, str, str]]] = {}
    tech_names = {t["id"]: t["name"] for t in techniques}
    for e in edges:
        if e["edge_type"] in ("SYNERGIZES_WITH", "TRADEOFF_WITH", "BUILDS_ON"):
            s, t_id = e["source"], e["target"]
            if s in tech_names and t_id in tech_names:
                neighbors.setdefault(s, []).append((e["edge_type"], tech_names[t_id], e.get("rationale", "")))
                neighbors.setdefault(t_id, []).append((e["edge_type"], tech_names[s], e.get("rationale", "")))

    major_map = {m["id"]: m["name"] for m in tax.get("major_topics", [])}
    written = 0

    # Topic MOCs (Maps of Content)
    by_major: dict[str, list[dict]] = {}
    for t in techniques:
        by_major.setdefault(t["major_topic"], []).append(t)

    index_lines = ["# Sakurai Game Design Knowledge Vault", "", "## Major Topics", ""]
    for m in tax.get("major_topics", []):
        m_techs = by_major.get(m["id"], [])
        if not m_techs:
            continue
        safe_name = m["name"].replace("/", "-")
        index_lines.append(f"- [[{safe_name}]] ({len(m_techs)} techniques)")
        lines = [f"# {m['name']}", "", "## Techniques", ""]
        for t in sorted(m_techs, key=lambda x: x["name"]):
            t_file = t["name"].replace("/", "-")
            lines.append(f"- [[{t_file}]] — {t['summary'][:120]}")
        (topics_dir / f"{safe_name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        written += 1

    (VAULT_DIR / "INDEX.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    written += 1

    # Individual technique notes
    for t in techniques:
        t_file = t["name"].replace("/", "-")
        major_label = major_map.get(t["major_topic"], t["major_topic"]).replace("/", "-")
        lines = [
            "---",
            f"id: {t['id']}",
            f"major_topic: {t['major_topic']}",
            f"subtopics: {json.dumps(t.get('subtopics', []))}",
            f"sakurai_categories: {json.dumps(t.get('sakurai_categories', []))}",
            "---",
            "",
            f"# {t['name']}",
            "",
            f"**Major Topic:** [[{major_label}]]  ",
            f"**Subtopics:** {', '.join(t.get('subtopics', []))}  ",
            f"**Sakurai Categories:** {', '.join(t.get('sakurai_categories', []))}",
            "",
            "## Summary",
            "",
            t["summary"],
            "",
        ]
        if t.get("actionable_rules"):
            lines.extend(["## Actionable Rules", ""])
            lines.extend([f"- {r}" for r in t["actionable_rules"]])
            lines.append("")
        if t.get("anti_patterns"):
            lines.extend(["## Anti-Patterns (Avoid)", ""])
            lines.extend([f"- {a}" for a in t["anti_patterns"]])
            lines.append("")
        if t.get("tradeoffs"):
            lines.extend(["## Tradeoffs", ""])
            for trd in t["tradeoffs"]:
                lines.append(f"- **{trd['tension']}:** {trd['guidance']}")
            lines.append("")
        if t.get("attention_to_detail"):
            lines.extend(["## Attention to Detail", "", t["attention_to_detail"], ""])
        if t.get("game_examples"):
            lines.extend(["## Game Examples", "", ", ".join(t["game_examples"]), ""])

        # Citations & Visuals
        lines.extend(["## Evidence & Visual References", ""])
        for c in t.get("citations", []):
            ts = format_timestamp(c.get("timestamp_sec", 0))
            lines.append(f"- **{c['episode_code']}** ([{ts}]({c.get('url', '')})): {c.get('quote', '')}")
            for vid in c.get("visual_asset_ids", []):
                v = visuals_by_id.get(vid)
                if not v:
                    continue
                rel_img = f"../../{v['local_path']}"
                lines.append(f"  - Visual `{vid}` ({v['asset_type']}): {v['visual_summary']}")
                lines.append(f"    ![]({rel_img})")
                if v.get("mermaid_or_ascii"):
                    lines.extend(["    ```text", f"    {v['mermaid_or_ascii']}", "    ```"])
        lines.append("")

        rel_list = neighbors.get(t["id"], [])
        if rel_list:
            lines.extend(["## Related Techniques", ""])
            for etype, target_name, rationale in rel_list:
                lines.append(f"- `{etype}` [[{target_name.replace('/', '-')}]] — {rationale}")
            lines.append("")

        (tech_dir / f"{t_file}.md").write_text("\n".join(lines), encoding="utf-8")
        written += 1

    return written


@app.command()
def main(
    export_vault: bool = typer.Option(True, "--vault/--no-vault", help="Also generate Obsidian Markdown vault."),
) -> None:
    """Build SQLite FTS5 index (knowledge/index.db) and optional Obsidian vault (vault/)."""
    ensure_dirs()
    manifest = load_manifest()
    techniques = read_jsonl(TECHNIQUES_PATH)
    visuals = read_jsonl(VISUALS_PATH)
    edges = read_jsonl(EDGES_PATH)
    tax = load_taxonomy()

    # Load cleaned transcripts by video_id
    transcripts_by_vid: dict[str, CleanTranscript] = {}
    for p in TRANSCRIPTS_DIR.glob("*.json"):
        tr = CleanTranscript.model_validate_json(p.read_text(encoding="utf-8"))
        transcripts_by_vid[tr.video_id] = tr

    conn = sqlite3.connect(INDEX_DB_PATH)
    try:
        _init_db(conn)

        for ep in manifest:
            tr = transcripts_by_vid.get(ep["video_id"])
            summary = tr.summary if tr else ""
            full_text = tr.full_text if tr else ""
            conn.execute(
                "INSERT INTO episodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ep["video_id"],
                    ep["code"],
                    ep["slug"],
                    ep["title"],
                    ep["category_code"],
                    ep["category_name"],
                    ep["duration_sec"],
                    ep["url"],
                    summary,
                    full_text,
                ),
            )
            if full_text:
                conn.execute(
                    "INSERT INTO fts_transcripts VALUES (?, ?, ?, ?, ?)",
                    (ep["code"], ep["video_id"], ep["title"], ep["category_name"], full_text),
                )

        for t in techniques:
            conn.execute(
                "INSERT INTO techniques VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    t["id"],
                    t["name"],
                    t["major_topic"],
                    json.dumps(t.get("subtopics", [])),
                    json.dumps(t.get("sakurai_categories", [])),
                    t.get("summary", ""),
                    json.dumps(t.get("actionable_rules", [])),
                    json.dumps(t.get("anti_patterns", [])),
                    json.dumps(t.get("tradeoffs", [])),
                    t.get("attention_to_detail", ""),
                    json.dumps(t.get("game_examples", [])),
                    json.dumps(t.get("citations", [])),
                ),
            )
            conn.execute(
                "INSERT INTO fts_techniques VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    t["id"],
                    t["name"],
                    t["major_topic"],
                    " ".join(t.get("subtopics", [])),
                    t.get("summary", ""),
                    " ".join(t.get("actionable_rules", [])),
                    " ".join(t.get("anti_patterns", [])),
                    t.get("attention_to_detail", ""),
                    " ".join(t.get("game_examples", [])),
                ),
            )

        for v in visuals:
            conn.execute(
                "INSERT INTO visuals VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    v["asset_id"],
                    v["video_id"],
                    v["code"],
                    v["start_sec"],
                    v["end_sec"],
                    v["kind"],
                    v["local_path"],
                    v.get("loop_path"),
                    v["youtube_url"],
                    v["asset_type"],
                    v["importance"],
                    v.get("visual_summary", ""),
                    v.get("design_detail_highlighted", ""),
                    v.get("before_after_delta", ""),
                    v.get("on_screen_text", ""),
                    v.get("mermaid_or_ascii", ""),
                ),
            )
            conn.execute(
                "INSERT INTO fts_visuals VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    v["asset_id"],
                    v["code"],
                    v["asset_type"],
                    v.get("visual_summary", ""),
                    v.get("design_detail_highlighted", ""),
                    v.get("before_after_delta", ""),
                    v.get("on_screen_text", ""),
                ),
            )

        for e in edges:
            conn.execute(
                "INSERT INTO edges VALUES (?, ?, ?, ?, ?)",
                (e["source"], e["target"], e["edge_type"], e.get("weight", 1.0), e.get("rationale", "")),
            )

        conn.commit()
    finally:
        conn.close()

    console.print(
        f"[green]✓ Built SQLite FTS5 index at {INDEX_DB_PATH}[/green] "
        f"({len(transcripts_by_vid)} transcripts, {len(techniques)} techniques, {len(visuals)} visuals, {len(edges)} edges)"
    )

    if export_vault and techniques:
        vis_map = {v["asset_id"]: v for v in visuals}
        n_files = _export_obsidian_vault(techniques, vis_map, edges, tax)
        console.print(f"[green]✓ Exported Obsidian vault to {VAULT_DIR} ({n_files} markdown notes)[/green]")


if __name__ == "__main__":
    app()
