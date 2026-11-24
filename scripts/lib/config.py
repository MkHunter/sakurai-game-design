"""Central paths, configuration, and taxonomy loading."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
CATALOG_DIR = DATA_DIR / "catalog"
RAW_VIDEOS_DIR = DATA_DIR / "raw_videos"
RAW_SUBS_DIR = DATA_DIR / "raw_subs"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
VISUALS_RAW_DIR = DATA_DIR / "visuals_raw"
MEDIA_DIR = DATA_DIR / "media"

KNOWLEDGE_DIR = ROOT_DIR / "knowledge"
EPISODES_KNOWLEDGE_DIR = KNOWLEDGE_DIR / "episodes"
TAXONOMY_PATH = KNOWLEDGE_DIR / "taxonomy.yaml"
MANIFEST_PATH = CATALOG_DIR / "manifest.jsonl"
TECHNIQUES_PATH = KNOWLEDGE_DIR / "techniques.jsonl"
VISUALS_PATH = KNOWLEDGE_DIR / "visuals.jsonl"
EDGES_PATH = KNOWLEDGE_DIR / "edges.jsonl"
GRAPH_JSON_PATH = KNOWLEDGE_DIR / "graph.json"
INDEX_DB_PATH = KNOWLEDGE_DIR / "index.db"

VIEWER_DIR = ROOT_DIR / "viewer"
VAULT_DIR = ROOT_DIR / "vault"
SKILLS_EVAL_DIR = ROOT_DIR / "skills_eval"

CHANNEL_URL = "https://www.youtube.com/@sora_sakurai_en/videos"
PLAYLISTS_URL = "https://www.youtube.com/@sora_sakurai_en/playlists"

# Default stratified 10-episode pilot covering talk-heavy, diagram, animation, VFX, audio, UI, specs, and concepts.
DEFAULT_PILOT_CODES = [
    "A01",  # Work Ethic (talk-heavy)
    "B01",  # Game Essence (Risk & Reward — diagram heavy)
    "B05",  # Game Essence (Push & Pull / core feel)
    "C01",  # Planning & Game Design
    "D01",  # Design Specifics
    "F01",  # Graphics
    "G01",  # Animation (hitstop / motion)
    "G03",  # Animation (motion/frame breakdown)
    "H01",  # Effects (VFX comparisons)
    "J01",  # UI (layout & readability)
]

# Visually dense Sakurai categories that deserve higher visual extraction budgets.
HIGH_VISUAL_CATEGORIES = {"B", "D", "F", "G", "H", "J"}
MEDIUM_VISUAL_CATEGORIES = {"C", "I", "K", "N", "S"}
LOW_VISUAL_CATEGORIES = {"A", "E", "L", "M", "NEWS"}

# Deictic cues indicating Sakurai is pointing to something important on screen.
VISUAL_DEICTIC_CUES = (
    "look at",
    "notice",
    "compare",
    "comparison",
    "on the left",
    "on the right",
    "left side",
    "right side",
    "slow motion",
    "frame by frame",
    "frames",
    "here you can see",
    "as you can see",
    "diagram",
    "graph",
    "chart",
    "example",
    "without",
    "with it",
    "watch closely",
    "take a look",
    "side by side",
    "before",
    "after",
    "red",
    "blue",
    "arrow",
    "highlight",
)

DEFAULT_GEMINI_CLEAN_MODEL = os.environ.get("SAKURAI_CLEAN_MODEL", "gemini-flash-lite-latest")
DEFAULT_GEMINI_VISION_MODEL = os.environ.get("SAKURAI_VISION_MODEL", "gemini-flash-lite-latest")
DEFAULT_GEMINI_KNOWLEDGE_MODEL = os.environ.get(
    "SAKURAI_KNOWLEDGE_MODEL", os.environ.get("SAKURAI_TEXT_MODEL", "gemini-3.8-flash")
)
DEFAULT_GEMINI_TEXT_MODEL = DEFAULT_GEMINI_KNOWLEDGE_MODEL
DEFAULT_GEMINI_EMBED_MODEL = os.environ.get("SAKURAI_EMBED_MODEL", "text-embedding-004")

# USD per 1M tokens: (input, output) — thinking tokens are billed at the output rate.
MODEL_PRICING_PER_1M: dict[str, tuple[float, float]] = {
    "gemini-flash-lite-latest": (0.25, 1.50),
    "gemini-3.8-flash": (0.75, 3.75),
    "gemini-flash-latest": (1.50, 9.00),
    "gemini-4-neon": (3.00, 15.00),
}


def ensure_dirs() -> None:
    for d in (
        CATALOG_DIR,
        RAW_VIDEOS_DIR,
        RAW_SUBS_DIR,
        TRANSCRIPTS_DIR,
        VISUALS_RAW_DIR,
        MEDIA_DIR,
        KNOWLEDGE_DIR,
        EPISODES_KNOWLEDGE_DIR,
        VIEWER_DIR,
        VAULT_DIR,
        SKILLS_EVAL_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def load_taxonomy() -> dict[str, Any]:
    with TAXONOMY_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def taxonomy_lookup() -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Return (major_by_id, subtopic_id -> major_id)."""
    tax = load_taxonomy()
    majors: dict[str, dict[str, Any]] = {}
    sub_to_major: dict[str, str] = {}
    for m in tax.get("major_topics", []):
        majors[m["id"]] = m
        for s in m.get("subtopics", []):
            sub_to_major[s["id"]] = m["id"]
    return majors, sub_to_major


def resolve_gemini_api_key() -> str | None:
    """Resolve Gemini API key from environment (or optional local .env)."""
    for var in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        val = os.environ.get(var)
        if val and val.strip():
            return val.strip()
    env_file = ROOT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() in ("GEMINI_API_KEY", "GOOGLE_API_KEY") and v.strip():
                return v.strip().strip('"').strip("'")
    return None


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_manifest() -> list[dict[str, Any]]:
    return read_jsonl(MANIFEST_PATH)


def filter_episodes(
    episodes: list[dict[str, Any]],
    codes: list[str] | None = None,
    pilot: bool = False,
    category: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    result = episodes
    if pilot:
        wanted = {c.upper() for c in DEFAULT_PILOT_CODES}
        result = [e for e in result if e["code"].upper() in wanted]
    if codes:
        wanted = {c.strip().upper() for c in codes if c.strip()}
        result = [
            e
            for e in result
            if e["code"].upper() in wanted or e["video_id"].upper() in wanted
        ]
    if category:
        cat = category.strip().upper()
        result = [e for e in result if e["category_code"].upper() == cat]
    if limit is not None and limit > 0:
        result = result[:limit]
    return result


def format_timestamp(seconds: float) -> str:
    total = max(0, round(seconds))
    m, s = divmod(total, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def yt_timestamp_url(video_id: str, seconds: float) -> str:
    return f"https://youtu.be/{video_id}?t={max(0, int(seconds))}"
