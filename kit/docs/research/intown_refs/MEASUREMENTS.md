# In-this-town reference reels - measurements (2026-11-14)
Sources (analysis only, media deleted after study): R1 = instagram.com/p/Dfe8B5Hs3G6 (@kyreblx, 132.3 s, "missing minute"), R2 = instagram.com/p/Dfs43n3oWqx (105.5 s, "I can't wait").
Pipeline: yt-dlp (anonymous, no cookies) -> ffmpeg mono wav -> ElevenLabs audio-isolation -> scribe_v1 word timestamps (*_stt.json, *_transcript.txt here). ElevenLabs credits used: 1,455.

| metric | R1 | R2 | EP1 narration | hype test B (raw) |
|---|---|---|---|---|
| words / sentences | 496 / 46 | 499 / 50 | 334 | 92 |
| sentence length median (mean, max) | 10 (10.8, 32) | 9 (10.0, 28) | - | - |
| wpm overall (first->last word) | 229 | 285 | 185 | 191 (post 264) |
| wpm articulation (gaps>0.25 s removed) | 251 | 288 | - | - |
| inter-sentence gap | 0.20-0.40 s (median 0.28) | 0.10-0.30 s | 0.16 med | - |
| gaps > 0.6 s | 0 | 0 | - | - |
| first word at | 0.10 s | 0.16 s | - | - |
| F0 median (p10-p90) | 181 Hz (128-269) | 203 Hz (165-260) | 134 Hz | 171 Hz |
| F0 range p5-p95 / sd | 17.0 st / 5.2 | 10.6 st / 3.5 | 14.7 / 4.6 | 21.6 / 6.7 |
| RMS sd (active) | 7.0 dB | 7.4 dB | 5.5 | 6.1 |
| AudioSet "Speech synthesizer" (isolated voice) | 0.86 | 0.82 | 0.64 | - |
| mix LUFS / LRA | -14.4 / 1.9 LU | -14.1 / 0.8 LU | - | - |
| music bed | continuous soft piano/strings ("inspirational/warm"), only ~2 dB under voice in voice-quiet frames | near-silent bed (-19 dB under voice in gaps), light foley/tick SFX | - | - |
| audio events tagged by STT | none | none | - | - |

Reading: both reels are AI TTS storyteller voices (light, young/neutral register ~180-205 Hz), first person, NOT hyped:
no shouting, no ad-libs, no spoken SFX, no laughs, no gaps longer than 0.4 s, flat loudness (LRA 1-2 LU). Pace comes from
dense script + near-zero pauses, not from excited delivery. R2 is ~285 wpm (likely sped/tightened); R1 229 wpm with tiny breaths.
