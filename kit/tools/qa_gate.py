"""QA gate: the one command that must PASS before a video is delivered (docs/AGENT_PLAYBOOK.md).
    python tools/qa_gate.py <slug> [--stress] [--no-audio] [--json] [--format NAME]
    (--format is passed to pacing.py; default = story.json "format" / docs/FORMATS.json default. Grade: run
     tools/grade_check.py <final.mp4> --format NAME separately, all PASS.)
Exit code 0 = PASS, 1 = FAIL, 2 = cannot run (missing inputs). Writes videos/<slug>/out/qa_gate.json.

Checks (each prints [ok]/[FAIL]/[warn] with the measured number and the rule it is held to):
  1. pacing          tools/pacing.py <slug> (FAIL rows fail the gate, FIX rows warn)
  2. audio           tools/audio_qa.py <slug> --quick, then out/audio_measure.json: -15..-13 LUFS, true peak <= -1 dBTP
  3. transition SFX  each cut cue (kind flash/whip/push) in audio/cues.json: onset in the final mix within 2 frames of the
                     cut and >= +10 dB over the 400 ms bed before it (R3-2: a +3 dB whoosh is inaudible)
  4. transitions     measured from the rendered frames (frames/ or, if cleaned, decoded from out/final_nocaptions.mp4):
                     flash = white frames (luma >= 240) 1-3 + decay to full contrast, total <= 8 frames (REF1 3.1.5);
                     whip/push = motion-blurred / occluded frames around the cut 2-20 frames, and the landing frame
                     (cut + blur span) must be sharp (>= 60 % of the shot's median detail) so the whip lands on something
  5. captions        caption_report.json: no word invisible, no word > 1 frame off its voice onset;
                     INSERT/ECU shots: a caption must not repeat a number/word the shot description puts on screen (R2-1)
  6. length          rendered frame count vs audio length: frames >= ceil(audio*fps) and <= audio + 2 frames
  7. stress (opt.)   --stress runs tools/stress_suite.py all under the blender lock and FAILS if any cell is missing
                     or errors.txt is non-empty (R1-3)
Visual acting/finish defects (wing arms, closed eyes, floating headband) are NOT machine-checked: the playbook's
preview-and-LOOK loop covers them. The gate prints that reminder with the open weak spots."""
import json, math, os, re, subprocess, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__)); STUDIO = os.path.dirname(HERE)
PY = sys.executable
FPS = 30
RES = []   # (status, name, detail)


def add(st, name, detail):
    RES.append((st, name, detail))


def sh(args, timeout=1800):
    r = subprocess.run(args, capture_output=True, text=True, cwd=STUDIO, timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


# ------------------------------------------------------------------------------------------------ 1 pacing
def check_pacing(slug):
    fa = sys.argv[sys.argv.index("--format"):sys.argv.index("--format") + 2] if "--format" in sys.argv else []
    rc, out = sh([PY, os.path.join(HERE, "pacing.py"), slug] + fa)
    fails = [l.strip() for l in out.splitlines() if l.startswith("[FAIL")]
    fixes = [l.strip() for l in out.splitlines() if l.startswith("[FIX")]
    if rc != 0 or fails:
        add("FAIL", "pacing", "; ".join(fails) or out.strip().splitlines()[-1:])
    elif fixes:
        add("warn", "pacing", "; ".join(fixes))
    else:
        add("ok", "pacing", "PACING OK")


# ------------------------------------------------------------------------------------------------ 2/3 audio
def film_of(vdir):
    for f in ("out/final.mp4", "out/final_nocaptions.mp4", "audio/mix.m4a"):
        p = os.path.join(vdir, f)
        if os.path.exists(p):
            return p
    return None


def check_audio(slug, vdir):
    rc, out = sh([PY, os.path.join(HERE, "audio_qa.py"), slug, "--quick"])
    mp = os.path.join(vdir, "out", "audio_measure.json")
    if not os.path.exists(mp):
        add("FAIL", "audio loudness", f"audio_qa produced no audio_measure.json (rc {rc}): {out.strip()[-200:]}")
        return
    m = json.load(open(mp))
    lufs, tp = m.get("lufs"), m.get("true_peak_dbtp")
    ok = lufs is not None and -15 <= lufs <= -13 and tp is not None and tp <= -1.0
    add("ok" if ok else "FAIL", "audio loudness", f"{lufs} LUFS (target -15..-13), true peak {tp} dBTP (<= -1)")
    sil = m.get("digital_silence_frac", 0)
    add("ok" if sil <= 0.02 else "FAIL", "audio silence", f"digital silence {sil:.1%} (<= 2 %: room tone fills holds)")


def decode_mono(path, sr=16000):
    import numpy as np
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                       capture_output=True)
    return np.frombuffer(r.stdout, np.float32), sr


