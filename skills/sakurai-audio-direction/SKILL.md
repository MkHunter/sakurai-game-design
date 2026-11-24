---
name: sakurai-audio-direction
description: >
  Direct and review game audio with Masahiro Sakurai's principles: a relevance-based sound effect
  priority hierarchy (KO > impacts > specials/voices > … > footsteps > ambience), front-loaded
  impact sounds with short reverb, exaggerated "fictional" combat audio, realistic ambience,
  listening on many playback devices, tempo that matches the game, fewer memorable songs built on
  a main theme, faithful arrangements ("the original piece is always right"), voice recording
  lists, and giving feedback to the sound team. Use when setting mix priorities, designing hit
  or UI sounds, briefing composers, arranging legacy music, or reviewing a game's soundscape.
---

# Sakurai: audio direction

Sound is direct feedback to the player. **The more relevant a sound is to the player, the louder
it should be** (I02).

## When to use

- Setting the mix priority across SFX, voice, music and ambience.
- Designing or reviewing hit, attack, UI and movement sounds.
- Briefing composers, arranging existing themes, or reviewing a soundscape before ship.

**Not for:** bus routing, ducking implementation and adaptive-music systems in an engine. Pair
with your audio-implementation skill and use this one for the *what* and *why*.

## Priority hierarchy (Smash Bros. example, I02)

Loudest to quietest. Adapt the categories to your genre:

1. **KO / match-deciding sounds.** Crucial to push and pull and the outcome.
2. **Impact sounds** (hitting and getting hit) and **perfect shields**. Direct feedback.
3. **Special move activation** and **voices** (balance voices, because clear speech cuts through
   everything). **Explosions** sit between impacts and specials, scaled by size.
4. **Success signals:** dodges, shield blocks, ledge grabs.
5. **Attack swings** (without impact) and **dash** sounds. Quieter, but still button feedback.
6. **Movement:** landing (a reaction, so louder) above jumping, with landings matched to
   footwear and costume.
7. **Footsteps.** Audible feedback with unique variations per character. Many 3D games make them
   too quiet, so characters feel like they're hovering.
8. **Ambient sounds.** Lowest priority, but never dead silence. Silence kills the atmosphere
   (I11).

Always include **variations** of repeated sounds so they don't sound mechanical (I02).

## Sound design rules

- **Strong attack, light reverb** (I09). Front-load the impact: reach a strong level almost
  immediately so the sound never feels late. Don't drag out the reverb. Rapid jabs need trimmed
  sounds that still read as consecutive hits. The main body should finish before the action
  resumes after hit stop.
- **Audio is fiction.** Fighting games are nothing like real fights, so exaggerated SFX serve
  the game's essence. Ambient sound is the exception: realistic ambience builds immersion,
  especially in first-person or over-the-shoulder views (I05, I11).
- **Make the tempo match the game.** 60 BPM is one clap per second and 120 BPM is two. Keep tempo
  in mind whether or not you're the composer (I01).
- **Restraint with music.** Too many songs are hard to remember. Prefer a **main theme with
  arrangements** across the game. A memorable melody has more impact. Write music that
  complements how the player feels (I04).
- **Arranging beloved music:** **"The original piece is always right."** Keep the main melody so
  that humming the arrangement is like humming the original. Build toward a climax. Don't erase
  the identity even if the original sounds dated (I07, I08).
- **Using reference songs** speeds up communication but can blur what to keep versus change.
  A new creation must do more than recreate (I12).
- **Voice recording:** list every vocalization, down to each "hah", attack, jump, damage, special
  move and Final Smash line (I06).
- **Audio quality matters:** "No masterpiece has bad audio" (I14). Learn from hardware-limited
  eras (I13).

## Process

- **Listen in various environments** (I03): studio monitors *and* TV speakers, handhelds and
  earbuds. Details tuned only on studio speakers may be inaudible for most players. Never finalize
  on big studio speakers alone.
- **Giving feedback** (I10): approve sounds that differ from your idea if they fit the game, but
  push for the desired result when the feedback to the player is wrong.

## Review procedure

1. List every sound event in a typical play session and assign each to a priority tier above.
   Flag inversions, such as ambience masking impacts or footsteps louder than hit feedback.
2. For impact sounds, check the onset on the hit frame, the reverb tail length, and how
   rapid-hit variants behave.
3. Check for variation pools on repeated sounds.
4. Listen on at least two very different devices.
5. Music: is there a recognizable theme, does the tempo fit the pace, are arrangements faithful?
6. Report the fixes with episode codes.

## Evidence

`references/episodes.md`: I01–I14.
