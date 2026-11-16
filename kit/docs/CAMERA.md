# Camera: recipes and rules (rbx/cams.py)

Research summary: the reference channels vary shot TYPE every cut, keep most moves gentle, and save big moves (whip, crash
zoom, dolly zoom) for beats. Subjects fill 40-70% of the vertical frame; top 10% and bottom 20% stay clear for captions/UI.

## Recipes (`from rbx import cams`; each returns the Cam)
| Beat | Recipe | Lens | Distance | Move | Hold |
|---|---|---|---|---|---|
| open / new location | `establish` | 22-26 | 20-30 | slow push 18% + 10 deg yaw | 2-3 s |
| person talks/reacts | `eye_med` | 40 | 7-8 | push 15% | 1.5-2.5 s |
| after every surprise | `close_up` | 55 | 4 | push 12% | 0.8-1.6 s |
| pride / power / threat | `hero_low` | 28 | 8-10 | rise 10% | 1.5-2.5 s |
| conversation | `ots` (alternate side) | 45 | behind shoulder | tiny drift | 1.5-3 s |
| confrontation | `two_shot` | 20 | 12 | lateral drift | 2 s |
| small object (<= a hand) | `insert` + macro prop | 70-90 | 2-3 | slow push, rack focus | 1-1.5 s |
| reveal scale | `pull_reveal` | 28 | 5 -> 14 | pull back | 2-3 s |
| overview/crowd | `top_down` | 32 | 26 up | slow rotate | 1.5-2.5 s |
| walking/running | `track_side` / `pov` | 24-30 | 5 | follows | 1-2 s |
| something is wrong | `dutch_push` | 35 | 6.5 | roll 11 deg + 22% push | 1.5-2 s |
| shock / punchline | `crash_zoom` | 30 -> 60 | 7 | lens punch at the word | 0.5-1 s |
| realisation | `dolly_zoom` | 24 -> 60 | 10 -> 4.5 | vertigo | 1.6-2.2 s |
| change of place | `whip` | 26 | n/a | 0.3 s blur | 0.3 s |
`cams.pick(prev, beat)` chooses a recipe that differs from the previous shot.

## Rules
1. Never the same recipe twice in a row. Alternate wide / medium / close / insert.
2. Frame width in 9:16 is `distance * 13.5 / lens` units. Two characters 6 units apart need >= 8 units of width.
3. Push amount <= 18% unless it is a beat move. Hold 0.8 s before a move starts. Handheld <= 0.7 (panic beats only).
4. One big move (whip/crash/dolly) per ~6 shots. Put the SFX on it.
5. Every move has a reason (a word, a hit, a reveal). Easing is always ease-in-out.
6. Cameras never dip below z=0.6 (the insert recipe clamps this) and never sit inside props: check the contact sheet.
7. Parallax: keep foreground, subject, background at different depths; orbit/lateral moves, depth of field to separate.
8. Hook (first 3 s): subject already doing the weird thing, large in frame, one gentle move, first caption word at 0.0 s.