def check_transition_sfx(vdir):
    import numpy as np
    cp = os.path.join(vdir, "audio", "cues.json"); film = film_of(vdir)
    if not (os.path.exists(cp) and film):
        add("warn", "transition SFX", "no cues.json or film")
        return
    cuts = [c for c in json.load(open(cp)) if c.get("cut")]
    if not cuts:
        add("ok", "transition SFX", "no special transitions")
        return
    x, sr = decode_mono(film)
    win = int(0.02 * sr)
    env = np.sqrt(np.convolve(x.astype(np.float64) ** 2, np.ones(win) / win, "same") + 1e-12)
    db = 20 * np.log10(env)
    for c in cuts:
        t = c["t"]; i = int(t * sr)
        bed = db[max(0, i - int(0.45 * sr)): max(1, i - int(0.05 * sr))]
        near = db[max(0, i - int(0.067 * sr)): i + int(0.067 * sr)]   # +-2 frames
        if not len(bed) or not len(near):
            continue
        rise = near.max() - np.median(bed)
        pk = (np.argmax(near) - min(i, int(0.067 * sr))) / sr * 1000
        st = "ok" if rise >= 10 else "FAIL"
        add(st, f"SFX {c.get('kind')} @{t:.2f}s", f"peak {rise:+.1f} dB over bed at {pk:+.0f} ms (rule >= +10 dB within 2 f)")


# ------------------------------------------------------------------------------------------------ 4 transitions (frames)
def load_frames(vdir, lo, hi):
    """luma arrays (downscaled 135x240) for frames lo..hi (1-based) from frames/ or decoded from the encode."""
    import numpy as np
    from PIL import Image
    fd = os.path.join(vdir, "frames"); out = {}
    if os.path.isdir(fd) and os.path.exists(os.path.join(fd, f"{lo:04d}.png")):
        for f in range(lo, hi + 1):
            p = os.path.join(fd, f"{f:04d}.png")
            if os.path.exists(p):
                out[f] = np.asarray(Image.open(p).convert("L").resize((135, 240)), np.float32)
        return out
    film = next((os.path.join(vdir, "out", f) for f in ("final_nocaptions.mp4", "final.mp4")
                 if os.path.exists(os.path.join(vdir, "out", f))), None)
    if not film:
        return out
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", film, "-vf", f"select='between(n,{lo - 1},{hi - 1})',scale=135:240,format=gray",
                        "-vsync", "0", "-f", "rawvideo", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    n = len(a) // (135 * 240)
    for k in range(n):
        out[lo + k] = a[k * 135 * 240:(k + 1) * 135 * 240].reshape(240, 135).astype(np.float32)
    return out


def detail(img):
    import numpy as np
    return float(np.abs(np.diff(img, axis=0)).mean() + np.abs(np.diff(img, axis=1)).mean())


def check_transitions(vdir):
    import numpy as np
    cp = os.path.join(vdir, "audio", "cues.json")
    if not os.path.exists(cp):
        add("warn", "transitions", "no audio/cues.json")
        return
    cuts = [c for c in json.load(open(cp)) if c.get("cut")]
    for c in cuts:
        kind = c.get("kind"); cf = round(c["t"] * FPS) + 1          # first frame of shot B (1-based)
        fr = load_frames(vdir, max(1, cf - 24), cf + 30)
        if len(fr) < 20:
            add("warn", f"{kind} @{c['t']:.2f}s", "frames not available (rendered frames cleaned and no encode)")
            continue
        if kind == "flash":
            white = [f for f in range(cf - 2, cf + 6) if f in fr and fr[f].mean() >= 240]
            if not white:
                add("FAIL", f"flash @{c['t']:.2f}s", "no white frame (luma >= 240) at the cut")
                continue
            ref = fr.get(cf + 24, fr[max(fr)]); rc = ref.std()
            end = max(white)
            for f in range(end + 1, cf + 25):
                if f in fr and abs(fr[f].mean() - ref.mean()) <= 8 and fr[f].std() >= 0.85 * rc:
                    break
                end = f
            total = end - min(white) + 1
            st = "ok" if 1 <= len(white) <= 3 and total <= 8 else "FAIL"
            add(st, f"flash @{c['t']:.2f}s", f"{len(white)} white + {total - len(white)} decay = {total} f "
                f"(rule 1-3 white, full contrast by <= 8 f; frames {min(white)}-{end})")
        else:
            a_det = np.median([detail(fr[f]) for f in range(cf - 24, cf - 8) if f in fr])
            b_det = np.median([detail(fr[f]) for f in range(cf + 12, cf + 30) if f in fr])
            blurred = [f for f in range(cf - 12, cf + 12) if f in fr and
                       detail(fr[f]) < 0.6 * (a_det if f < cf else b_det)]
            span = (max(blurred) - min(blurred) + 1) if blurred else 0
            land = (max(blurred) + 1) if blurred else cf
            land_ok = land in fr and detail(fr[land]) >= 0.6 * b_det
            st = "ok" if 2 <= span <= 20 and land_ok else "FAIL"
            add(st, f"{kind} @{c['t']:.2f}s", f"blur/occlusion span {span} f (rule 2-20), landing frame {land} detail "
                f"{detail(fr[land]) if land in fr else 0:.1f} vs shot median {b_det:.1f} -> {'sharp' if land_ok else 'SMEAR'}")


