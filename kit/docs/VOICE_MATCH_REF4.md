# Ref 4 narrator: measured metrics and mapping (2026-11-14)
Source: zzu-VJTRlM8 audio, voice stem via ElevenLabs audio-isolation (beat bleed remains; pitch is rough).
## Metrics
- F0 p25/p50/p75: 162 / 188 / 226 Hz (p10 144, p90 257). Probably inflated by vocal-chop bleed.
- Rate: ~6 onsets/s (syllable proxy), speech share 84%, pauses >=0.25 s: 8 in 93 s, median 0.26 s, max 0.42 s => almost no gaps.
- Level vs peak: p10 -22.9, p50 -10.3, p90 -4.3 dB (about 18 dB narration-to-whisper spread). Integrated -12.6 LUFS incl. beat.
## Mapping (proxy only, user says Alex yl2ZDV1MzN4HbQJbMihG sounds nothing like it => reject)
- Alex 203 Hz -> -1.3 semitones to reach 188; Liam premade TX3LPaxmHKxFdv7VOQHJ 142 Hz -> +4.9 st (too much, artifacts).
- Settings: eleven_turbo_v2_5 stability 0.40, similarity 0.78, style 0.20, speed 1.12, speaker boost on; eleven_v3: stability 0.0-0.5 (Creative/Natural).
- Voice Design prompt (<500 ch): "Young American male, early 20s, bright tense mid-high pitch, fast breathless urgent horror-storytime delivery, almost no pauses, crisp diction, close-mic presence, slightly raspy, sudden eerie close-mic whispers on scary lines."
## Test script (30 s)
[fast-paced] Look at your wrist. That number isn't your age... it's how many people have lied about you. [pause] In Blox Town, over forty, shops flip their signs to CLOSED. [fast-paced] Over ninety, police stop asking. [whispers, eerie] Every morning Mom buttons the cuff herself. Covered, Harry. Always covered. [pause] [fast-paced] This morning my wrist read zero.
## Mix sheet (final bus -14 LUFS, TP <= -1.5)
- Narration: peaks -4 dBFS, median -10; whispers about -18 to -22.
- Beat/drone bed: -22 dB under narration (about -32 LUFS short-term), duck -6 dB on whispers.
- SFX (knock/crow/whoosh): peaks -8 to -6 dBFS; impact hits -3 dBFS with bed ducked 6-12 dB for 0.3 s; 0.3 s stop-down gap before drops.
