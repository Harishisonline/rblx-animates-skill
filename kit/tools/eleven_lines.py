"""Regenerate single script lines (same voice/settings) with previous_text/next_text for prosody continuity.
python tools/eleven_lines.py <slug> "<line>" "<prev>" "<next>" <out.mp3>   (prints characters billed; key never printed)"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit, eleven
slug, line, prev, nxt, out = sys.argv[1:6]
c = kit.cfg()
body = {"text": line, "model_id": c["tts_model"], "voice_settings": eleven.voice_settings(c)}
if prev:
    body["previous_text"] = prev
if nxt:
    body["next_text"] = nxt
audio = eleven.call(f"/text-to-speech/{c['voice_id']}?output_format=mp3_44100_128", body)
open(out, "wb").write(audio)
print("wrote", out, "chars", len(line))