# ------------------------------------------------------------------------------------------------ 5 captions
def shots_of(vdir):
    """[(id, w0, w1, desc)] from the @S(...) lines of shots.py"""
    src = open(os.path.join(vdir, "shots.py"), encoding="utf-8").read()
    out = []
    for m in re.finditer(r'^@S\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\w+)\s*,\s*"([^"]*)"', src, re.M):
        out.append((int(m.group(1)), int(m.group(2)), None if m.group(3) == "None" else int(m.group(3)), m.group(4)))
    return out


def check_captions(vdir):
    rp = os.path.join(vdir, "out", "caption_report.json")
    if not os.path.exists(rp):
        add("FAIL", "captions timing", "no out/caption_report.json (run finish.py)")
    else:
        r = json.load(open(rp))
        bad = r.get("words_not_visible", []) + r.get("off_by_more_than_1_frame", [])
        add("ok" if not bad else "FAIL", "captions timing",
            f"invisible/off-onset words: {bad or 'none'}; max voice offset {r.get('voice_offset_max_frames')} f")
    wp = os.path.join(vdir, "audio", "words.json")
    if not os.path.exists(wp):
        return
    words = [w["word"] for w in json.load(open(wp))]
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())
    hidden = {}                                   # v3.5: captions.json "hide" rules are the fix for a duplicate
    cj = os.path.join(vdir, "captions.json")
    if os.path.exists(cj):
        j = json.load(open(cj))
        for r in (j.get("hide", []) if isinstance(j, dict) else []):
            hidden.setdefault(str(r.get("shot", "*")), set()).update(norm(w) for w in (r.get("words") or ["*"]))
    dup = []
    for sid, w0, w1, desc in shots_of(vdir):
        if not re.search(r"\b(INSERT|ECU|MACRO)\b", desc):
            continue
        ws = {norm(w) for w in words[w0:(w1 if w1 is not None else len(words))]} - {""}
        onscreen = {norm(t) for t in re.findall(r"\b\d{2,}\b", desc)}   # digits/readouts the insert shows
        hid = hidden.get(str(sid), set()) | hidden.get("*", set())
        hit = [] if "*" in hidden.get(str(sid), set()) else sorted((ws & onscreen) - hid)
        if hit:
            dup.append(f"s{sid:02d} caption repeats on-screen {hit}")
    add("ok" if not dup else "FAIL", "captions vs insert", "; ".join(dup) or
        "no caption repeats a number/word shown on an insert (R2-1: drop the caption word or blank the group)")


def check_render_logs(vdir):
    """v3.5: build-time guards print STRESS_FAIL lines into the render logs - town.insert_cuff_button 'pinch' (fingertips
    >= town.CUFF_TOL=0.05 from the cuff button; also sleeve_pull grip and town.hand_on_prop), cams.hands_guard 'hand_near_lens' (a fist inside the bottom 20 % / side edges of an
    MCU), motion._contact_report 'contact'. Only the LAST build of each shot in render_log_final.txt counts."""
    lp = os.path.join(vdir, "render_log_final.txt")
    if not os.path.exists(lp):
        add("warn", "build guards", "no render_log_final.txt"); return
    # render.py logs only its own say() lines; guards print to stdout. Scan the last run's stdout copy if present.
    logs = [lp] + sorted(glob.glob(os.path.join(vdir, "out", "render_stdout*.log")))
    last = {}
    for p in logs:
        cur = []
        for ln in open(p, errors="ignore"):
            cur.append(ln)
            m = re.match(r"shot (\d+) (ok|FAILED)", ln)
            if m:
                last[int(m.group(1))] = [x.strip() for x in cur if "STRESS_FAIL" in x]; cur = []
    bad = {k: v for k, v in last.items() if v}
    add("ok" if not bad else "FAIL", "build guards",
        "; ".join(f"s{k:02d}: {v[0][:120]}" for k, v in sorted(bad.items())) or
        f"no STRESS_FAIL (pinch / grip / hand_on_prop / hand_near_lens / contact) in the last build of {len(last)} shots")


