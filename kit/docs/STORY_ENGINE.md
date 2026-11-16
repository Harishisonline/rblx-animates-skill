# STORY ENGINE — mandatory rules for every RBLX ANIMATES script (v3)
Supersedes the length/ending parts of `STORY.md` (still valid for premise + originality). Checked by `tools/story.py`.
Source playbook: `RBLX_Animates_60_Unique_Story_Scripts_v2.pdf` -> `engine/stories/episodes.json` (`story.py parse|list|show`).

## 1. Hard rules (story.py FAILs on these)
1. **Length: up to 120 s (v3.7, supersedes the old 80-90 s rule).** Per-format bands live in `docs/FORMATS.json`
   (`python tools/format_preset.py <format>`). Narration speed for In this world/town, horror and comedy: **255-290 wpm
   delivered** (measured: high-view refs 262-293 wpm; our EP1 at ~185 read as "just delivering a story"), target ~270.
   60-120 s at 270 wpm = **270-540 words**; a 90-100 s episode = **400-450 words**. `hype_lint.py` checks the text before
   TTS (estimate band 235-290), `pacing.py --format <name>` checks the real take (words.json). If short, add a picture line,
   never slow the voice. The old 215-245 wpm pace survives only as format `natural` (calm read, on request).
2. **Hook in the first 3 s.** Line 1 states the rule (or its consequence) and the rule must already be being spoken by 3 s; the picture
   proves it at the same moment (number lights up, shadow raises its hand…). No greeting, no "in today's video". <= 18 words.
3. **Finishing cliffhanger** = the line right before the CTA: a concrete new fact that reopens the story (a message, a face, a door).
4. **Engagement last.** The final line contains the question + `Comment A or B` + `Like, share and follow…` and ends on a mystery tag
   (PDF order: question -> Comment -> like/share/follow -> mystery tag). Final 5-8 s (~20-30 words).
5. **Banned generic phrases** (list in story.py `BANNED`): little did I know, everything changed, but then, plot twist, suddenly,
   and that's when, one day, wait for it, smash/hit that like, like and subscribe, stay tuned, out of nowhere…

## 2. Beat structure and word budgets (table written for 230 wpm ≈ 3.8 words/s; at the v3.7 pace of ~270 wpm ≈ 4.5 words/s scale every word budget by x1.17)
| Window | Beat | Words | Must do |
|---|---|---|---|
| 0-3 s | Hook | 10-18 | rule spoken + visually proven |
| 3-12 s | Rule + visual proof | 25-35 | 2-3 concrete consequences of the rule, hero introduced with his "wrong" version + a **plant** |
| 12-25 s | Character + stakes | 45-50 | what the hero stands to lose; first rule event happens to HIM |
| 25-40 s | First complication | 55-60 | the obvious explanation is wrong; the clock (number, count, timer) jumps |
| 40-56 s | Escalation / investigation | 60 | the hidden mechanic of the rule; the scale grows (house -> street -> town) |
| 56-72 s | Reveal + emotional choice | 55-60 | twist pays off the plant; hero must choose between two things he loves |
| 72-77 s | Cliffhanger | 15-20 | one line, new fact |
| 77-88 s | CTA + final mystery | 20-30 | rule 4 |
Every line must give the animator a picture. If a line cannot be shot, cut it.

## 3. Shot count (why not "6-8 shots")
The PDF asks for "6-8 purposeful shots". We treat that as **6-8 story beats / setups (locations or camera set-ups)**, not a shot cap:
our references cut every 0.84-2.2 s, and pacing.py targets an average shot of 1.4-2.2 s. For 80-90 s that is **35-55 shots** (v3.7: scale to the length, ~26-40 cuts per minute, up to 120 s)
(story.py prints the target). Hold key beats (hook proof, the reveal, the cliffhanger message) 2.5-3.5 s; inserts (number ticks,
impacts) may be < 0.8 s but at most 10 % of shots; nothing over 4 s without a camera move.

