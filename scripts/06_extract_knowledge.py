#!/usr/bin/env python3
"""Phase 3A: Extract atomic game design techniques, rules, tradeoffs, and citations per episode."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import typer
from rich.console import Console

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.config import (
    DEFAULT_GEMINI_KNOWLEDGE_MODEL,
    EPISODES_KNOWLEDGE_DIR,
    TRANSCRIPTS_DIR,
    VISUALS_RAW_DIR,
    ensure_dirs,
    filter_episodes,
    load_manifest,
    load_taxonomy,
    taxonomy_lookup,
    yt_timestamp_url,
)
from lib.gemini_client import GeminiHelper, GeminiUnavailableError, is_fatal_gemini_error
from lib.schemas import (
    Citation,
    CleanTranscript,
    EpisodeKnowledge,
    RawRelation,
    Technique,
    Tradeoff,
    VisualAnnotation,
)

console = Console()
app = typer.Typer(add_completion=False)

# Default fallback mapping from Sakurai's A-N categories to our controlled Major Topic IDs.
SAKURAI_TO_MAJOR_DEFAULT = {
    "A": ("production_and_ethic", "player_first_mindset"),
    "B": ("core_game_design", "core_loop_and_fun"),
    "C": ("planning_and_prototyping", "game_concepts_and_pitching"),
    "D": ("core_game_design", "difficulty_and_balance"),
    "E": ("production_and_ethic", "direction_and_communication"),
    "F": ("vfx_and_graphics", "visual_hierarchy_and_clarity"),
    "G": ("animation_and_motion", "key_poses_and_silhouettes"),
    "H": ("vfx_and_graphics", "impact_and_action_vfx"),
    "I": ("audio_and_sound", "impact_and_feedback_audio"),
    "J": ("ui_ux_and_onboarding", "hud_readability"),
    "K": ("engineering_and_tech", "technical_architecture"),
    "L": ("production_and_ethic", "marketing_and_presentation"),
    "M": ("core_game_design", "genre_fundamentals"),
    "N": ("planning_and_prototyping", "game_concepts_and_pitching"),
    "S": ("production_and_ethic", "direction_and_communication"),
}


def _slug_id(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return f"tech_{s[:52]}" if s else "tech_unnamed"


def _heuristic_extract(
    ep: dict,
    tr: CleanTranscript,
    visuals: list[VisualAnnotation],
) -> EpisodeKnowledge:
    """Offline fallback extraction so the pipeline runs end-to-end even without an API key."""
    cat = ep["category_code"].upper()
    major, sub = SAKURAI_TO_MAJOR_DEFAULT.get(cat, ("core_game_design", "core_loop_and_fun"))
    clean_title = re.sub(r"\s*\[[^\]]+\]\s*$", "", ep["title"]).strip()
    top_vis = [v.asset_id for v in visuals if v.importance != "low"][:4]

    rules = []
    for sec in tr.sections[:5]:
        first_sent = sec.text.split(". ")[0].strip()
        if first_sent:
            rules.append(first_sent.rstrip(".") + ".")

    tech = Technique(
        id=_slug_id(clean_title),
        name=clean_title,
        major_topic=major,
        subtopics=[sub],
        sakurai_categories=[ep["category_name"]],
        summary=tr.summary or (tr.full_text[:280] + "..." if len(tr.full_text) > 280 else tr.full_text),
        actionable_rules=rules[:5],
        anti_patterns=[],
        tradeoffs=[],
        attention_to_detail=(
            visuals[0].visual_summary if visuals else "See episode transcript for detailed breakdown."
        ),
        game_examples=[],
        citations=[
            Citation(
                episode_code=ep["code"],
                video_id=ep["video_id"],
                episode_title=ep["title"],
                timestamp_sec=tr.sections[0].start_sec if tr.sections else 0.0,
                url=yt_timestamp_url(ep["video_id"], tr.sections[0].start_sec if tr.sections else 0.0),
                quote=tr.full_text[:200],
                visual_asset_ids=top_vis,
            )
        ],
    )
    return EpisodeKnowledge(
        video_id=ep["video_id"],
        code=ep["code"],
        slug=ep["slug"],
        title=ep["title"],
        category_name=ep["category_name"],
        url=ep["url"],
        extraction_mode="heuristic",
        episode_takeaway=tr.summary,
        techniques=[tech],
        relations=[],
    )


def _gemini_extract(
    ep: dict,
    tr: CleanTranscript,
    visuals: list[VisualAnnotation],
    gemini: GeminiHelper,
    model: str,
    thinking_level: str = "low",
) -> EpisodeKnowledge:
    tax = load_taxonomy()
    majors, sub_to_major = taxonomy_lookup()

    tax_lines = []
    for m in tax["major_topics"]:
        subs = ", ".join(s["id"] for s in m["subtopics"])
        tax_lines.append(f"- {m['id']} ({m['name']}): [{subs}]")

    vis_lines = []
    for v in visuals:
        if v.asset_type == "skip_generic_broll" or v.importance == "low":
            continue
        vis_lines.append(
            f"- {v.asset_id} [{v.start_sec:.0f}s-{v.end_sec:.0f}s] ({v.asset_type}): "
            f"{v.visual_summary} | Detail: {v.design_detail_highlighted} | Delta: {v.before_after_delta}"
        )

    sec_lines = [
        f"[{s.start_sec:.0f}s-{s.end_sec:.0f}s] {s.heading}: {s.text}" for s in tr.sections
    ]

    prompt = f"""You are a senior game designer building a structured, evidence-backed knowledge graph from Masahiro Sakurai's episode:
