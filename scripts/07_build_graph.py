#!/usr/bin/env python3
"""Phase 3B: Cross-episode deduplication, canonical technique merging, and knowledge graph build."""

from __future__ import annotations

import json
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import (
    EDGES_PATH,
    EPISODES_KNOWLEDGE_DIR,
    GRAPH_JSON_PATH,
    TECHNIQUES_PATH,
    VISUALS_PATH,
    VISUALS_RAW_DIR,
    ensure_dirs,
    load_manifest,
    load_taxonomy,
    write_jsonl,
)
from lib.schemas import EpisodeKnowledge, GraphEdge, Technique, VisualAnnotation

console = Console()
app = typer.Typer(add_completion=False)


def _name_sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _dedup_list(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def _merge_techniques(target: Technique, incoming: Technique) -> None:
    target.subtopics = _dedup_list(target.subtopics + incoming.subtopics)
    target.sakurai_categories = _dedup_list(target.sakurai_categories + incoming.sakurai_categories)
    target.actionable_rules = _dedup_list(target.actionable_rules + incoming.actionable_rules)
    target.anti_patterns = _dedup_list(target.anti_patterns + incoming.anti_patterns)
    target.game_examples = _dedup_list(target.game_examples + incoming.game_examples)
    if len(incoming.summary) > len(target.summary):
        target.summary = incoming.summary
    if incoming.attention_to_detail and incoming.attention_to_detail not in target.attention_to_detail:
        target.attention_to_detail = (
            f"{target.attention_to_detail} | {incoming.attention_to_detail}".strip(" |")
        )
    existing_tensions = {t.tension.lower() for t in target.tradeoffs}
    for trd in incoming.tradeoffs:
        if trd.tension.lower() not in existing_tensions:
            target.tradeoffs.append(trd)
            existing_tensions.add(trd.tension.lower())
    existing_cites = {(c.episode_code, int(c.timestamp_sec)) for c in target.citations}
    for c in incoming.citations:
        key = (c.episode_code, int(c.timestamp_sec))
        if key not in existing_cites:
            target.citations.append(c)
            existing_cites.add(key)


@app.command()
def main(
    similarity_threshold: float = typer.Option(
        0.84, "--merge-threshold", help="Name similarity threshold for cross-episode technique merging."
    ),
) -> None:
    """Consolidate per-episode extractions into canonical techniques, edges, and graph.json."""
    ensure_dirs()
    tax = load_taxonomy()
    manifest_by_vid = {ep["video_id"]: ep for ep in load_manifest()}

    # 1. Load all annotated visual assets (retaining medium & high importance).
    all_visuals: dict[str, VisualAnnotation] = {}
    for p in sorted(VISUALS_RAW_DIR.glob("*_annotated.json")):
        for row in json.loads(p.read_text(encoding="utf-8")):
            v = VisualAnnotation(**row)
            if v.asset_type != "skip_generic_broll" and v.importance != "low":
                all_visuals[v.asset_id] = v

    # 2. Load all episode knowledge files & merge near-duplicate techniques.
    ep_files = sorted(EPISODES_KNOWLEDGE_DIR.glob("*.json"))
    if not ep_files:
        console.print("[red]No episode knowledge files found. Run 06_extract_knowledge.py first.[/red]")
        raise typer.Exit(1)

    canonical: list[Technique] = []
    name_to_id: dict[str, str] = {}
    raw_relations = []
    processed_episodes: dict[str, EpisodeKnowledge] = {}

    for p in ep_files:
        ek = EpisodeKnowledge.model_validate_json(p.read_text(encoding="utf-8"))
        processed_episodes[ek.code] = ek
        raw_relations.extend(ek.relations)

        for tech in ek.techniques:
            matched: Technique | None = None
            for existing in canonical:
                if existing.id == tech.id or _name_sim(existing.name, tech.name) >= similarity_threshold:
                    matched = existing
                    break
            if matched is not None:
                _merge_techniques(matched, tech)
                name_to_id[tech.name.lower()] = matched.id
            else:
                # Ensure unique ID
                base_id = tech.id
                idx = 2
                existing_ids = {t.id for t in canonical}
                while tech.id in existing_ids:
                    tech.id = f"{base_id}_{idx}"
                    idx += 1
                canonical.append(tech)
                name_to_id[tech.name.lower()] = tech.id

    # 3. Build nodes & typed edges for the interactive graph.
    nodes: list[dict[str, Any]] = []
    edges: list[GraphEdge] = []
    edge_keys: set[tuple[str, str, str]] = set()

    def add_edge(src: str, dst: str, etype: str, weight: float = 1.0, rationale: str = "") -> None:
        if src == dst:
            return
        k = (src, dst, etype)
        if k in edge_keys:
            return
        edge_keys.add(k)
        edges.append(GraphEdge(source=src, target=dst, edge_type=etype, weight=weight, rationale=rationale))  # type: ignore[arg-type]

    # Major Topic and Subtopic nodes (include only active ones that have >=1 technique, plus all majors for context).
    active_subtopics = {s for t in canonical for s in t.subtopics}
    active_majors = {t.major_topic for t in canonical}
    major_colors: dict[str, str] = {}

    for m in tax["major_topics"]:
        mid = f"topic:{m['id']}"
        major_colors[m["id"]] = m.get("color", "#4361ee")
        if m["id"] in active_majors:
            nodes.append(
                {
                    "id": mid,
                    "label": m["name"],
                    "node_type": "major_topic",
                    "major_topic": m["id"],
                    "color": major_colors[m["id"]],
                }
            )
        for s in m.get("subtopics", []):
            if s["id"] in active_subtopics:
                sid = f"subtopic:{s['id']}"
                nodes.append(
                    {
                        "id": sid,
                        "label": s["name"],
                        "node_type": "subtopic",
                        "major_topic": m["id"],
                        "color": major_colors[m["id"]],
                    }
                )
                add_edge(sid, mid, "BELONGS_TO", weight=1.5)

    # Technique nodes + BELONGS_TO + CITED_IN + VISUALIZED_BY + EXEMPLIFIED_BY
    tech_by_id = {t.id: t for t in canonical}
    for t in canonical:
        vis_ids: list[str] = []
        for c in t.citations:
            for vid in c.visual_asset_ids:
                if vid in all_visuals and vid not in vis_ids:
                    vis_ids.append(vid)
        nodes.append(
            {
                "id": t.id,
                "label": t.name,
                "node_type": "technique",
                "major_topic": t.major_topic,
                "subtopics": t.subtopics,
                "sakurai_categories": t.sakurai_categories,
                "color": major_colors.get(t.major_topic, "#4361ee"),
                "citation_count": len(t.citations),
                "visual_count": len(vis_ids),
                "summary": t.summary,
                "actionable_rules": t.actionable_rules,
                "anti_patterns": t.anti_patterns,
                "tradeoffs": [trd.model_dump() for trd in t.tradeoffs],
                "attention_to_detail": t.attention_to_detail,
                "game_examples": t.game_examples,
                "citations": [c.model_dump() for c in t.citations],
                "visuals": [all_visuals[vid].model_dump() for vid in vis_ids],
            }
        )
        for s in t.subtopics:
            add_edge(t.id, f"subtopic:{s}", "BELONGS_TO", weight=1.0)
        if not t.subtopics:
            add_edge(t.id, f"topic:{t.major_topic}", "BELONGS_TO", weight=1.0)

    # Semantic relations between techniques
    def resolve_tech_name(name: str) -> str | None:
        low = name.lower().strip()
        if low in name_to_id:
            return name_to_id[low]
        best_id, best_sim = None, 0.0
        for t in canonical:
            sim = _name_sim(t.name, name)
            if sim > best_sim:
                best_sim = sim
                best_id = t.id
        return best_id if best_sim >= 0.72 else None

    for rel in raw_relations:
        src_id = resolve_tech_name(rel.source_name)
        dst_id = resolve_tech_name(rel.target_name)
        if src_id and dst_id and src_id != dst_id:
            add_edge(src_id, dst_id, rel.edge_type, weight=1.2, rationale=rel.rationale)

    # Also infer co-occurrence SYNERGIZES_WITH edges when two techniques share >=1 episode & subtopic.
    ep_to_techs: dict[str, list[str]] = {}
    for t in canonical:
        for c in t.citations:
            ep_to_techs.setdefault(c.episode_code, []).append(t.id)
    for ep_code, tids in ep_to_techs.items():
        unique_tids = sorted(set(tids))
        for i in range(len(unique_tids)):
            for j in range(i + 1, len(unique_tids)):
                a, b = unique_tids[i], unique_tids[j]
                if set(tech_by_id[a].subtopics) & set(tech_by_id[b].subtopics):
                    add_edge(
                        a,
                        b,
                        "SYNERGIZES_WITH",
                        weight=0.8,
                        rationale=f"Co-taught in episode {ep_code}.",
                    )

    # Persist canonical files
    write_jsonl(TECHNIQUES_PATH, [t.model_dump() for t in canonical])
    write_jsonl(VISUALS_PATH, [v.model_dump() for v in all_visuals.values()])
    write_jsonl(EDGES_PATH, [e.model_dump() for e in edges])

    graph_bundle = {
        "metadata": {
            "episodes_processed": len(processed_episodes),
            "total_catalog_episodes": len(manifest_by_vid),
            "techniques_count": len(canonical),
            "visual_assets_count": len(all_visuals),
            "edges_count": len(edges),
        },
        "taxonomy": tax["major_topics"],
        "nodes": nodes,
        "edges": [e.model_dump() for e in edges],
    }
    GRAPH_JSON_PATH.write_text(json.dumps(graph_bundle, indent=2, ensure_ascii=False), encoding="utf-8")

    console.print(
        f"[bold green]Graph built![/bold green] "
        f"{len(canonical)} canonical techniques · {len(all_visuals)} visuals · "
        f"{len(edges)} edges across {len(processed_episodes)} episodes -> {GRAPH_JSON_PATH}"
    )


if __name__ == "__main__":
    app()
