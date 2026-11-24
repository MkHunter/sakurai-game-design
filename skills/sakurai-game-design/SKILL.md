---
name: sakurai-game-design
description: >
  Router for Masahiro Sakurai's game design principles (Kirby, Super Smash Bros.), distilled from
  all 261 episodes of "Masahiro Sakurai on Creating Games". Use when the user asks how Sakurai
  would approach something, wants a design review "through Sakurai's lens", or the task spans
  several game development areas (essence/balance, action feel, attack animation, VFX/graphics,
  audio, UI/UX, planning/specs, direction/teamwork). Picks the matching sakurai-* area skill.
---

# Sakurai game design (router)

This skill pack turns Masahiro Sakurai's 261 lessons into skills that agents can act on. Each
area skill has hand-distilled principles in `SKILL.md` and generated evidence in
`references/episodes.md` (official English quotes, YouTube links, visual contact sheets).

## Pick the area skill

| If the task is about… | Load |
| :--- | :--- |
| Why a game is fun, risk & reward, push & pull, rewards, difficulty, balance, character uniqueness, randomness, handicaps | `sakurai-game-essence` |
| Hit stop, button weight, jump physics, responsiveness, frame timing, screen shake, camera center point, input lag | `sakurai-action-feel` |
| Attack animations: standby / lead-in / attack / follow-through, poses, interpolation, damage reactions, hitbox-aware animation | `sakurai-attack-animation` |
| Visual effects, hit marks, explosions, readability, lighting, scale, saturation, art supervision | `sakurai-vfx-and-graphics` |
| Sound effect priority, impact sounds, reverb, music tempo, arrangement, ambience, mixing checks | `sakurai-audio-direction` |
| Menus, HUDs, help text, skip/pause, text speed, key config, tutorials, loading, transitions, respecting player time | `sakurai-ui-ux` |
| Proposals, concepts, specs, parameters, tuning tables, sequels/homages, onboarding the first 3 minutes | `sakurai-planning-and-specs` |
| Directing a team, decisions, feedback loops, bug/play testing, naming, tickets, debug tools, marketing & trailers | `sakurai-direction-and-teamwork` |

Load more than one when a task crosses areas. For example, "make this attack feel better"
usually needs `sakurai-action-feel` (hit stop, responsiveness), `sakurai-attack-animation`
(poses, follow-through) and the hit-mark section of `sakurai-vfx-and-graphics`.

## Ideas that recur across every area

1. **Game essence = push & pull + risk & reward.** Evaluate every mechanic by the tension it
   creates and the payoff it gives (B01, B23).
2. **Deconstruct, don't imitate.** Ask *why* something is fun, then rebuild it in your own
   form. "Don't just mimic" comes up in at least six episodes (B02, B11, B16, B22, B25, C07).
3. **Average is mediocre.** Amplify strengths *and* weaknesses. Don't decide by majority
   vote. Don't sand everything down to the middle (B28, D15, A15, L08).
4. **Never waste the player's time.** Fast retries, fast transitions, skippable cutscenes,
   gameplay inside the first three minutes (B14, D06, D17, J10, C02, C30).
5. **Exaggerate for a small screen.** Animation, effects and sound should overshoot reality,
   because "it's a small thing on a small screen" (G02, G07, I05).
6. **Feedback for every input.** Respond immediately and unambiguously (C12, G04, D01).
7. **Think in frames (60 fps).** State timing as frame counts and learn to feel them
   (C01, C09, G03).
8. **Tune for beginners.** Developers are the worst judges of difficulty, so make the game
   easier than feels right (B29, C29, B24).

## How to use the evidence

- Cite episode codes (e.g. `G03`) when you justify a recommendation, so the user can watch the
  exact lesson. Each area skill's `references/episodes.md` lists the title, link, quotes and visuals.
- When working inside the full `sakurai-game-design` repository with the index built
  (`scripts/08_build_index.py`), you can query the graph directly:
  `uv run python scripts/query.py search "<term>"` or `... neighbors <technique_id>`.
- Sakurai often says that rules are not absolute and you should do what fits your game.
  Present the principles as strong defaults with stated tradeoffs, not as laws.
