# GROWTH LOOP (kit copy, v6.0 2026-11-19)

Sections 0-8 (target table, cadence, measure, compare, learn, update with change control, ship, weekly report, never) are the RBLX ANIMATES Project instructions 'GROWTH LOOP v1 2026-11-17' - read them there; the rules in docs/VIRAL_V6.md section 6 (honest monetization pace) apply.

---

## 9. Self-learning loop (v6.0, 2026-11-19, owner: "apply self-learning loops ... run test cases once a week")

A scheduled task ("RBLX weekly self-learning loop") runs every Monday 10:17 IST on the Mac (it needs yt-dlp, the kit
and the Mac's network). Each run:

1. **Measure:**
   - `cd ~/RobloxStories && .venv/bin/python tools/growth_scan.py --discover` (add `--ears` if last week's downloads
     worked) -> `research/growth/<date>/scan.json`, `GAPS.md`, `CHANNEL_LOG.md` rows.
   - Windsor.ai (`get_connectors` -> `get_fields` -> `get_data`) for Instagram reach, skip rate and watch time, and for
     YouTube engaged views.
   - Ask the owner for YouTube Studio "viewed vs swiped away" screenshots of every Short older than 48 h.
2. **Test cases** (the weekly regression suite; every one must still discriminate):
   - `script_lint_v3.py` on this week's viral transcripts (expect 0 FAIL) and on our latest script.
   - `ears_check.py` on the stored viral EARS JSONs (expect 0 FAIL) and on our latest `audio/voice.wav`.
   - `package_check.py` on our latest `package.json`.
   - `ep_viral_check.py` on our latest episode.
   - If a viral reference FAILS a gate, the gate is wrong: re-measure and fix the threshold (self-update, step 4).
3. **Learn:** read `GAPS.md` and pick the 3 biggest gaps by weight x cheapness. For each top outlier, note its mechanism (premise
   family, sentence 1, trigger, loophole, ending, title), never its words. Write
   `rule | evidence | level | test | decision rule` lines into `research/growth/<date>/REPORT.md`.
4. **Self-update** (allowed without asking; each with a LESSONS + CHANGELOG line):
   - thresholds in `FORMATS.json` re-measured on 3+ new outliers
   - roster/COMPETITORS rows
   - new experiments in `EXPERIMENTS.md`, and closing experiments whose 7-day data is in
   - new lessons
   - bug fixes in the tools that keep a test case passing.
5. **Propose** (needs the owner's yes):
   - changes to `SKILL.md`, as a skill-update card
   - the narrator, music, runtime, endings, caption style
   - anything that posts, deletes or spends credits beyond a voice sample.
6. **Report:**
   - the white weekly card (section 7) as `REPORT.md`, copied to the Project as
     `knowledge/WEEKLY_<date>.md`
   - a push notification with the 3 numbers that matter: subs, 90-day Shorts views, the weakest funnel stage.
7. **Breakout rule:** any Short above 5x our median -> teardown + 2 follow-up premises in the report the same day.
