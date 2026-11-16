# kit v4.2: per-episode meme SFX generation. Jobs come from $EP/audio/sfx_jobs.json:
#   {"name": {"sfx": "prompt", "dur": 2.0}}  -> ElevenLabs sound generation (our own recreation, never a ripped clip)
#   {"name": {"tts": "[deadpan] Bruh."}}      -> short Alex v3 take (alex_ep1 settings)
#   {"name": {"copy": "/path/to/existing.mp3"}} -> reuse an earlier episode's sound
# Existing $EP/sfx/<name>.mp3 files are skipped (no double spend). EP2's original job list: sfxgen_ep2.py.
import os, json, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from el import call
EP = os.environ['EP'].rstrip('/'); D = EP + '/sfx/'; os.makedirs(D, exist_ok=True)
jobs = json.load(open(EP + '/audio/sfx_jobs.json'))
for n, j in jobs.items():
    out = D + n + '.mp3'
    if os.path.exists(out): print('skip', n); continue
    if 'copy' in j:
        shutil.copy(os.path.expanduser(j['copy']), out); print('copy', n); continue
    if 'tts' in j:
        a = call('/text-to-speech/yl2ZDV1MzN4HbQJbMihG?output_format=mp3_44100_128', {"text": j['tts'], "model_id": "eleven_v3",
                 "voice_settings": {"stability": 0.0, "similarity_boost": 0.75, "style": 0.25, "use_speaker_boost": True}}, accept='audio/mpeg')
    else:
        a = call('/sound-generation', {"text": j['sfx'], "duration_seconds": j.get('dur', 2.0), "prompt_influence": j.get('influence', 0.6),
                 "model_id": "eleven_text_to_sound_v2"}, accept='audio/mpeg')
    open(out, 'wb').write(a); print('gen', n, len(a))
