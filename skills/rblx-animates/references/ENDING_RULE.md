# ENDING RULE: like / share / follow + on-screen pop-ups (user, 2026-11-15) - ALL videos, both series

Every video (Blox City AND In this world / In this town) ends with a spoken engagement line plus pop-ups:
1. Last story line (twist / callback).
2. Narrator: "Like, share and follow for more." (wording can vary slightly, the three verbs stay).
3. Narrator: the episode's one-word, two-option question: "Would you ...? Comment X or Y." (LESSONS 2026-11-14).

On-screen, CENTRE of the screen (user, 2026-11-15: "pop up in the middle of the screen while the character is saying it,
and a mouse clicks the follow button"):
- A row in the middle (y ~0.50): heart pops in ON "Like", share arrow ON "share", then a red "+ FOLLOW" button; a white mouse
  cursor glides in and CLICKS it on "follow" (button presses, ripple, turns grey "FOLLOWING", click sound).
- On "Comment" the row fades and a big comment bubble pops in the centre; the two answer words pop in as buttons (X / Y) lower down.
- Pop-in: scale 0 -> 125 % -> 100 % over ~8 frames, slight wobble, short "pop" SFX a few dB under the voice.
- Captions move down to y 0.68 during the end card so they never collide with the pop-ups.
- Icon/cursor art is our own flat drawing (no Instagram/YouTube/TikTok logos).
- Timing comes from words.json word onsets. Reference implementation: EP2 ~/w/endcard.py (copied to
  videos/poor_boy_school/tools/endcard.py), mixed by comp.py over the rendered frames.

Script budget: the end block adds ~12-16 words (~4-5 s). Keep the whole video within 90-120 s.
This overrides INTOWN_FORMAT.md's "no CTA" reading of the reference reels for our channel.
