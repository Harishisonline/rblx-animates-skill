> **2026-11-14: for In this town / In this world use voice_preset "intown_v1" (calm storyteller, no hype). Current spec:
> docs/VOICE_SPEC.md "INTOWN recipe". The rules below are history for this format.**

# Narration voice spec (user-supplied 2026-11-14)

> **v3.7 CURRENT RULES (read first; older sections below are history):** narrator Alex yl2ZDV1MzN4HbQJbMihG on eleven_v3,
> per-beat takes (2-4 sentences, 60-250 chars, each opening with its tag), stability 0.0-0.3, similarity 0.75, **style
> 0.35-0.45** (was 0.25), speaker boost on. **Delivered pace 255-290 wpm** for In this world/town, horror, comedy
> (measured refs 262-293; `pacing.py --format`), spoken SFX per format (docs/research/NARRATION_HYPE.md, FORMATS.json).
> Script must pass `tools/hype_lint.py` (no FAIL) before any credit is spent. The "Adam" lines directly below are SUPERSEDED.
Target: the viral "Adam" narrator heard in ref 5 (E9TTaFj-YXU).
- Voice: premade Adam, id pNInz6obpgDQGcFmaJgB (also library "Adam - Dominant, Firm" eGSd0uV8dNQnZuEEX9lu).
- Model: eleven_multilingual_v2 (drama) or eleven_turbo_v2_5 (fast shorts cadence).
- Settings: stability 35-45%, similarity 75-80%, style 15-25%, speaker boost ON.
  NOTE: the MCP creative_generate_speech tool exposes no sliders; use the full ElevenLabs API/connector to apply them.
- Post: speed 1.10-1.15x (or trim micro-pauses), HPF 80 Hz, +3-5 kHz presence, light compression.
- SFX: pspsps / gasp / breath one-shots (ElevenLabs sound effects) layered by hand.
- Ref 5 audio (user supplied mp3): 100.9 s, 48 kHz stereo, ~-22.7 LUFS gating threshold, LRA 7.5, true peak +0.2 dBFS (hot, clipped master).
- Still: user may replace with their own voice; ask before spending credits on full narration.

## Ref 5 audio, measured with earshot (2026-11-14)
It is a FULL MIX, not a bare voice: continuous hip-hop / glitch-hop / future-bass bed with heavy sub bass and vocal chops
(9 sections, ~6.8 onsets/s, no steady grid), integrated -12.6 LUFS (loud, LRA 7.5), true peak +0.2 dBTP, brightness 2.6 kHz,
bands (dB): sub -20, low -8.5, lowmid -2.4, mid -6.9, presence -14.6, air -15.5.
Accents: impact hit at 0:33 (+40 dB over bed), 0.3 s stop-down gap at 0:41.6, sub drops at 0:38.8 and 1:23.5,
chat-message-pop UI dings at 0:52, 1:09, 1:27, 1:31, fast whoosh 0:12.7.
earshot cannot transcribe or judge a voice; the narrator itself is unverified by me.

## Ref 4 narrator match attempt (2026-11-14)
Ref 4 (zzu-VJTRlM8) = same viral beat bed + narrator. Voice isolated via ElevenLabs /v1/audio-isolation (stem still has beat bleed).
Crude proxies (pyin F0 median Hz / spectral centroid Hz / onsets per s): ref 188/1944/6.0.
Candidates (free preview clips): Alex "Young American Male" yl2ZDV1MzN4HbQJbMihG 203/1856/6.4 (closest);
Liam premade TX3LPaxmHKxFdv7VOQHJ 142/1693/5.8; Adam 112/2301/4.9 (far too low => why the first sample was wrong).
Credit state: 8395/10000 chars used at 2026-11-14; keep tests under ~100 chars. API key in ~/RobloxStories/.env (never print).

## DECISION (user, 2026-11-14): narrator voice
- NOW: Alex - Young American Male, id yl2ZDV1MzN4HbQJbMihG (in the user's account).
- LATER/backup: Adrian - Cinematic Deep Male, shared-library id BT6eaRWNcJkXzGwuFtu0 (add to account before use). Closest library sound-alike by measurement (173 Hz, 6.3 onsets/s, centroid 1903).
- Do NOT clone the ref narrator (public-link voice). Do not use Adam, designed voices, or Liam unless the user asks.
- Recipe (Alex, one take, ~270 chars for 15 s): model eleven_v3, stability 0.0, similarity 0.75, style 0.25, speaker boost on;
  tags [fast, urgent, breathless] hook/closer, [whispers] for eerie lines.
  Post: ffmpeg silenceremove=stop_periods=-1:stop_duration=0.22:stop_threshold=-38dB:stop_silence=0.14, atempo=1.08, highpass 80,
  +3 dB @4 kHz, acompressor thr -20 dB ratio 3, loudnorm I=-14 TP=-1.5. Pauses stay <= 0.14-0.4 s.
- API key lives in ~/RobloxStories/.env (Creator plan as of 2026-11-14). Library voices need a paid key; check /v1/user/subscription first.
- Credit rule: ~100-300 chars per test, user approves before full narration.
