---
name: sakurai-game-essence
description: >
  Design and critique core gameplay with Masahiro Sakurai's "game essence" framework: risk and
  reward, push and pull, squeeze and release, rewards-first planning, difficulty curves, quick
  retries, character uniqueness ("average is mediocre"), randomness, handicaps, beginner
  kindness, and balance tuning. Use when designing or reviewing a core loop, enemy/boss/encounter
  pacing, a reward economy, roguelite appeal, competitive balance, fighter/character rosters, or
  when a game "works but isn't fun".
---

# Sakurai: game essence & balance

Sakurai defines **game essence** as the mix of **push and pull** (back-and-forth tension between
player and challenge) and **risk and reward** (exposure to danger buys a payoff) (B01, B23).
Cinematics, story and controls can add to the fun, but they are not the essence itself (B04).

## When to use

- Designing a new mechanic, enemy, boss, mode or reward system, or diagnosing why one is flat.
- Balancing characters or weapons, setting difficulty, tuning retry and death flow.
- Reviewing a game design document "through Sakurai's lens".

**Not for:** moment-to-moment feel (hit stop, jump arcs) → `sakurai-action-feel`. Menu or
onboarding flow → `sakurai-ui-ux`. Writing the proposal itself → `sakurai-planning-and-specs`.

## Core principles

### Risk & reward
- **Keep risk and reward close together and in the right amounts.** Look for exciting ways to
  link them (B01). In *Space Invaders*, the cannon's width sets how much risk you take, and
  getting close to the invaders is the most dangerous and the most rewarding play.
- **Scale reward with risk, roughly in proportion.** A more intense risk should produce more
  intense joy. Low risk means low reward (B17, B18). The Shoryuken command input is the most
  dangerous stick position, so the full command earns a stronger attack and more invincibility.
- **More essence narrows appeal.** Sometimes hold back on harsh risk so beginners aren't
  punished, for example with pit-saving features (B17). Pick the target audience on purpose.
- **Let players exploit the system.** Gains without losses, reset-until-you-win and cheesing
  can be part of the fun (B06).

### Push & pull / squeeze & release
- Tension followed by release feels better than never having stress at all (B02).
- **Don't let genre conventions limit your push and pull.** That goes for RPGs, puzzles,
  shooters and strategy games alike (B03, B11, B16, B26).
- **Design from why it's fun, not from the convention.** Don't start from "blocks must
  disappear". Start from why clearing blocks feels good (B11).

### Rewards first
- **Consider rewards first** (B09, C17). Points or currency need somewhere to be spent, the
  player must feel they are profiting, and the reward should be something they really want.
- **Keep the next reward in sight.** Show progress toward it, like EXP to the next level (C03).
- Growth and progress give a reason to fight enemies (B08). "Work" games become fun through a
  loop of working, profiting and growing stronger, plus role-play (B23).
- Rethink score presentation instead of defaulting to a plain number (C23, B19). Leaderboards
  can be "eternal humiliation" for everyone who isn't #1.

### Difficulty, death & retries
- **Make retries quick.** After a loss, let the defeat land for about a second (it depends on
  the genre), then give control back as soon as possible. Don't spawn players straight into
  enemies, and don't make respawning so free that the game feels mindless (B14, B12).
- **Use peaks and valleys, not linear scaling.** Don't keep player and enemy strength in direct
  proportion. A boss should force a new strategy and pay out a real reward, not just be a
  stronger regular enemy (B13).
- **Repetition needs appeal.** Roguelites only work if the game is appealing enough to start
  over. Consider how players feel replaying the same area (B15).
- **Offer help without humiliation.** Let players change difficulty at any time (B24, B05).
- **Match consequence to how bad the action was.** Every outcome deserves a fitting
  consequence (B27).
- **Tune easier than feels right.** Developers know the game too well. Handicap yourself with
  the controls while testing, and make the game easier than you think it should be (B29).
- **Be kind to beginners,** from the first minute until they're hooked (C29).

### Balance & uniqueness
- **Average and mediocre are the same thing.** Keep characters unique by amplifying their
  shortcomings to offset their strengths. Describe each one in a word or two (D15, B28, C24).
- **Nerf without erasing identity.** To weaken a move, keep its signature power and lengthen
  its follow-through (vulnerable time) instead (B28).
- **Complexity has to earn its place.** Long-lived competitive games need depth, but question
  inherited "givens" at the start of every project (B10).
- **Leave room for strategy.** Avoid a single mandatory solution unless that's the experience
  you want (B25). Two identical armies should draw (B26).
- **Randomness:** players must feel responsible for their own failures. Keep randomness out
  of pure skill contests, use it to spice up casual play (D13).
- **Handicaps** are essential for casual and party games. Let different people take turns
  winning. Smash deliberately avoids rubber-banding so skill still decides matches (D14).
- **CPU opponents** exist to be fun, not perfect. Frame-perfect shields would make them
  invincible (C26).

## Review procedure

When asked to evaluate a mechanic, level, boss or system:

1. **Name the push & pull.** What does the player push against, and what pushes back?
2. **Map risk to reward.** List each risky action and its payoff. Flag risks with no payoff,
   payoffs with no risk, and risk/reward pairs that are far apart in time or space.
3. **Check the reward pipeline.** What is earned, what is it spent on, and is the next reward
   visible?
4. **Walk the failure loop.** Count the seconds from death to control. Are the penalty and
   retread fair? Can players change difficulty without shame?
5. **Look for mediocrity.** Are characters or options interchangeable? Suggest amplifying
   traits and pairing them with clear weaknesses.
6. **Audit inherited conventions.** Which rules exist only because other games have them?
7. Give 3–5 concrete changes, each with the episode code behind it and the tradeoff it brings.

## Anti-patterns

- Copying a hit game's systems without understanding why they're fun (B16, B22, C22).
- Enemy stats that scale linearly with player power, and bosses that are just bigger enemies (B13).
- Currency with nothing worth buying. Rewards decided late in development (B09, C17).
- Long death animations, slow reloads, respawning into danger (B14).
- Balancing everyone toward the middle (D15).
- Tuning difficulty for the dev team (B29).

## Evidence

`references/episodes.md` has quotes, links and visual contact sheets for every source episode
(B01–B29, C03, C17, C23, C24, C26, C29, D13–D15, N06, N08).
