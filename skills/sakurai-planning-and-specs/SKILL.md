---
name: sakurai-planning-and-specs
description: >
  Plan games and write proposals/specs with Masahiro Sakurai's methods: concept as a lighthouse
  you never stray from, ideal spec first (no "Plan B" in proposals), fast and energetic proposals
  sorted into topics and subtopics, keeping ideas under internal pressure until written,
  deconstruct-analyze-rebuild, avoiding comparison to existing games, homages that offer
  something the original doesn't, sequels, parameters in [brackets] with external tuning tables,
  relative parameters, frame-based specs, hierarchical outlines, plus case studies of how Kirby,
  Smash Bros., Air Ride, Meteos and Kid Icarus concepts were formed. Use when writing a game
  proposal, concept doc, GDD, feature spec, or tuning-parameter design, or when ideating new
  mechanics.
---

# Sakurai: planning, proposals & specs

A project needs a clear **concept**, a lighthouse that the director keeps in sight from the first
proposal to release (A17). Specs should turn that concept into concrete values the team can tune
quickly.

## When to use

- Writing a proposal, pitch, concept document, GDD section or feature spec.
- Designing parameter tables and tuning workflows with programmers.
- Ideating mechanics, planning a sequel or homage, or stress-testing a concept.

**Not for:** judging whether the core loop is fun → `sakurai-game-essence`. Running the team
→ `sakurai-direction-and-teamwork`.

## Concept & ideation

- **Never lose sight of the concept.** Don't change direction mid-development. Don't start
  building until the lighthouse is clearly in sight. If something fails, scrap it and start
  fresh rather than drifting (A17).
- **Fun from day one.** The spec change to avoid most is one forced because the game isn't fun,
  so design the fun into the plan. Be flexible about other changes, raise problems early, and
  don't dig in your heels on ideas that aren't working (A04).
- **Deconstruct, analyze, rebuild.** Break down why a game is fun, then rebuild those elements
  into something unique. Example: reward a drift's risk with a speed boost *after* the curve
  (C07).
- **When ideas won't come, define the theme of the problem first,** then list every possible
  solution, including minor or unrealistic ones (A21).
- **Keep internal pressure high.** Don't share or post half-formed ideas. Write the proposal
  first, then consult others (A14).
- **Avoid comparison.** Don't pitch your game as "X meets Y". If it's that similar, people may
  just play the original. Only sequels should sell on another game (C18).
- **Homages and "similar" games** must offer appeal the original doesn't. That said, making any
  game beats making none (C22).
- **Sequels** bring advantages but won't sell if they aren't well made (C19).
- **Hardware & screen:** design around what the hardware does uniquely (analog stick for Smash,
  stereoscopic 3D for Kid Icarus, handheld readability for Smash 3DS), and use screen space
  deliberately (N04, N10, N11, C05).
- **One button can be enough.** Don't add features just because you can. Judge each by how it
  feels (C06).

## Proposals

- **Hot and fast.** Sort ideas into main topics and subtopics, keep sentences brief, don't
  linger on the grand vision, and keep the energy high. If it's rejected, don't conclude the
  other side lacks taste (A06).
- **Clear, engaging, to the point.** Lean isn't always right, but every slide must earn its
  place. Present by talking around the slides, never reading them. Leave implementation detail
  for the team docs (A05).
- **Start from the ideal spec, no "Plan B".** Stand by the idea in the proposal phase, then
  course-correct for cost with input from the team (A11).
- **Presentations are all about speed.** Use simple graphics and keep moving (A02).
- **Hierarchical outlines** (collapsible headings) keep specs organized and easy to reshuffle
  (C16).

## Specs & parameters

- **Specify in frames** (60 fps) and with explicit units of distance and speed (C09, D07).
- **Put parameters in [brackets].** Write behavior as prose with bracketed tunables, e.g.
  "Initiate movement at [Special startup X-velocity], decelerating by [Special X-deceleration
  per frame]". Anything in brackets becomes an externally editable parameter. Each parameter's
  meaning must be crystal clear to anyone (K03).
- **Tuning tables live outside the code,** so planners iterate without programmers. Hide rarely
  used values to reduce errors. Let parameters reference each other (e.g. move A = ½ × move B)
  to keep relative balance. Make the "conversion" into the game fast, because this is where
  you'll iterate most (K02).
- **Model systems as parameters with a guaranteed minimum,** e.g. Smash knockback uses base
  knockback plus scaling so there's always some reaction, and identical inputs give identical
  results (K06).
- **Characters through parameters:** maximize eccentricities and deviate from the neutral
  baseline. Unique behavior needs dedicated programming, so budget for it (C24).
- **Rewards are planned, not bolted on** (C17).
- **Errands and quests:** give useful rewards and mystery tied to the world. No "go buy me some
  meat" (C08). **Praise the player** often and in ways that match their feelings (C11).
- **Ship-ready by design.** Aim to be in the best possible shape at release rather than relying
  on patches (D16). Expect the unexpected, like hardware speed differences changing difficulty
  (D10).

## Case studies (N01–N12)

The Game Concepts episodes show how Sakurai formed each concept: beginner-friendly Kirby with
Extra Game depth (N01), copy abilities (N02), the Helper system dividing lead and support roles
(N03), Smash as interplay and improvisation built for the analog stick (N04), Air Ride widening
play styles instead of chasing perfection (N06), and more. Read `references/episodes.md` when
you need a precedent.

## Review procedure (for a proposal or spec)

1. Can the concept be stated in one sentence, and does every feature serve it?
2. Is the fun visible on paper (push & pull, rewards), or deferred to "we'll find it later"?
3. Does the proposal pitch through comparison to other games? Remove those comparisons.
4. Are timings in frames, units explicit, and tunables bracketed with clear meanings?
5. Are parameters external and relative where they should be?
6. Return concrete edits with episode codes.

## Evidence

`references/episodes.md`: A04–A06, A11, A14, A17, A21, B29, C04–C08, C11, C14, C16, C18, C19, C22,
D10, D16, K02, K03, K06, N01–N12, S04.
