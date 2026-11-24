---
name: sakurai-action-feel
description: >
  Make action gameplay feel responsive and heavy using Masahiro Sakurai's techniques: hit stop
  ("stop for big moments") and his eight Smash Bros. hit-stop techniques, button "weight",
  frame-based jump physics, immediate input feedback, counting frames at 60 fps, units of speed,
  ledge behavior, camera center point (don't anchor it to the character), screen shake, and
  input lag. Use when combat or movement feels floaty, weak, laggy, or unresponsive, or when
  specifying timing values for attacks, jumps and hit reactions.
---

# Sakurai: action feel

Sakurai's goal is that **the player can always see and feel the point of impact and the
moment their input registered**. The tools are frame-precise timing, stop effects, camera
framing and shake.

## When to use

- An attack connects but doesn't feel heavy. A jump feels floaty. Inputs feel ignored.
- Writing frame data, hit-stop durations, jump parameters or camera behavior.
- Reviewing a combat or movement prototype for feel.

**Not for:** what the poses look like → `sakurai-attack-animation`. Hit-mark and explosion
art → `sakurai-vfx-and-graphics`. Engine-specific tween or shake code: pair with your engine
skill.

## Think in frames

- At 60 fps, frames are the unit of time for all movement. Specify timing as frame counts (C01, C09).
- **Learn to feel frames:** clap "1-and-2-and-3", where each beat is about 30 frames and each
  "and" splits it into about 15 frames (C09). A 30 fps game draws half as often, and PAL ran
  games at 5/6 speed (C01).
- **State units of speed explicitly** (pixels per frame, cm per frame) so the whole team shares
  one sense of distance and speed (D07).

## Hit stop

- **Don't skimp on stop effects.** They completely change how heavy a hit feels, and they
  belong in every genre (D01). The player's takeaway should be "oh no!", never "wait, I got hit?"
- Stop the screen briefly on big moments (being hit, KO, critical events) so the point of
  impact is clearly visible (D01).
- **Smash Bros. hit-stop techniques (D04).** Hit stop is never just a stop; there is always
  some shake.
  1. **The receiver shakes more** than the attacker.
  2. **Don't move the hit box.** Shake only the model, or attacks that should connect will miss.
  3. **Grounded characters shake horizontally, airborne ones in all directions.** Vertical shake
     would read better between facing fighters, but grounded legs would clip into the floor.
  4. **Resolve the shake gradually.** Start big and shrink it over the computed stop duration.
  5. **Control the amount.** Stronger attacks get longer stops, plus a per-move multiplier: a
     sweet spot like Marth's sword tip feels stronger than its damage alone, and each
     character's stops can match their home game's style.
  6. **Interpolate into the damage pose** over about 4 frames instead of freezing or snapping.
  7. **Keep the attacker inching forward** during the stop, slow enough that it doesn't advance
     every frame. This sells sword cuts. Toggle it per attack, since some moves are better
     without it.
  - Extras: longer stops for lightning, shorter stops in multiplayer, and **more shake when the
    camera is pulled back**, so the impact reads the same at any zoom.
- Keep rapid multi-hits short so they still read as consecutive hits (I09).

## Responsiveness

- **Every input deserves feedback.** Unresponsive buttons and ambiguous reactions are worse
  than redundant ones. Let several buttons confirm in menus, and react to presses even during
  cutscenes (C12).
- **Smash attacks come out 1 frame after input.** The lead-in jumps instantly to a big pose
  instead of interpolating from standby, so the player knows the input landed and the opponent
  can react (G04, G03). "Instant" is a choice, not a law. Some designs need a readable lead-in.
- **Button weight:** speed, inertia, jump physics, lag and frame rate all change how a button
  "feels". It's a powerful tool, so tune it on purpose (D02).
- **Input lag** from displays and setups often goes unnoticed. Test on the real target setup
  (M01).
- **Respect the hardware.** Consider what new peripherals make possible, like flick inputs,
  but don't shoehorn features in (D11). One button can carry a whole game if it feels right
  (C06).

## Jump physics (D03)

- Basic model: apply an upward velocity (e.g. 5), then add constant downward acceleration each
  airborne frame (5 → 4 → 3 → … → 0 → falling faster), with a max fall speed and inertia. X
  velocity stays constant or decays slightly.
- **Shape the arc to the game's goal.** Mario rises gently, gravity spikes at the peak, and
  holding the button changes the height. Samus floats, which suits shooting at heights. Ghosts
  'n Goblins commits you to a fixed arc, so every jump has to be planned. Zangief's pile driver
  falls faster than it rises for impact.
- Smash keeps a short, unified jump windup so jump inputs don't swallow Up Smash.
- **Ultimate's jump:** a very strong initial upward velocity, then a few frames of greatly
  increased downward acceleration, then normal gravity. Players can still escape a jam even if
  they react a little late. It adds parameters and bug risk, but it feels great.
- Question whether you even need a jump at the start of each project.

## Ledges (D08)

Decide which actions can carry a character off a ledge (forward dodges? rushing attacks?),
account for momentum, and judge the result by how it feels in playtests.

## Camera & shake

- **Don't anchor the camera center point to the character** (D05). Track Y less (or not at
  all) so jumps feel tall. Offset or lag the center point to sell speed, as in Kirby Air Ride
  drifting. Fit the camera to the gameplay and presentation.
- **Screen shake** has mattered since Kirby's Adventure, but too much makes the screen hard to
  read. In 3D, shake the center point modestly on both axes, because shake fades with distance
  from the camera (H05).
- **Motion sickness:** a wider field of view and a locked (non-inertial) vehicle frame help,
  but a sickness-proof camera has little embellishment. That's the tradeoff (C15).

## Sound sync

Impact sounds must hit hard almost immediately and never feel late. Keep the reverb short,
especially on rapid jabs (I09). See `sakurai-audio-direction`.

## Review procedure

1. Record or step through the action frame by frame. List the input frame, the first visible
   reaction, the hit frame, the stop duration and when control returns.
2. Is there feedback within 1–2 frames of input? If not, can the lead-in jump to a key pose?
3. Does the hit have a stop, a shake on the victim, a frozen hit box, a blended damage pose
   and a slow-moving attacker?
4. Is the camera center point helping (height, speed) or locked rigidly to the player?
5. Is the shake proportional and readable? Does the audio onset land on the hit frame?
6. Report the fixes with frame numbers and the episode code behind each.

## Evidence

`references/episodes.md`: C01, C06, C09, C12, C15, D01–D05, D07, D08, D11, D18, G04, H05, I09, M01.
