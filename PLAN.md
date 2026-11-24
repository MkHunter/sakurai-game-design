# Sakurai Game Design Knowledge Pipeline — Master Plan

**Source Channel:** [Masahiro Sakurai on Creating Games (`@sora_sakurai_en`)](https://www.youtube.com/@sora_sakurai_en/videos)  
**Goal:** Build a reproducible, low-cost, local-first pipeline that extracts Sakurai's game design knowledge in clean English text **plus** structured visual references, categorizes every technique into a searchable knowledge graph with interactive visualization, and establishes an evidence-backed foundation for authoring AI agent skills (`SKILL.md`).

---

## 1. Ground-Truth Channel Audit (Verified Metadata)

Before designing the pipeline, the channel was inspected directly via `yt-dlp`:

| Metric | Verified Value | Pipeline Implication |
| :--- | :--- | :--- |
| **Total uploads** | **300 videos** (36.15 hrs) | Channel is **complete/finite** — no streaming/incremental complexity required. |
| **Category Compilations** | **39 videos** (16.92 hrs) | Stitched duplicates of individual episodes (`(Category Compilation)`). **Exclude** to cut work by ~47%. |
| **Unique episodes** | **261 videos** (**19.22 hrs**, avg **4m 25s**) | Small, ultra-dense corpus: 254 lettered episodes (`A`–`N`), 4 `[S: Special]` episodes, ~3 `[news]`/intro videos. |
| **Official categories** | **14 playlists (`A`–`N`) + Specials** | Ready-made provenance taxonomy (`A: Work Ethic` through `N: Game Concepts`). |
| **YouTube CC subtitles** | **No manual `en` CC tracks** (auto `ja-orig` + MT `en` only) | **Critical finding:** Relying on YouTube's auto-translated `en` CC yields noisy machine translation of Japanese speech. |
| **On-video localization** | **Burned-in professional English subs + localized diagrams/UI overlays** | Official localization (8-4 Ltd.) is rendered directly onto the video frames — clean, fixed-position typography ideal for local OCR + selective VLM analysis. |

### Official Playlist Breakdown (`A`–`N`)
- **A:** Work Ethic (23) · **B:** Game Essence (29) · **C:** Planning & Game Design (30) · **D:** Design Specifics (18)
- **E:** Team Management (15) · **F:** Graphics (20) · **G:** Animation (18) · **H:** Effects (11)
- **I:** Audio (14) · **J:** UI (15) · **K:** Programming & Tech (9) · **L:** Marketing (9)
- **M:** Grab Bag (31) · **N:** Game Concepts (12) · **S:** Special (4) · **News/Intro:** (~3)

---

## 2. End-to-End Pipeline Architecture

```text
[Phase 0: Discovery]
  yt-dlp channel + playlist metadata
        │
        ▼  manifest.jsonl (261 unique episodes, 39 compilations excluded)
[Phase 1: Text Extraction ($0 OCR + ~$0.25 LLM cleanup)]
  ├── 720p video download (cached locally; deletable after Phase 2)
  ├── Bottom-ROI change detection + local OCR (official burned-in English subs)
  ├── yt-dlp auto-captions (ja-orig / en) as timestamp & cross-check fallback
  └── LLM reconciliation pass -> clean, timestamped English transcript (Markdown + JSON)
        │
        ▼
[Phase 2: Budget Visual Extraction (~$2–$6 total via Gemini Flash Batch)]
  ├── Shot boundary detection (PySceneDetect / ffmpeg) + perceptual dedup (pHash)
  ├── Local triage: drop talking-head shots; keep diagrams, split-screens, UI callouts
  ├── Deictic cue detector ("look at", "compare", "left/right", "slow motion", "frame")
  ├── Pack motion/animation sequences into labeled 2x2 / 3x2 contact sheets
  ├── Selective VLM pass (Gemini Flash Batch API) -> structured visual descriptions + Mermaid
  └── Save compressed WebP keyframes / contact sheets / optional micro-loops locally
        │
        ▼
[Phase 3: Knowledge Extraction & Taxonomy Normalization (~$1–$2)]
  ├── Extract atomic Techniques, Principles, Anti-Patterns, Tradeoffs, Game Examples
  ├── Link every claim to exact (episode_id, timestamp, quote, visual_asset_id)
  ├── Map to 2-tier Game Development Ontology (Major Topics -> Subtopics) + preserve A–N tags
  └── Cross-episode deduplication, canonical naming & relationship graph synthesis
        │
        ▼
[Phase 4: Indexing, Retrieval & Graph Visualization ($0)]
  ├── Canonical Markdown + JSONL store (human-readable, Git-friendly)
  ├── SQLite index (relational + FTS5 full-text + optional vector embeddings)
  ├── Interactive zero-backend web graph viewer (Cytoscape.js / ForceGraph + inline visual refs)
  └── Optional Obsidian vault export ([[wikilinks]] + embedded WebP visuals)
        │
        ▼
[Phase 5: Pilot (10 eps) -> QA -> Full 261-ep Rollout]
        │
        ▼
[Phase 6: Downstream AI Agent Skill Evaluation & Authoring]
  └── Cluster density audit -> gap check vs. existing skills -> candidate SKILL.md + eval suite
```

---

## 3. Target Repository Layout

```text
game-design-toolkit/
├── PLAN.md
├── pyproject.toml                   # Python tooling managed via uv
├── scripts/
│   ├── 00_discover_catalog.py       # Fetch playlists & build deduplicated manifest
│   ├── 01_download_media.py         # Resumable 720p video + auto-sub fetcher
│   ├── 02_extract_hardsubs.py       # Bottom-ROI frame-diff + local OCR -> raw EN subs
│   ├── 03_clean_transcripts.py      # Reconcile OCR + auto-subs -> clean English MD/JSON
│   ├── 04_extract_visuals.py        # Scene detect, talking-head filter, contact sheets
│   ├── 05_analyze_visuals.py        # Gemini Flash Batch VLM descriptions + Mermaid
│   ├── 06_extract_knowledge.py      # Atomic techniques, taxonomy mapping, citations
│   ├── 07_build_graph.py            # Cross-episode dedup, edge synthesis, graph.json
│   ├── 08_build_index.py            # SQLite (FTS5 + vectors) & Obsidian vault export
│   └── lib/                         # Shared schemas, Gemini batch client, checkpoints
├── data/                            # Intermediate & raw artifacts (gitignored media)
│   ├── catalog/manifest.jsonl       # Authoritative list of 261 unique episodes
│   ├── raw_videos/                  # Temporary 720p MP4s (~10–14 GB; prunable post-Phase 2)
│   ├── raw_subs/                    # OCR raw JSON + yt-dlp auto-subs
│   ├── transcripts/                 # Clean organized English transcripts (.md + .json)
│   └── media/<video_id>/            # Retained WebP keyframes, contact sheets, micro-clips
├── knowledge/                       # Canonical structured knowledge layer
│   ├── taxonomy.yaml                # Major Topics -> Subtopics controlled vocabulary
│   ├── episodes/<code_slug>.json    # Per-episode structured extractions
│   ├── techniques.jsonl             # Deduplicated canonical techniques/principles
│   ├── visuals.jsonl                # Visual reference registry with VLM annotations
│   ├── edges.jsonl                  # Typed semantic relationships
│   ├── graph.json                   # Precomputed graph bundle for viewer & queries
│   └── index.db                     # SQLite FTS5 + embedding search index
├── viewer/                          # Static interactive graph explorer (HTML/JS/CSS)
│   └── index.html
├── vault/                           # Generated Obsidian-compatible Markdown graph
└── skills_eval/                     # Phase 6 skill candidates & evaluation prompts
```

---

## 4. Detailed Pipeline Stages

### Phase 0 — Channel Discovery, Playlist Mapping & Deduplication
**Goal:** Produce an authoritative, ordered catalog of every unique video with its official Sakurai category and episode number.

1. Run `yt-dlp --flat-playlist` on `https://www.youtube.com/@sora_sakurai_en/videos` and all 16 official playlists (`A`–`N`, `S: Special`, `news`).
2. Exclude all 39 videos matching `(Category Compilation)` (and validate no unique content is lost by verifying every episode `#01..#NN` exists individually).
3. Join playlist membership to assign canonical episode codes (`A01`–`N12`, `S01`–`S04`, `NEWS01`–...) plus upload date, duration, title, description, and URL.
4. Output `data/catalog/manifest.jsonl` and a checkpoint state file (`data/state.sqlite` or `status.json`) so every downstream step is idempotent and resumable.

---

### Phase 1 — High-Fidelity English Text Extraction
**Goal:** Obtain accurate, well-organized, timestamped English text matching Sakurai's official localization — without paying ASR/translation API fees or settling for broken auto-captions.

1. **Download Media (Throttled & Resumable):**
   - Fetch `720p` MP4 (`bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720]`) with `--js-runtimes node`, `--sleep-interval 2 --max-sleep-interval 5`, and download archive tracking.
   - Simultaneously download free YouTube auto-captions (`en`, `ja-orig` in `json3`/`vtt`) as a secondary cross-check signal.
   - *Storage note:* 19.22 hrs at 720p is ~10–14 GB. Videos can be processed in batches (e.g., 30 at a time) and optionally deleted after Phase 2 retains the extracted keyframes/clips.
2. **Hardcoded English Subtitle OCR (Primary Text Source — $0):**
   - Sakurai's English channel displays crisp, outlined/boxed English subtitles in a consistent bottom band (~bottom 18–22% of frame).
   - Sample the bottom ROI at 2 fps, compute frame-to-frame difference (MSE / SSIM on binarized text mask) to detect subtitle transitions — collapsing a 4-minute video into ~30–60 unique subtitle events with exact `[start_sec, end_sec]` timestamps.
   - Run local OCR (**RapidOCR / PaddleOCR** via Python; supports RTX 4070 Ti GPU acceleration or fast CPU execution with near-100% accuracy on clean digital subtitles).
   - Also run a lightweight pass on full-frame static title/section cards to capture **on-screen chapter headings and bullet slides**.
   - **Optional Dual-Track Verification (RTX 4070 Ti):** Run local `faster-whisper` (`large-v3-turbo`, ~3 GB VRAM) on the Japanese audio to cross-check OCR lines and recover any minor spoken nuance condensed in 2-line subtitles.
3. **Reconciliation & Formatting Pass (Cheap LLM — ~$0.25 total):**
   - Feed each episode's `[OCR subtitle lines + on-screen headings + YouTube auto-captions]` to `gemini-flash` (Batch API, 50% discount).
   - Prompt instructions: fix minor OCR typos (e.g., `l`/`I`, broken hyphenation), preserve Sakurai's exact localized terminology, segment into logical topical sections with `[MM:SS]` timestamps, and flag any ambiguous lines.
   - Emit two synchronized outputs per episode:
     - `data/transcripts/<code_slug>.md` — clean human-readable English document with YAML frontmatter, section headers, and clickable `[MM:SS](https://youtu.be/<id>?t=<sec>)` links.
     - `data/transcripts/<code_slug>.json` — machine-readable timestamped segments for alignment with visuals.

---

### Phase 2 — Budget-Friendly Visual Reference Extraction
**Goal:** Capture Sakurai's high-effort visual explanations (animations, hitstop comparisons, frame-by-frame breakdowns, diagrams, UI layouts, Good-vs-Bad comparisons) while keeping total VLM cost under **$5–$6**.

#### Why Naive Video Ingestion Fails Budget
Sending 19.22 hours of raw video at high FPS to a frontier VLM wastes 60–70% of tokens on Sakurai sitting at his desk and generic unannotated B-roll. Instead, use a **3-stage visual funnel**:

#### Stage 2A — Local Shot Segmentation & Visual Triage ($0)
1. **Shot Detection:** Run `PySceneDetect` (`ContentDetector` + `AdaptiveDetector`) per episode to split into visual shots.
2. **Talking-Head Removal:** Compute color/layout embeddings (or face-box + studio-background template match) on a small labeled sample of Sakurai's desk setup. Drop talking-head shots unless they include an inset picture-in-picture diagram/callout!
3. **Visual Signal Scoring (Prioritize What Matters):** Score each remaining shot using zero-cost heuristics:
   - **Transcript deictic triggers:** Boost shots whose aligned transcript contains visual pointers (`"look at"`, `"notice"`, `"compare"`, `"left"`, `"right"`, `"slow motion"`, `"frame"`, `"diagram"`, `"example"`, `"without"`, `"with"`, `"here"`, `"red"`, `"arrow"`).
   - **Category weight:** Higher visual budget for visually dense playlists (`F: Graphics`, `G: Animation`, `H: Effects`, `J: UI`, `B: Game Essence`, `D: Design Specifics`), lighter budget for talk-heavy playlists (`A: Work Ethic`, `E: Team Management`, `L: Marketing`).
   - **Motion vs. Static classification:** Measure optical flow / frame-diff variance inside the shot:
     - **Static Diagram / Slide / Annotated Screenshot / UI Layout:** Extract 1 crisp deduplicated keyframe (using perceptual hash `dHash`/`pHash` to avoid duplicates).
     - **Side-by-Side Comparison (`Good vs. Bad` / `Before vs. After`):** Extract 1–2 frames or a 2×2 comparison strip.
     - **Animation / Hitstop / VFX / Camera Motion Sequence:** Extract 4–6 evenly spaced frames (or peak-motion frames) and stitch them into a **single labeled Contact Sheet** (e.g., 3×2 grid with `[MM:SS.d]` headers burned onto each tile). Optionally export a lightweight 3–5s muted **WebP/GIF loop** (480p, 10–12 fps) for human browsing in the graph viewer!

#### Stage 2B — Selective Multimodal VLM Analysis (~$2–$5 total)
- **Model:** Gemini Flash (`gemini-2.5-flash` / `gemini-flash-latest`) via **Gemini Batch API (50% cost reduction)**.
- **Input per visual asset:** The single keyframe or 3×2 contact sheet + a 20-second window of surrounding English transcript for context.
- **Structured JSON Output per Visual Asset:**
  - `asset_type`: `diagram` | `comparison_before_after` | `animation_breakdown` | `ui_callout` | `annotated_gameplay` | `principle_slide` | `skip_generic_broll`
  - `importance`: `high` | `medium` | `low` (automatically filters out uninformative B-roll that slipped past local triage)
  - `visual_summary`: Concrete explanation of *what the viewer sees* and *why Sakurai built this visual*.
  - `design_detail_highlighted`: The subtle craft detail being demonstrated (e.g., *"3-frame hitstop freeze on heavy attack impact with 2px opposing camera jitter and bright flash frame before knockback launch"*).
  - `before_after_delta` (if comparison): Exact observable difference between the two states.
  - `on_screen_text`: Any labels, numbers, frame counts, or diagram legends visible in the graphic.
  - `mermaid_or_ascii` (optional, for diagrams/timelines/state flows): Text-native reconstruction so **text-only AI agents** can reason over Sakurai's charts/timelines without viewing pixels!
- **Targeted Video-Clip Escalation (Optional, High-ROI):** For ~20–40 ultra-important motion demonstrations in `G: Animation` and `H: Effects` where contact sheets miss timing feel (e.g., hitstop frames, anticipation curves, camera lag), pass the trimmed 5–15 second 480p clip directly to Gemini Flash native video understanding (~$0.20 total for 40 clips!).

#### Stage 2C — Visual Asset Retention
- Save only `high` and `medium` visual assets in `data/media/<video_id>/` as compressed WebP (quality 82, ~40–100 KB each → **~250–400 MB total** for the whole channel).
- Every retained asset gets a stable ID (`vis_<video_id>_<sec>`), local relative path, and clickable YouTube timestamp URL.

---

### Phase 3 — Knowledge Extraction, Taxonomy & Graph Synthesis
**Goal:** Transform 261 linear episodes + visual annotations into a normalized, multi-dimensional library of reusable game design & development techniques.

#### 3.1 Controlled Game Development Taxonomy (`knowledge/taxonomy.yaml`)
Maintain **both** Sakurai's original `A`–`N` playlist label (provenance) and a **2-level Game Development Topic/Subtopic Ontology** designed for practical retrieval and AI skill routing:

| Major Topic | Representative Subtopics |
| :--- | :--- |
| **1. Core Game Design & Essence** | Risk & Reward · Push & Pull · Core Loop · Difficulty & Balance · Pacing & Tempo · Player Agency · Replayability · Genre Fundamentals |
| **2. Game Feel, Juice & Combat** | Hitstop & Impact · Timing & Frame Data · Input Responsiveness & Buffering · Controls & Handling · Feedback Loops · Kinesthetics |
| **3. Animation & Motion Craft** | Key Poses & Silhouettes · Anticipation & Follow-Through · Frame Economy · Transitions & Blending · Camera-Relative Readability · Expressive/Facial Animation |
| **4. Visual Effects (VFX) & Graphics** | Visual Hierarchy & Clarity · Hit/Impact Effects · Lighting & Color Contrast · Framing & Composition · Readability in Chaos · Art Direction vs. Function |
| **5. Camera Systems** | Framing & Sightlines · Tracking & Smoothing · Combat/Action Camera · Multi-Target Framing · Camera Shake & Dynamic Angles |
| **6. Audio & Sound Design** | Impact & Feedback Audio · Spatial/Reverb Weight · Mixing & Priority · Music Pacing & Mood · Audio-Visual Sync |
| **7. UI, UX & Onboarding** | Menu Flow & Speed · HUD Readability · Tutorials & Affordances · Feedback States · Localization & Accessibility |
| **8. Level Design & Encounter Flow** | Space & Metrics · Sightlines & Guidance · Escalation & Variety · Environmental Storytelling · Risk Placement |
| **9. Engineering, Tech & Performance** | Frame Rate & Stability · Tooling & Debug Views · Collision/Hitboxes · Optimization Tradeoffs · Prototyping Architecture |
| **10. Planning, Prototyping & Specs** | Game Concepts & Pitching · Fast Prototyping · Spec Writing & Changes · Scope Control · Playtesting & Iteration |
| **11. Production, Team & Craft Ethic** | Direction & Communication · Decision Making · Schedule & Prioritization · Player-First Mindset · Marketing & Presentation |

*(Refine subtopics empirically after the 10-episode pilot and again after the full pass before locking IDs.)*

#### 3.2 Atomic Knowledge Schema (`techniques.jsonl`)
Each extracted technique/principle conforms to a strict JSON schema:

```json
{
  "id": "tech_hitstop_impact_weight",
  "name": "Hitstop to Communicate Attack Weight",
  "major_topic": "game_feel_and_combat",
  "subtopics": ["hitstop_and_impact", "timing_and_frame_data"],
  "sakurai_categories": ["G: Animation", "H: Effects", "B: Game Essence"],
  "summary": "Briefly freezing attacker and target on impact communicates force, gives players time to register hits, and distinguishes light vs. heavy attacks.",
  "actionable_rules": [
    "Scale freeze duration proportionally to attack power (light: 2-4 frames, heavy/finisher: 8-15+ frames at 60fps).",
    "Keep ambient/UI elements or subtle hit-vibration active so the freeze reads as impact rather than lag.",
    "Avoid excessive hitstop on rapid multi-hit moves or in competitive flow where it breaks rhythm."
  ],
  "anti_patterns": [
    "Uniform hitstop across all attack weights (flattens feel).",
    "Freezing without accompanying VFX/audio peak (reads like a frame drop)."
  ],
  "tradeoffs": [
    {
      "tension": "Impact weight vs. combat tempo / multiplayer flow",
      "guidance": "In multiplayer brawlers, freeze only the colliding fighters rather than the global simulation."
    }
  ],
  "attention_to_detail": "Sakurai contrasts identical attacks with 0f vs. tuned hitstop and adds micro-tremor to the struck defender during freeze frames.",
  "game_examples": ["Super Smash Bros. Ultimate", "Kirby", "Street Fighter II"],
  "citations": [
    {
      "episode_code": "G03",
      "video_id": "...",
      "timestamp_sec": 74,
      "url": "https://youtu.be/...?t=74",
      "quote": "...",
      "visual_asset_ids": ["vis_..._74"]
    }
  ]
}
```

#### 3.3 Cross-Episode Consolidation & Graph Edge Synthesis
Because Sakurai revisits core principles across multiple categories (e.g., *risk & reward* appears in Game Essence, Design Specifics, Audio, and UI):
1. **Pass 1 (Per-Episode Extraction):** Extract candidate techniques + local relations from each episode's cleaned transcript + visual annotations.
2. **Pass 2 (Entity Resolution / Deduplication):** Embed candidate technique names + summaries, cluster near-duplicates (cosine similarity > 0.82), and run an LLM merge pass to consolidate into canonical techniques with **merged multi-episode citations** and **merged visual references**.
3. **Pass 3 (Graph Edge Generation):** Synthesize typed edges (`edges.jsonl`):
   - `BELONGS_TO`: `Technique -> Subtopic -> MajorTopic`
   - `CITED_IN`: `Technique -> Episode`
   - `VISUALIZED_BY`: `Technique -> VisualAsset`
   - `SYNERGIZES_WITH`: Techniques that reinforce each other (e.g., *Hitstop* ↔ *Impact VFX* ↔ *Strong Attack Reverb*)
   - `TRADEOFF_WITH`: Competing principles requiring explicit balancing
   - `BUILDS_ON` / `PREREQUISITE_FOR`: Foundational vs. applied techniques
   - `EXEMPLIFIED_BY`: `GameTitle -> Technique`

---

### Phase 4 — Indexing, Retrieval & Graph Visualization
**Goal:** Make every technique, quote, and visual reference instantly queryable by both humans and AI agents.

1. **Dual-Mode Retrieval Index (`knowledge/index.db`):**
   - **SQLite relational schema** mirroring `episodes`, `techniques`, `topics`, `subtopics`, `visual_assets`, `edges`.
   - **SQLite FTS5** virtual tables indexing technique names, rules, anti-patterns, full transcripts, and VLM visual descriptions.
   - **Semantic Vector Index** (optional `sqlite-vec` or lightweight NumPy `.npz` matrix using Gemini `text-embedding-004` or local `bge-small-en-v1.5`) for conceptual queries like *"how to make menus feel snappy without losing clarity"*.
   - **CLI Query Helper (`scripts/query.py`):** Supports `search`, `topic <slug>`, `neighbors <tech_id> --depth 2`, and `visuals <tech_id>`, returning compact Markdown/JSON snippets ready for agent context injection.

2. **Interactive Graph Visualization (`viewer/index.html`):**
   - Zero-backend static web app (runs via `python3 -m http.server` or direct file open) built with **Cytoscape.js** (or **ForceGraph / Sigma.js**) consuming `knowledge/graph.json`.
   - **Visual encodings:**
     - Node size = number of cross-episode citations / degree centrality.
     - Node color = Major Game Dev Topic (11 distinct hues).
     - Edge style = solid (`BELONGS_TO`), dashed green (`SYNERGIZES_WITH`), dotted amber (`TRADEOFF_WITH`).
   - **Interactive controls:**
     - Hierarchical collapse/expand (Major Topic → Subtopic → Technique) + force-directed exploration mode.
     - Live search bar + filters by Major Topic, Sakurai Playlist (`A`–`N`), Edge Type, and "Has Visual Reference".
     - **Inspector Drawer:** Clicking any Technique displays its summary, Do/Don't rules, tradeoffs, **inline rendered WebP keyframes / contact sheets / animation loops**, exact quotes, and one-click YouTube timestamp links (`?t=...`).

3. **Obsidian Vault Export (`vault/`, Optional Bonus — trivial to generate):**
   - Generate interconnected Markdown notes per Major Topic, Subtopic, Technique, and Episode with `[[wikilinks]]` and `![[relative_image.webp]]`, giving instant native graph browsing and personal note-taking in Obsidian.

---

### Phase 5 — Pilot Validation, QA & Full-Corpus Rollout
**Never run 261 videos blind.** Execute in two gates:

#### Gate 1 — 10-Episode Stratified Pilot (Est. cost: < $0.30, time: ~15–20 min)
Select 10 diverse episodes spanning every structural edge case:
- 1 talk-heavy (`A: Work Ethic`), 2 diagram-heavy (`B: Game Essence`, `C: Planning`), 2 motion/frame-heavy (`G: Animation`, `H: Effects`), 2 UI/graphics (`F: Graphics`, `J: UI`), 1 audio (`I: Audio`), 1 design specifics (`D: Design Specifics`), 1 grab bag/concept (`M` or `N`).

**Pilot Acceptance Criteria:**
- [ ] Hardsub OCR word error rate < 2% against manual spot-check of 3 episodes (and subtitle ROI bounding box holds across early 2022 vs. late 2024 episodes).
- [ ] Talking-head filter removes ≥ 80% of pure desk shots without dropping picture-in-picture diagrams.
- [ ] Contact sheets clearly convey before/after and animation timing to both humans and Gemini Flash.
- [ ] Extracted techniques are **concrete and actionable** (not generic summaries), with valid timestamps and visual links.
- [ ] Measured per-video API cost extrapolates cleanly under the $10 budget.

#### Gate 2 — Full 261-Episode Batch Run
- Run Phases 1–3 via resumable batch scripts (processing ~20–30 videos per batch; optionally purging `data/raw_videos/` after verifying Phase 2 outputs if disk space is tight).
- Run automated integrity checks (`scripts/verify_dataset.py`):
  - 0 orphan visual paths, 0 broken `episode_id` citations, 0 timestamps exceeding episode duration, 100% of 261 episodes accounted for, taxonomy coverage report.

---

### Phase 6 — Downstream Evaluation & AI Agent Skill Generation
**Goal:** Turn the curated knowledge graph into modular, high-leverage AI agent skills (`SKILL.md`) — *only where Sakurai's principles add genuine, actionable design power*.

1. **Skill Candidate Discovery (Data-Driven):**
   - Query `knowledge/index.db` for Subtopic clusters with high density (≥ 6–8 distinct actionable techniques, concrete checklists/heuristics, and strong visual/example grounding).
   - Likely high-value candidate domains:
     - `sakurai-game-feel-and-impact` (hitstop, timing, anticipation, audio/VFX sync, input feel)
     - `sakurai-risk-reward-and-essence` (push & pull, core loop tension, difficulty curves, balancing)
     - `sakurai-ui-clarity-and-speed` (snappy menu UX, HUD hierarchy, player feedback states)
     - `sakurai-animation-and-readability` (key poses, frame economy, silhouettes, combat clarity)
     - `sakurai-prototyping-and-iteration` (proposals, fast validation, spec changes, playtesting)

2. **Overlap & Complementarity Audit:**
   - Compare each candidate cluster against existing toolkit skills (e.g., `game-feel`, `game-ui-ux`, `camera-systems`, `level-design`, `prototype-fast`).
   - Decide per cluster:
     - **Standalone Skill** (distinct Sakurai craft lens, e.g., design critique / review rubric), OR
     - **Reference Pack / Augmentation** attached to an existing domain skill.

3. **Skill Authoring Standard (Progressive Disclosure):**
   - Keep `SKILL.md` tight (< 200–300 lines): trigger description, core mental models, decision checklists, anti-patterns, and tradeoff rules.
   - Place deep episode citations, game case studies, and ASCII/Mermaid visual breakdowns in `references/` so agents only load details when needed.
   - Include a lightweight local lookup script or index query pointer if the agent needs deeper Sakurai examples on demand.

4. **Skill Evaluation Harness (`skills_eval/`):**
   - Design 5–10 realistic game-design review/implementation tasks (e.g., *"Critique this 2D melee combat prototype's attack feel"*, *"Design a fast-navigable RPG equipment menu"*, *"Diagnose why this boss encounter feels unfair"*).
   - Compare agent outputs **with vs. without** each candidate skill on: specificity of feedback, concrete frame/timing/UX recommendations, explicit tradeoff reasoning, and zero fluff.
   - Ship only skills that show measurable uplift.

---

## 5. Budget, Compute & Storage Estimates

Assuming Gemini Flash Batch API (50% discount) and local CPU execution for `yt-dlp`, `ffmpeg`, `PySceneDetect`, and `RapidOCR`:

| Stage | Volume | Method / Model | Estimated Cost |
| :--- | :--- | :--- | :---: |
| **Phase 0:** Catalog discovery | 300 videos + 16 playlists | Local `yt-dlp` | **$0.00** |
| **Phase 1A:** Hardsub OCR + auto-subs | 261 videos (19.2 hrs) | Local `ffmpeg` + `RapidOCR` | **$0.00** |
| **Phase 1B:** Transcript cleanup & structuring | ~350K input / ~300K output tokens | Gemini Flash (Batch) | **~$0.20 – $0.40** |
| **Phase 2A:** Shot detect, dedup, contact sheets | 261 videos | Local `PySceneDetect` + OpenCV + `ffmpeg` | **$0.00** |
| **Phase 2B:** Visual analysis (~3.5K keyframes/sheets + ~40 micro-clips) | ~2.5M–4M input / ~800K output tokens | Gemini Flash (Batch) | **~$1.50 – $3.50** |
| **Phase 3:** Technique extraction, dedup & graph edges | ~1.5M input / ~600K output tokens | Gemini Flash / Pro (Batch) | **~$0.80 – $2.00** |
| **Phase 4:** Embeddings + SQLite FTS5 + Web Viewer | ~2,000 chunks | `text-embedding-004` / local | **~$0.01 – $0.05** |
| **TOTAL (Full 261-episode corpus)** | **All text + visuals + graph** | **Fits inside 1 month of Google AI Pro $10 credit** | **~$2.50 – $6.00** |

**Disk Footprint:**
- Temporary 720p video cache: **~10–14 GB** (can be capped at ~1.5 GB by processing in 30-video rolling batches and deleting raw MP4s after Phase 2).
- Permanent outputs (clean transcripts, structured JSON, compressed WebP keyframes/contact sheets, SQLite DB, web viewer): **~400–600 MB**.

---

## 6. Key Technical Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| **YouTube rate limiting / bot checks during download** | Use `--js-runtimes node`, polite sleep intervals (`2–5s`), persistent download archive, optional browser cookies only if throttled; never scrape aggressively in parallel. |
| **Subtitle ROI shifts or overlays overlap subtitles** | Validate ROI coordinates across early, mid, and late episodes in the 10-video pilot; cross-check every episode against YouTube auto-captions to detect missing lines or unusually low OCR word-per-minute rates. |
| **Missing important visual cues inside talking-head PiP frames** | Check for high-edge-density inset regions (bounding boxes / text overlays) before discarding a talking-head shot. |
| **VLM hallucinating frame numbers or unseen details** | Pass exact `[MM:SS.d]` timestamps burned onto contact-sheet tiles + surrounding transcript window; instruct strict grounded-only extraction with `"unknown"` fallback. |
| **Taxonomy sprawl / duplicate techniques across 261 episodes** | Enforce closed controlled vocabulary (`taxonomy.yaml`) during extraction + mandatory Phase 3.3 embedding-assisted entity resolution pass. |
| **Copyright & redistribution hygiene** | Treat raw videos, screenshots, and Nintendo/Sakurai footage strictly as **local personal study/reference material**. Keep `data/raw_videos/` and `data/media/` in `.gitignore` if publishing the repository; attribute every distilled principle to its original YouTube video URL and timestamp. |

---

## 7. Implementation Roadmap & Next Steps

1. **Milestone 1 — Project Scaffold & Catalog (`Phase 0`)**
   - Initialize `pyproject.toml` (`uv`) with `yt-dlp`, `scenedetect`, `opencv-python-headless`, `rapidocr-onnxruntime`, `imagehash`, `pillow`, `google-genai`, `pydantic`, `pyyaml`.
   - Run `00_discover_catalog.py` to freeze `data/catalog/manifest.jsonl` (261 unique episodes).
2. **Milestone 2 — 10-Episode End-to-End Pilot (`Phases 1–3` on 10 eps)**
   - Build `01`–`06` scripts, run on the stratified 10-episode pilot, inspect transcripts, visual contact sheets, VLM outputs, and real API spend.
3. **Milestone 3 — Full Corpus Extraction (`261 episodes`)**
   - Run full batched extraction + consolidation (`07_build_graph.py`) + verification suite.
4. **Milestone 4 — Index & Interactive Graph Viewer (`Phase 4`)**
   - Build `knowledge/index.db`, `scripts/query.py`, static `viewer/index.html`, and optional `vault/`.
5. **Milestone 5 — Agent Skill Evaluation (`Phase 6`)**
   - Audit top technique clusters against existing game-dev skills, draft 2–3 pilot `SKILL.md` candidates, and validate them on concrete design-critique tasks.