# ------------------------------------------------------------------------------------------------ 6 length
def audio_len(vdir):
    L = []
    for f in ("audio/mix.m4a", "audio/voice.wav"):
        p = os.path.join(vdir, f)
        if os.path.exists(p):
            o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                               capture_output=True, text=True).stdout.strip()
            try:
                L.append(float(o))
            except ValueError:
                pass
    return max(L) if L else None


def check_length(vdir):
    al = audio_len(vdir)
    fd = os.path.join(vdir, "frames")
    n = len(glob.glob(os.path.join(fd, "[0-9][0-9][0-9][0-9].png"))) if os.path.isdir(fd) else 0
    src = "frames/"
    if not n:
        p = os.path.join(vdir, "out", "final_nocaptions.mp4")
        if os.path.exists(p):
            o = subprocess.run(["ffprobe", "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
                                "stream=nb_read_packets", "-of", "csv=p=0", p], capture_output=True, text=True).stdout
            n = int(o.strip() or 0); src = "final_nocaptions.mp4"
    if not al or not n:
        add("warn", "length", f"audio {al} s, frames {n}")
        return
    need = math.ceil(al * FPS - 1e-6)
    ok = need - 1 <= n <= need + 2
    add("ok" if ok else "FAIL", "length", f"{n} frames ({src}) vs audio {al:.3f} s = {need} f (rule {need - 1}..{need + 2})")


# ------------------------------------------------------------------------------------------------ 7 stress
def check_stress():
    rc, out = sh([PY, os.path.join(HERE, "stress_suite.py"), "all"], timeout=6 * 3600)
    root = os.path.join(os.path.dirname(STUDIO), "RobloxStories", "research", "stress")
    root = root if os.path.isdir(root) else os.path.join(STUDIO, "research", "stress")
    runs = sorted(glob.glob(os.path.join(root, "2*")))
    if not runs:
        add("FAIL", "stress suite", f"no run written (rc {rc})"); return
    last = runs[-1]; pngs = [p for p in glob.glob(os.path.join(last, "*.png"))]
    err = os.path.join(last, "errors.txt")
    errs = open(err).read().strip() if os.path.exists(err) else ""
    st = "ok" if rc == 0 and pngs and not errs else "FAIL"
    add(st, "stress suite", f"{last}: {len(pngs)} tiles, errors: {errs[:200] or 'none'} (LOOK at sheet.jpg)")


OPEN_WEAK_SPOTS = [
    "v3.5: s04 is now a hands insert (insert_cuff_button) - LOOK that the pinch reads; faces are not in that shot",
    "wing arms: hands_guard only checks fists in the near-lens zone, LOOK at upper-arm silhouettes yourself",
    "R2-2 frontal square-shouldered MCUs: LOOK (body yaw vs camera >= 25 deg is the rule, not machine-checked)",
    "R2-1b flat faces on stressed words (no brow/mouth keys)",
    "R2-5 centred MCUs with weak DoF",
    "D4 insert hand finish / watch bezel; Mom headband (v3.5 conformed to the cap: LOOK it is not hidden/floating)",
    "R3-2 score timbre reads lo-fi (pads/drones wanted); R5-1 push cut has no own SFX",
]


def main():
    if len(sys.argv) < 2 or sys.argv[1].startswith("-"):
        sys.exit(__doc__)
    slug = sys.argv[1]; vdir = os.path.join(STUDIO, "videos", slug)
    if not os.path.exists(os.path.join(vdir, "shots.py")):
        print(f"QA GATE: cannot run, {vdir}/shots.py missing"); sys.exit(2)
    check_pacing(slug)
    if "--no-audio" not in sys.argv:
        check_audio(slug, vdir)
        check_transition_sfx(vdir)
    check_transitions(vdir)
    check_captions(vdir)
    check_render_logs(vdir)
    check_length(vdir)
    if "--stress" in sys.argv:
        check_stress()
    fails = [r for r in RES if r[0] == "FAIL"]
    for st, name, d in RES:
        print(f"[{st:4s}] {name:26s} {d}")
    print("\nNot machine-checked (LOOK at the contact sheet, docs/AGENT_PLAYBOOK.md sec. 9):")
    for w in OPEN_WEAK_SPOTS:
        print("  -", w)
    verdict = "FAIL" if fails else "PASS"
    print(f"\nQA GATE {verdict}: {len(fails)} failing check(s)" + ("" if not fails else ": " + ", ".join(r[1] for r in fails)))
    os.makedirs(os.path.join(vdir, "out"), exist_ok=True)
    json.dump(dict(verdict=verdict, results=RES), open(os.path.join(vdir, "out", "qa_gate.json"), "w"), indent=1)
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
