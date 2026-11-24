---
name: sakurai-vfx-and-graphics
description: >
  Direct and critique game visual effects and graphics with Masahiro Sakurai's principles: make
  effects "pop" with contrast (not just additive blending), keep characters visible inside
  effects, flash/blast/smoke explosions, the hit-mark criteria, screen shake, effect scale,
  particle budgets, "draw the light, not the asset", emphasizing collision terrain, major vs.
  minor elements, sense of scale and saturation, unified visual style, manga-like expression,
  color-blind readability, and art supervision through retouches. Use when designing or
  reviewing VFX, hit effects, explosions, stage/background art, lighting, or overall visual
  readability.
---

# Sakurai: VFX & graphics

Effects and art exist to **communicate gameplay first and look great second**. Sakurai gives
"gameplay the slight edge" in every visual trade-off (F02, F10).

## When to use

- Designing or reviewing hit marks, explosions, specials, auras, blade trails or particles.
- Reviewing stage or background art, lighting, color, scale, or how readable a busy scene is.
- Giving art feedback or supervising an art team.

**Not for:** animation poses and timing → `sakurai-attack-animation`. Hit stop and shake
values → `sakurai-action-feel`. Shader math: pair with your shader skill.

## Effects

### Make it pop (H01)
- **Don't let additive blending do all the work.** It pushes everything toward white, so the
  effect vanishes on light backgrounds and lacks impact.
- **Mix in crisp elements** (polygons, simple images) as the focus. Smash Ultimate does this on
  every effect for a clean, anime look.
- **Add dark elements for contrast** so effects read on both light and dark backgrounds.
  Use opposing elements in general, like straight lines against curves.

### Let characters shine (H02)
- Characters get lost in effects, especially in 3D. Forcing draw priority creates depth
  conflicts. Instead, **shape effects around the character**: leave openings, vary height front
  to back, or outline the character model.

### Hit marks (H06)
1. **Flashiness matches impact**, and they're usually flashy for clear feedback.
2. **Visually balanced.** Don't rely on additive blending and weak contrast.
3. **Positioned on the actual hit** (where hitbox meets hurtbox). This is tricky with large
   hitboxes.
4. **Several elements**, e.g. the main burst plus a shockwave behind the target and an upward
   spray (sparks for machines). Use well-timed color additions, without clutter.
5. **Don't eclipse the characters.**
6. **Appropriate duration.** Rapid hits get short marks, and even long ones resolve fairly
   quickly.
7. **Contrasting brightness.** Add dark backing so marks read on light backgrounds.
- Hit marks can keep animating during hit stop, so use that time for extra detail. Effects can
  also expose game rules (Smash shows the influenced launch direction) (H06).

### Explosions, shake, trails, scale, particles
- **Flash → blast → smoke** (a classic shmup explosion does it in 5 frames). The blast is key. Pure white flashes
  disappear on white backgrounds. Don't let the hit register for the whole blast, and use
  screen shake (H03, H05).
- **Screen shake** is very important but must not hurt readability (H05).
- **Blade trails** emphasize fast swings. Light-emitting blades keep a non-fading trail (H08).
- **Effects must respect world scale.** Since they move fast they don't need fine detail.
  Make them look **quick and fierce** (H09).
- **Particles always cost something.** Keep them short, stagger their timing and positions so
  fewer are on screen at once, and draw each billboard large (H07, H11).
- **Flashing effects** are toned down under modern regulations. Add shadows for internal
  contrast instead (H10).
- Study effects in slow motion. Careful observation is the shortcut (H04).

## Graphics

- **Draw the light, not the asset.** The finished image should express the light the asset
  reflects in its environment. Simple techniques beat brute-force detail (F01).
- **Emphasize collision, de-emphasize the backdrop.** Players must always know where solid
  ground is. "Your backdrop's outshining your terrain." Aerial perspective alone hurts the look,
  so balance it (F02).
- **Major vs. minor elements.** Spend detail where it covers the screen and faces the camera.
  Small on-screen elements need less, even important ones (F03).
- **Sense of scale & saturation.** Large objects look too small when drawn like small ones. Give
  closer objects higher saturation and distant or large ones lower. Don't over-saturate
  realism. Use depth of field sparingly (F04, F12).
- **Unify the visual style.** "Don't make it look like a fight between live action and
  animation." Harmonize lighting, eye treatments and materials across characters from
  different sources (F08, F09).
- **Make the imaginary feel real.** Add the physical cues players would expect: wind making
  things flutter, gusts near explosions, objects that look heavy (F15). Destruction details
  matter, like jagged edges instead of perpendicular cuts (F17).
- **Manga-like expression** (manpu, eyes visible through glasses) is welcome. Don't take
  realism as a given (F18).
- **Character design** comes from exaggerating the core essence, so the silhouette reads even
  in solid black (F19).
- **Color accessibility.** Check the game in grayscale. Don't rely on hue alone, and keep the
  background from overpowering the foreground (C25). Calibrate team monitors, but remember
  players use ordinary TVs (F13).
- **Final output and post-processing** lift quality, but don't overdo motion blur (F14, F16).
- **Graphics do affect fun:** visuals draw players in, so raise both (F10).

## Supervising art (F05, F11, F20)

- Showing beats telling. Retouch or paint over the art to explain feedback.
- Check that the fighter is in front, contrast is strong in the foreground and weaker in the
  background, and atmosphere doesn't fight the VFX. Point problems out as soon as you find them.

## Review procedure

1. View the scene at real gameplay scale, and in grayscale.
2. Can you tell collision terrain from backdrop instantly? Is the player character always
   visible through effects?
3. For each effect, check contrast on light **and** dark backgrounds, size versus world scale,
   duration, and position on the hit.
4. For art, check where detail is spent (major vs. minor), whether light is expressed,
   saturation by distance, and style consistency.
5. Give prioritized fixes with episode codes, gameplay readability first.

## Evidence

`references/episodes.md`: H01–H11, F01–F20, C25, D05, with contact sheets of the in-game
before/after comparisons.
