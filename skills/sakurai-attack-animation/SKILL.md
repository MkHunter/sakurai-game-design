---
name: sakurai-attack-animation
description: >
  Specify, direct, and critique combat/character animation with Masahiro Sakurai's Smash Bros.
  method: the standby / lead-in / attack / follow-through breakdown, the four-value animation
  spec (standby pose, attack pose, attack start frame, total frames), instant lead-ins, cancel
  frames, exaggerated asymmetric poses with clear silhouettes, the perils of interpolation,
  damage animations, collision-aware animation, squash & stretch, two-axis rotation, and
  animation lists/pose references. Use when writing animation specs, reviewing attack or hit
  reaction animations, porting 2D moves to 3D, or when attacks look slow, stiff, or unreadable.
---

# Sakurai: attack & character animation

Sakurai's attack animations are built for **responsiveness and readability**. Players must know
instantly that their input registered, see the hit clearly, and be able to punish the opening
afterward.

## When to use

- Writing an animation list or animation spec for a character or move set.
- Reviewing attack, damage or idle animations, or translating 2D sprite moves to 3D.
- Attacks feel slow despite low frame counts, poses don't read, or hits look like they should
  connect but don't.

**Not for:** hit stop, shake and timing feel → `sakurai-action-feel`. Hit marks and effects →
`sakurai-vfx-and-graphics`. Engine animation-graph code: pair with your engine skill.

## The four phases (G03)

| Phase | Purpose | Sakurai's rule |
| :--- | :--- | :--- |
| **Standby** | Ground or aerial idle that every move starts from | Nail it first and **don't change it**. Everything is built from it. |
| **Lead-in** (anticipation) | Shows the attack is starting | Often **jumps to a big, unexpected pose on frame 1**. Interpolating from standby takes too long. Confirms the input and cues the opponent to dodge (G03, G04). |
| **Attack** | Key pose while the hitbox is active | The crux. **Hit stop** freezes it into a firm, readable pose. "Everything hinges on this moment." |
| **Follow-through** (recovery) | The opening after the attack | Keep it **very distinct from standby** and hold it as long as possible, because the player can't act here. Add **cancel frames** to give some "elbow room" back. Pre-Melee games without them felt heavy and rigid. |

### The four-value spec
For every new animation, specify: **standby pose, attack pose, attack start frame, total frames**
(time until the attack can be canceled). The lead-in fills standby → attack, and the
follow-through fills attack → total. That's usually enough for animators to start (G03).
Communicate poses by photographing a poseable figure, keep an **animation list**, and give
direction with all animators present so everyone learns together (G01).

### Timing proportions (G06)
- Standard attacks finish in **under one second**. Even big Smash Attacks almost never pass 1 s.
- The hit registers about **1/4 to 1/3 of the way in** (fast moves around 1/5). **The rest is
  follow-through**, which is the part on screen the longest.
- With push and pull, **strong attacks must leave the attacker proportionally vulnerable**, or
  the game feels unrefined.

## Poses (G05, G08, G02, G07)

- **Exaggerate. "Too much is just right."** On a small screen there's almost no such thing as
  too far. If it looks OK, push it further. Physically possible isn't always best. Small
  overshoots read well, like frame 3 going too far and frame 4 pulling back (G02, G07).
- **Avoid symmetry.** Don't just bend the torso sideways. Angle the head away from right
  angles. Don't let the torso, hips and legs follow the same line. Hands aren't straight
  extensions of the arms. Limbs shouldn't be equidistant from the camera (G05, G08).
- **Cut a distinct silhouette.** All four limbs should be clearly visible. Check the pose from
  several angles. In side-view games the side silhouette matters most (G05, G16).
- **Damage, idle and expressive poses** follow the same rules. Characters must look cool.

## Interpolation (G11, G14)

- **Convenience isn't quality.** Tool interpolation makes 3D versions of snappy 2D moves feel
  slow, even at the same frame count. An 8-frame kick can feel slow or snappy depending on how
  quickly it reaches its key frames.
- **Reach key frames fast.** Spend few frames on in-betweens, and save time for the lead-in hold
  and the attack. Give poses even more energy than the originals.
- Make the follow-through take a **different trajectory** from the lead-in. Don't just play the
  move backwards.
- **Blends** between animations must be short, especially into cancel frames (G14).

## Damage animations (G10)

- The first damage frame gets hit stop. **Interpolate from the impact pose into damage over a
  few frames** instead of snapping.
- Choose high, middle or low damage reactions by the point of impact. Non-standard body shapes
  need their own sets.
- Prioritize the feeling of impact for **both** players.

## Collision-aware animation (G16)

- Attack collision is deliberately **wider than the weapon** in fast, coordinate-based games.
  Some visual mismatch is acceptable if it makes the game more fun, but misplaced animation
  makes it feel broken.
- **Collision starts partway through a sword swing.** Animators must always know when and where
  collision is active, and which pose lands the clean hit (that's when hit stop shows it).

## Craft details

- **Squash & stretch:** keep the object's mass roughly constant (G09).
- **Rotate on two axes** for organic turns. Twisting motions move the shoulder and collarbone
  with the wrist. Lead head turns with the eyes (G18).
- **Shift the center of gravity or pivot** to give mechanical motions personality. A bomb
  rotating around an off-center axis feels organic (D18).
- **Fingers** should grip naturally, and spend processing on what matters (G15).
- **Flipped (mirrored) animation** saves work but causes asymmetry problems for expressive
  characters (G13).
- **Skeletons have limits, but push past them.** "Creation is all about freedom" (G17).
- **Supervise top-down.** Check ground and aerial versions of specials, landing follow-throughs,
  wing and cloth timing, and whether attacks that look like they hit actually do (F11, F20).

## Review procedure

1. Get the frame data: lead-in start, active frames, total, and cancel window.
2. Check the proportions. Is the hit 1/5 to 1/3 in, the total under 1 s, and the vulnerability
   proportional to strength?
3. Step through the key frames. Does frame 1 show a clear pose change? Is the attack pose
   exaggerated, asymmetric and readable in silhouette?
4. Look for interpolation mush: long in-betweens, a follow-through retracing the lead-in, or an
   end pose identical to standby.
5. Overlay the hitboxes. Do the visuals line up with collision timing and position?
6. Report pose and timing changes with frame numbers and episode codes.

## Evidence

`references/episodes.md`: G01–G18, D04, D18, F11, F20, with contact sheets of the actual frame
breakdowns (e.g. G03 lead-in poses, G06 recovery timelines).
