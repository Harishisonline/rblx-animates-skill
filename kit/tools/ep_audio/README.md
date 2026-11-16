# ep_audio (kit v4.3): voice + meme SFX + mix, per episode, config driven
Set `EP=<episode dir>` (and `RBX_HOME=~/RobloxStories`, where .env with the ElevenLabs key lives; never print it). Order:
1. `python tts.py`: Alex v3 /with-timestamps -> audio/raw.mp3 + alignment_raw.json (voice preset alex_ep1, VOICE_SPEC.md).
   Reads tts_script.txt (TTS spelling, e.g. "Blocks City"); captions use script.txt ("Blox City").
2. `python words.py`: script words <-> alignment -> words_raw.json ("blocks" matches "blox").
3. `python post.py`: meme-cue pauses (audio/meme_cues.json: {"line", "after_word", "sfx", optional "nth"}) + atempo 1.08,
   HPF 80, +3 dB @ 4 kHz, comp, loudnorm -14 -> voice.wav, words.json, pauses.json.
   v4.2: `"nth": 2` picks the 2nd occurrence of a repeated word in that line (EP3 "Somebody screamed. Then everybody screamed.").
4. `python sfxgen.py`: reads **audio/sfx_jobs.json**, one job per output file sfx/<name>.mp3:
   - `{"name": {"sfx": "prompt", "dur": 2.0, "influence": 0.6}}` ElevenLabs sound generation (our own recreation)
   - `{"name": {"tts": "[deadpan] Bruh."}}` a short Alex v3 take (alex_ep1 settings)
   - `{"name": {"copy": "/path/to/earlier/episode/sfx/x.mp3"}}` reuse an earlier episode's sound (no credits)
   Existing sfx/<name>.mp3 files are SKIPPED (no double spend; to redo one, rename the old file first).
4b. `python bed.py [your_song.mp3 | --none]`: the person's music; else assets/music/default_bed.wav (their licensed
   copy of the channel default "Numbers"); else an ORIGINAL bed composed by tools/score.py. Writes $EP/MUSIC_LICENSE.txt.
5. `python mix.py`: reads **audio/mix_cfg.json**:
   - `files`: {LABEL: [[path, ffmpeg_filter, offset_s], ...]}, LABEL = the "sfx" name in meme_cues.json. Path tokens:
     `{K}` kit sfx/, `{S}` $EP/sfx/, `{A}` $EP/audio/, `{RB}` kit root. The filter can shape a sound, e.g. a tail fade
     `afade=t=out:st=0.42:d=0.35` or `volume='if(lt(t,0.40),1,0.5)':eval=frame` (keeps the hit, lowers the tail under speech).
   - `gain`: {LABEL: g} (default 0.8; each sound is peak-normalised to 0.5*g before mixing).
   - `extra`: [[path, word_index or "t:<sec>", gain]] sounds on a word onset (e.g. kids laughing under "Everyone laughed").
   - `bed`: {"file", "from_word", "to_word", "under_db", "duck_db", "fade_out"}: the music bed (set by bed.py, step 4b).
   Meme hits land at word end + 0.04 s (inside the post.py pause). Ending pops and the follow click are placed from the words
   automatically (last Like / share / follow / Comment + the two option words). The bed dips -8 dB for 1.2 s under each meme hit.
   Writes audio/mix_final.wav (the one mix that goes into out/final.mp4, with the bed) + mix_nomusic.wav (for re-mixing), both -14 LUFS,
   TP <= -1.5, and sfx_cues_placed.json.
Then: Blender `tools/ep_lo.py -- <slug> all` (QA) -> look-dev gate -> `tools/ep_final.sh <slug> 32` -> `tools/ep_finish.sh <ep dir>`.

QA by measurement (you cannot hear): every meme hit starts inside its word gap; SFX tails over the following speech
>= 10 dB under the voice RMS; both mixes -14 LUFS / TP <= -1.5; bed clearly under the voice in speech (EP3: 11 dB).
EP2 originals kept for reference: `mix_ep2.py` (fixed word indices, EP2 music switch), `sfxgen_ep2.py` (EP2 prompts).

6. `python qa_audio.py`: the measurement QA above as one command (prints AUDIO QA PASS/FAIL, exit 1 on FAIL).
