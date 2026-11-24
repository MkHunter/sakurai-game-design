---
name: sakurai-ui-ux
description: >
  Design and review game UI/UX and player-time flow with Masahiro Sakurai's principles: clarity
  vs. style, text size for localization, skip and pause everything, fast text advancing, help
  text that never repeats the option name, choosing fast, key config in every game, playable
  without reading, HUD design, color-coding, loading screens, fast screen transitions, "say no
  to slow", never unresponsive inputs, natural tutorials, gameplay in the first three minutes,
  start with the climax, maps as game screens, customization UI, and respecting the time players
  give you. Use when building menus, HUDs, settings, tutorials, onboarding, cutscene flow, or
  auditing a game for wasted player time.
---

# Sakurai: UI, UX & player time

Two themes run through every UI lesson. **Menus are part of your world**, so match the game's
tone. And **never waste the player's time**: every second they aren't having fun is a cost
(D06, C30).

## When to use

- Building or reviewing menus, settings, HUDs, help text, loading screens or transitions.
- Designing onboarding: the first minutes, tutorials, intro cutscenes.
- Auditing pacing for waits, unskippable content or unresponsive inputs.

**Not for:** engine layout and anchoring implementation. Pair with your UI-implementation skill
and use this one for design judgments.

## Respect player time

- **Say no to slow.** Cut waiting as much as you can. Trimming spectacle usually helps (D06).
- **Make screen transitions quick.** It's almost impossible to make them too fast, though
  removing them entirely feels jarring. Themed wipes are fine if they're fast (D17).
- **Let them skip, let them pause.** Make anything the player doesn't control skippable, even
  without save data, because it may not be their first time. Let cutscenes be paused (J10, C27).
- **Text should be easy to speed through,** or voiced so players can listen while playing (J12).
- **Quick retries** after failure (see `sakurai-game-essence`, B14).
- Players weigh hours spent against everything else they could do. "Longer is better" is
  outdated (C30, C13).

## First minutes & onboarding

- **Just let them play.** Players should understand why the game is fun within **three
  minutes**. Get to gameplay early. Consider dropping players into a later slice of the action
  first (C02).
- **Start with the climax** instead of slow daily-life intros. If the structure requires a slow
  start, hand control over as soon as possible (C28, C13: Kid Icarus briefs you while you play).
- **Natural tutorials.** Teach through real challenges woven into progression, not inorganic
  training rooms. When showing button icons, cover every button the player can use (C10, D12).
- **Use de facto standards** for controls so experienced players know them instantly, but still
  offer remapping (C20).

## Menus & text

- **Clarity vs. style.** Clear isn't automatically good and stylish isn't automatically bad.
  Fit the game's content and setting, then make it user-friendly (J01).
- **Menus, fonts, frames and icons define your world** (J06).
- **Make important elements bigger.** Size signals priority and frequency of use (J08).
- **Color-coding:** any palette that matches the game's tone works, but avoid a mishmash of
  colors on one screen. Tone and manner come first (J07).
- **Help text: never explain an option using its own name.** "Options: Go to the Options" is
  useless. Use different, plain words and no jargon ("config", "key repeat"). Prefer names like
  "Play Solo" over "1P Mode" (J13).
- **Text size and localization:** layouts designed only for English break in other languages,
  and kanji needs larger glyphs. Make text emphasis (size, shake, color) editable by translators
  in script, and let native speakers decide (J02, J05).
- **Playable without words.** Ideally, players reach the main game by repeatedly pressing
  confirm, and the game is understandable without reading (J14).
- **Choose fast.** Minimize steps and use new input devices (like a scroll wheel) to speed up
  selection (J09).
- **Customization UI:** make the result of each choice clear, show pros and cons, and offer an
  auto-equip-strongest option. Care about the process, not just the outcome (C21).

## Controls & responsiveness

- **Every game needs key config,** even simple ones. Avoid confusing vertical lists, and never
  let the exit button start a rebind (J11).
- **Never be unresponsive.** Several buttons can confirm. React to presses during cutscenes.
  Avoid ambiguous feedback (C12).
- **Modern QoL** (J03): rich settings, subtitles with sound captions, vibration toggles for
  cutscenes, high-frame-rate options, and changing settings in-game to compare.

## HUD, maps & loading

- **HUDs:** easy *and* fun to play. Keep essentials visible, auto-hide situational elements based
  on distance and context, and consider letting players hide the HUD (J15).
- **Maps are game screens too.** Avoid constant full-screen map toggling. Use in-world guidance
  (e.g. racing-line cues) and overlays. Anticipate where players look and what they're thinking
  (D09).
- **Loading screens:** simple, elegant indicators that evoke the game's world, ready to appear
  whenever needed (J04).

## Review procedure

1. Time the cold start to first control, death to retry, and menu-to-gameplay. Flag anything
   that feels slow.
2. Walk every screen. Can it be skipped or paused? Does every button do something? Do several
   buttons confirm?
3. Read all help text. Does any description repeat the option name or use jargon?
4. Check localization headroom and text-size readability on the target display.
5. Check the HUD's information priority and visual hierarchy (size = importance).
6. Report the issues ranked by wasted time and confusion, with episode codes.

## Evidence

`references/episodes.md`: J01–J15, C02, C10, C12, C13, C20, C21, C27, C28, C30, D06, D09, D12, D17.