Episode: {ep['code']} — {ep['title']} ({ep['category_name']})

Extract 1 to 5 distinct, ATOMIC, ACTIONABLE game design/development techniques or principles taught in this episode.
Focus on concrete craft heuristics, frame/timing details, UX/animation micro-decisions, tradeoffs, and anti-patterns — NOT vague inspirational platitudes.

CONTROLLED TAXONOMY (use ONLY these exact major_topic and subtopics IDs):
{chr(10).join(tax_lines)}

TRANSCRIPT SECTIONS:
{chr(10).join(sec_lines)}

EXTRACTED VISUAL REFERENCES:
{chr(10).join(vis_lines) if vis_lines else "(none)"}

Return strict JSON:
{{
  "episode_takeaway": "1-2 sentence core takeaway of this episode.",
  "techniques": [
    {{
      "name": "Concise canonical technique name (3-8 words)",
      "major_topic": "exact_major_topic_id",
      "subtopics": ["exact_subtopic_id"],
      "summary": "Clear 2-3 sentence explanation of the principle and why it works.",
      "actionable_rules": ["Concrete do-this rule...", "..."],
      "anti_patterns": ["Concrete avoid-this pitfall..."],
      "tradeoffs": [{{"tension": "X vs Y", "guidance": "How Sakurai balances them"}}],
      "attention_to_detail": "Specific subtle craft detail Sakurai highlights (especially from visuals/examples).",
      "game_examples": ["Exact game titles cited, e.g. Super Smash Bros. Ultimate"],
      "timestamp_sec": 42.0,
      "quote": "Short verbatim or near-verbatim quote from the transcript.",
      "visual_asset_ids": ["vis_..."]
    }}
  ],
  "relations": [
    {{
      "source_name": "Technique Name A",
      "target_name": "Technique Name B (can be another technique in this episode or a known Sakurai concept like Hitstop or Risk and Reward)",
      "edge_type": "SYNERGIZES_WITH|TRADEOFF_WITH|BUILDS_ON",
      "rationale": "1 sentence explaining the relationship."
    }}
  ]
}}
"""
    data = gemini.generate_json(
        prompt=prompt, model=model, temperature=0.15, thinking_level=thinking_level
    )

    valid_vis_ids = {v.asset_id for v in visuals}
    fallback_major, fallback_sub = SAKURAI_TO_MAJOR_DEFAULT.get(
        ep["category_code"].upper(), ("core_game_design", "core_loop_and_fun")
    )

    techniques: list[Technique] = []
    for raw_t in data.get("techniques", []):
        name = str(raw_t.get("name", "")).strip()
        if not name:
            continue
        subs = [s for s in raw_t.get("subtopics", []) if s in sub_to_major]
        major = raw_t.get("major_topic", "")
        if major not in majors:
            major = sub_to_major[subs[0]] if subs else fallback_major
        if not subs:
            subs = [fallback_sub]

        ts = float(raw_t.get("timestamp_sec") or 0.0)
        vis_ids = [vid for vid in raw_t.get("visual_asset_ids", []) if vid in valid_vis_ids]
        tradeoffs = [
            Tradeoff(tension=str(trd.get("tension", "")), guidance=str(trd.get("guidance", "")))
            for trd in raw_t.get("tradeoffs", [])
            if isinstance(trd, dict) and trd.get("tension")
        ]

        techniques.append(
            Technique(
                id=_slug_id(name),
                name=name,
                major_topic=major,
                subtopics=subs,
                sakurai_categories=[ep["category_name"]],
                summary=str(raw_t.get("summary", "")).strip(),
                actionable_rules=[str(r).strip() for r in raw_t.get("actionable_rules", []) if str(r).strip()],
                anti_patterns=[str(a).strip() for a in raw_t.get("anti_patterns", []) if str(a).strip()],
                tradeoffs=tradeoffs,
                attention_to_detail=str(raw_t.get("attention_to_detail", "")).strip(),
                game_examples=[str(g).strip() for g in raw_t.get("game_examples", []) if str(g).strip()],
                citations=[
                    Citation(
                        episode_code=ep["code"],
                        video_id=ep["video_id"],
                        episode_title=ep["title"],
                        timestamp_sec=ts,
                        url=yt_timestamp_url(ep["video_id"], ts),
                        quote=str(raw_t.get("quote", "")).strip(),
                        visual_asset_ids=vis_ids,
                    )
                ],
            )
        )

    relations: list[RawRelation] = []
    for r in data.get("relations", []):
        etype = r.get("edge_type")
        if etype in ("SYNERGIZES_WITH", "TRADEOFF_WITH", "BUILDS_ON") and r.get("source_name") and r.get("target_name"):
            relations.append(
                RawRelation(
                    source_name=str(r["source_name"]).strip(),
                    target_name=str(r["target_name"]).strip(),
                    edge_type=etype,
                    rationale=str(r.get("rationale", "")).strip(),
                )
            )

    return EpisodeKnowledge(
        video_id=ep["video_id"],
        code=ep["code"],
        slug=ep["slug"],
        title=ep["title"],
        category_name=ep["category_name"],
        url=ep["url"],
        extraction_mode="gemini",
        episode_takeaway=str(data.get("episode_takeaway", "")).strip(),
        techniques=techniques,
        relations=relations,
    )


@app.command()
def main(
    pilot: bool = typer.Option(False, "--pilot"),
    episodes: str | None = typer.Option(None, "--episodes"),
    category: str | None = typer.Option(None, "--category"),
    limit: int | None = typer.Option(None, "--limit"),
    offline: bool = typer.Option(False, "--offline"),
    model: str = typer.Option(DEFAULT_GEMINI_KNOWLEDGE_MODEL, "--model"),
    thinking_level: str = typer.Option("low", "--thinking-level"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Extract structured game-design techniques mapped to taxonomy.yaml for each episode."""
    ensure_dirs()
    manifest = load_manifest()
    codes = episodes.split(",") if episodes else None
    targets = filter_episodes(manifest, codes=codes, pilot=pilot, category=category, limit=limit)

    gemini = GeminiHelper()
    use_gemini = (not offline) and gemini.available
    if not use_gemini:
        console.print("[yellow]Phase 3A running in offline heuristic mode (set GEMINI_API_KEY for LLM extraction).[/yellow]")

    for ep in targets:
        slug = ep["slug"]
        code = ep["code"]
        tr_path = TRANSCRIPTS_DIR / f"{slug}.json"
        vis_path = VISUALS_RAW_DIR / f"{slug}_annotated.json"
        out_path = EPISODES_KNOWLEDGE_DIR / f"{slug}.json"

        if out_path.exists() and not force:
            existing_mode = EpisodeKnowledge.model_validate_json(
                out_path.read_text(encoding="utf-8")
            ).extraction_mode
            if existing_mode == "gemini" or not use_gemini:
                console.print(f"  [dim]✓ {code} knowledge already extracted [{existing_mode}] ({out_path.name})[/dim]")
                continue
            console.print(f"  [cyan]↑[/cyan] Upgrading {code} knowledge from {existing_mode} -> gemini ({model})...")
        if not tr_path.exists():
            console.print(f"  [yellow]Skipping {code}: missing transcript ({tr_path.name}).[/yellow]")
            continue

        tr = CleanTranscript.model_validate_json(tr_path.read_text(encoding="utf-8"))
        visuals = (
            [VisualAnnotation(**row) for row in json.loads(vis_path.read_text(encoding="utf-8"))]
            if vis_path.exists()
            else []
        )

        if use_gemini:
            try:
                ek = _gemini_extract(ep, tr, visuals, gemini, model, thinking_level=thinking_level)
            except (GeminiUnavailableError, Exception) as exc:  # noqa: BLE001
                if is_fatal_gemini_error(exc):
                    console.print(f"  [red]✗ Fatal Gemini error on {code}:[/red] {exc}")
                    raise typer.Exit(1)
                console.print(f"  [yellow]⚠ Transient extraction error on {code} ({exc}); falling back.[/yellow]")
                ek = _heuristic_extract(ep, tr, visuals)
        else:
            ek = _heuristic_extract(ep, tr, visuals)

        out_path.write_text(ek.model_dump_json(indent=2), encoding="utf-8")
        cost_note = f" | cum=${gemini.usage.cost_usd:.4f}" if gemini.usage.calls > 0 else ""
        console.print(
            f"  [green]✓[/green] {code} [{ek.extraction_mode}]: "
            f"{len(ek.techniques)} techniques, {len(ek.relations)} relations -> {out_path.name}{cost_note}"
        )

    if gemini.usage.calls > 0:
        console.print(f"[bold cyan]Phase 3A Gemini spend ({model}):[/bold cyan] {gemini.format_usage_summary()}")


if __name__ == "__main__":
    app()
