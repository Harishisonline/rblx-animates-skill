# kit v4.3: pick or compose the music bed for one episode -> $EP/audio/bed.wav, and point mix_cfg.json at it.
#   python3 bed.py                    use the person's own file if given, else the default bed, else compose an original one
#   python3 bed.py /path/to/song.mp3  the person's own music (they must hold the rights for where they post)
#   python3 bed.py --none             no bed (voice + SFX only)
# Order when no file is given:
#   1. $RBX_HOME/assets/music/default_bed.wav  - the channel default ("Numbers" by TEMPOREX) if the person put a licensed copy there
#   2. tools/score.py                          - an ORIGINAL score composed with numpy (no samples, no copyright), mood from story.json
# Writes $EP/MUSIC_LICENSE.txt with what was used.
import os, sys, json, shutil, subprocess, tempfile, datetime
EP = os.environ['EP'].rstrip('/'); A = EP + '/audio/'
RB = os.environ.get('RBX_HOME', os.path.expanduser('~/RobloxStories'))
cfg_p = A + 'mix_cfg.json'
cfg = json.load(open(cfg_p)) if os.path.exists(cfg_p) else {"files": {}, "gain": {}}
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', A + 'voice.wav'],
                           capture_output=True, text=True, check=True).stdout) + 1.0
arg = sys.argv[1] if len(sys.argv) > 1 else None
note = ''
if arg == '--none':
    cfg.pop('bed', None); note = 'No music bed (voice + SFX only).'
else:
    if arg:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', arg, '-ac', '2', '-ar', '48000', A + 'bed.wav'], check=True)
        note = f'Bed: the person\'s own file {os.path.basename(arg)}. Rights: held by the person (not checked by the kit).'
    elif os.path.exists(RB + '/assets/music/default_bed.wav'):
        shutil.copy(RB + '/assets/music/default_bed.wav', A + 'bed.wav')
        note = 'Bed: channel default (assets/music/default_bed.wav, supplied by the person). Rights: held by the person.'
    else:
        mood = 'comedy'
        try:
            mood = json.load(open(EP + '/story.json')).get('music_mood', mood)
        except Exception:
            pass
        beats = subprocess.run([sys.executable, RB + '/tools/score.py', '--demo-beats', str(int(dur))],
                               capture_output=True, text=True, check=True).stdout
        bf = os.path.join(tempfile.mkdtemp(), 'beats.json'); open(bf, 'w').write(beats)
        subprocess.run([sys.executable, RB + '/tools/score.py', '--beats', bf, '--dur', str(int(dur)), '--mood', mood,
                        '--out', A + 'bed.wav'], check=True)
        note = f'Bed: original score composed by tools/score.py (mood {mood}), numpy only, no samples. Free to use.'
    cfg['bed'] = dict(cfg.get('bed', {}), file='{A}bed.wav')
    cfg['bed'].setdefault('under_db', 7); cfg['bed'].setdefault('duck_db', 3.5); cfg['bed'].setdefault('fade_out', 2.0)
json.dump(cfg, open(cfg_p, 'w'), indent=1)
open(EP + '/MUSIC_LICENSE.txt', 'w').write(f'{datetime.date.today()}  {note}\n'
    'Never use CC BY-NC music. Commercial songs mixed into the file can get a business account\'s reel muted or claimed.\n')
print(note)