## 4. Narration style
First person, past or present, consistent. Short sentences (<= 22 words; most 4-12). Specific nouns over adjectives (the cuff button,
not "something strange"). Numbers spoken as the graphic shows them ("zero zero one"). One tender or human line per video. Dialogue in
quotes, max ~8 words per quoted line. Plant 1-2 details in the first 15 s and pay one off in the reveal. If a fixed PDF line switches
person (e.g. Ep 1 cliffhanger "he"), bridge it with an intentional line just before it.

## 5. Genre variants (episodes.json `genre` is a keyword guess; decide per script)
- **Horror** (reference feel: youtube.com/shorts/zzu-VJTRlM8): slow-built, *real* dread. Quiet first, ordinary setting, one wrong
  detail that grows. No jump-scare every 5 s, no screaming narrator, no "SUDDENLY". Let silence and room tone carry 0.5-1 s pauses at
  2-3 places (between sentences only). The scare is a realisation, shown late and small (a second shadow, a breath on the mic).
  Lighting goes from warm to practical-only. Cliffhanger: something is now *closer*.
- **Mystery**: each line is a clue; a visible clock (count, number, timer) rises beat by beat; the investigation must find something,
  not just "learn more"; the twist re-reads an early plant.
- **Comedy**: rule taken literally to its absurd end; 3 escalating gags with a rule of three; a callback punchline; the cliffhanger is a
  bigger absurd problem; still within the format length (up to 120 s) and still a comment choice.
- **Emotional**: the rule costs something human (memory, family, a friend); the choice has no clean right answer; one quiet held shot.

## 6. Repetition avoidance (non-negotiable for "In this town/world")
- Every episode has its **own story engine** (the rule's hidden mechanic) and its own twist; never reuse "it was your mom/you all along"
  in consecutive videos; rotate twist types: hidden purpose, misread rule, narrator is the cause, protector-as-villain, scale reveal.
- Openers rotate: direct address ("Look at your wrist…"), first-person event ("I counted three…"), rule statement ("In this town…").
  No two consecutive videos with the same opener type.
- story.py warns on 6-word phrases shared with any other `videos/*/script.txt` (fixed PDF lines excluded) and on self-repeated 4-grams.
- Vary locations: at least 5 distinct locations, at least 2 not used in the previous video.
- Vary the CTA mystery tag (PDF gives a unique one per episode — keep it).

## 7. Script workflow
1. `story.py show N` -> brief. 2. Draft 2-3 variants with Sonnet subagents (one per tone: dread / momentum / emotional), each given the
fixed hook, cliffhanger and engagement verbatim + the word budget + BANNED list. 3. Judge and merge (best plant/payoff, most shootable
lines). 4. `story.py check <slug> --episode N` must pass. 5. Write `beats.md` (beat map, cast roles from CAST.md, locations, shot ideas).
6. Approval gate: user approves the script BEFORE any voice credits are spent. 7. After voice: `pacing.py --format <name>` length + wpm rows ok (FORMATS.json band).

## 8. QA checklist (in addition to the PDF's Creative QA)
- [ ] Rule understood with sound off in 3 s? - [ ] Hero makes a meaningful choice? - [ ] Twist specific to this rule (could not be
pasted into another episode)? - [ ] Plant in first 15 s, payoff in reveal? - [ ] Cliffhanger is a new concrete fact? - [ ] Final line
invites a real A/B debate? - [ ] 307-345 words, story.py all ok? - [ ] No banned phrases, no cross-video repeats? - [ ] Every line
shootable; 35-55 shots planned; >= 5 locations? - [ ] Horror: dread is earned, not shouted?

## 9. Known conflicts with the PDF (decisions)
- PDF hooks are often 14-20 words (4-5 s at 230 wpm). Rule implemented: the *rule must be spoken by 3 s* and the visual proof lands by
  3 s; the full hook line may run to ~4.5 s.
- PDF "6-8 shots" -> treated as setups/beats; cinematic target is 35-55 shots (section 3).
- PDF beat times total 72 s + cliffhanger + CTA ≈ 85 s; fine. But some PDF engagement lines end on a statement, not a question
  (e.g. Ep 3 "the next train arrives with one more passenger"); the question still sits before "Comment" — accepted.
- Some fixed PDF lines switch narrator person (Ep 1 "he"); bridge them (section 4).
