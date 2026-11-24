"""Strict Pydantic v2 schemas for every stage of the knowledge pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Episode(BaseModel):
    video_id: str
    code: str  # e.g., A01, G03, S01, NEWS01
    slug: str  # e.g., G03_hitstop
    title: str
    category_code: str  # A..N, S, NEWS, MISC
    category_name: str  # e.g., "G: Animation"
    playlist_index: int | None = None
    duration_sec: int = 0
    url: str


class SubtitleCue(BaseModel):
    start_sec: float
    end_sec: float
    text: str
    confidence: float = 1.0
    source: Literal["hardsub_ocr", "yt_auto_en", "yt_auto_ja", "whisper_ja"] = "hardsub_ocr"


class TitleCard(BaseModel):
    timestamp_sec: float
    text: str


class RawSubtitleExtraction(BaseModel):
    video_id: str
    code: str
    fps_sampled: float
    roi_box: list[float]  # [y0_frac, y1_frac, x0_frac, x1_frac]
    cues: list[SubtitleCue] = Field(default_factory=list)
    title_cards: list[TitleCard] = Field(default_factory=list)
    whisper_ja_cues: list[SubtitleCue] = Field(default_factory=list)
    yt_auto_en_cues: list[SubtitleCue] = Field(default_factory=list)


class TranscriptSection(BaseModel):
    heading: str
    start_sec: float
    end_sec: float
    text: str


class CleanTranscript(BaseModel):
    video_id: str
    code: str
    slug: str
    title: str
    category_name: str
    duration_sec: int
    url: str
    cleaning_mode: Literal["gemini", "deterministic"] = "deterministic"
    summary: str = ""
    sections: list[TranscriptSection] = Field(default_factory=list)
    full_text: str = ""
    cues: list[SubtitleCue] = Field(default_factory=list)


class RawVisualCandidate(BaseModel):
    asset_id: str
    video_id: str
    code: str
    start_sec: float
    end_sec: float
    kind: Literal["keyframe", "contact_sheet"]
    local_path: str  # relative to repo root
    loop_path: str | None = None
    youtube_url: str
    score: float = 0.0
    deictic_hits: list[str] = Field(default_factory=list)
    transcript_context: str = ""
    motion_score: float = 0.0
    talking_head_score: float = 0.0


class VisualAnnotation(BaseModel):
    asset_id: str
    video_id: str
    code: str
    start_sec: float
    end_sec: float
    kind: Literal["keyframe", "contact_sheet"]
    local_path: str
    loop_path: str | None = None
    youtube_url: str
    asset_type: Literal[
        "diagram",
        "comparison_before_after",
        "animation_breakdown",
        "ui_callout",
        "annotated_gameplay",
        "principle_slide",
        "skip_generic_broll",
    ] = "annotated_gameplay"
    importance: Literal["high", "medium", "low"] = "medium"
    visual_summary: str = ""
    design_detail_highlighted: str = ""
    before_after_delta: str = ""
    on_screen_text: str = ""
    mermaid_or_ascii: str = ""
    analysis_mode: Literal["gemini", "heuristic"] = "heuristic"


class Tradeoff(BaseModel):
    tension: str
    guidance: str


class Citation(BaseModel):
    episode_code: str
    video_id: str
    episode_title: str = ""
    timestamp_sec: float = 0.0
    url: str = ""
    quote: str = ""
    visual_asset_ids: list[str] = Field(default_factory=list)


class Technique(BaseModel):
    id: str
    name: str
    major_topic: str
    subtopics: list[str] = Field(default_factory=list)
    sakurai_categories: list[str] = Field(default_factory=list)
    summary: str
    actionable_rules: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)
    tradeoffs: list[Tradeoff] = Field(default_factory=list)
    attention_to_detail: str = ""
    game_examples: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)


class RawRelation(BaseModel):
    source_name: str
    target_name: str
    edge_type: Literal["SYNERGIZES_WITH", "TRADEOFF_WITH", "BUILDS_ON"]
    rationale: str = ""


class EpisodeKnowledge(BaseModel):
    video_id: str
    code: str
    slug: str
    title: str
    category_name: str
    url: str
    extraction_mode: Literal["gemini", "heuristic"] = "heuristic"
    episode_takeaway: str = ""
    techniques: list[Technique] = Field(default_factory=list)
    relations: list[RawRelation] = Field(default_factory=list)


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: Literal[
        "BELONGS_TO",
        "CITED_IN",
        "VISUALIZED_BY",
        "SYNERGIZES_WITH",
        "TRADEOFF_WITH",
        "BUILDS_ON",
        "EXEMPLIFIED_BY",
    ]
    weight: float = 1.0
    rationale: str = ""
