# One command for the voice step: (optional small speed-up) -> cut the silences -> THEN timestamp.
# v2: default speed is 1.0. Pace comes from the voice model (tts_speed in config.json, <= 1.15) and from tight writing,
# NOT from ffmpeg time-stretching: stacking 1.25x then retempo 1.35x made v1 sound sped up ~1.5x.
#   python tools/voice_run.py --video <slug> --voice videos/<slug>/audio/raw.mp3 [--speed 1.25]
import argparse, os, shutil, subprocess, sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ap = argparse.ArgumentParser(); ap.add_argument('--video', required=True); ap.add_argument('--voice', required=True); ap.add_argument('--speed', type=float, default=1.0)
ap.add_argument('--allow-fast', action='store_true')
o = ap.parse_args()
if o.speed > 1.12 and not o.allow_fast:
    sys.exit(f'--speed {o.speed} is above 1.12 and will sound sped-up. Raise tts_speed in config.json instead, or pass --allow-fast.')
adir = os.path.join(ROOT, 'videos', o.video, 'audio'); os.makedirs(adir, exist_ok=True)
fast, trimmed = os.path.join(adir, 'raw_fast.wav'), os.path.join(adir, 'trimmed.wav')
voice_py = [sys.executable, os.path.join(ROOT, 'tools', 'voice.py'), '--video', o.video]
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', o.voice, '-af', f'atempo={o.speed}', '-ar', '48000', '-ac', '1', fast], check=True)
subprocess.run(voice_py + ['--voice', fast, '--force'], check=True)                  # pass 1: find and cut the pauses
shutil.copyfile(os.path.join(adir, 'voice.wav'), trimmed)
subprocess.run(voice_py + ['--voice', trimmed, '--no-trim', '--force'], check=True)  # pass 2: time the words on the cut audio
print(f'voice ready: {os.path.join(adir, "voice.wav")} (x{o.speed}, silences cut, then timestamped)')
