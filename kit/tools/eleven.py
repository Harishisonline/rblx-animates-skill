"""ElevenLabs over the plain API, for machines without the ElevenLabs connector.
    python tools/eleven.py tts <slug>              videos/<slug>/script.txt -> videos/<slug>/audio/raw.mp3
    python tools/eleven.py sfx <name> "<prompt>"   -> sfx/raw/<name>.mp3 (then run tools/sfxprep.py)
    python tools/eleven.py check                   key present + voice reachable (free call)
    python tools/eleven.py voices                  list the voices on this account (free call)
    python tools/eleven.py sample "<text>" <voice name or id>[,<voice>...] [--model M] [--speed 1.1] [--stability .4] [--similarity .8] [--style .25] [--out DIR]
                                                   short audition clips so the user can pick the narrator BEFORE the full read
Key: env ELEVENLABS_API_KEY, or a line  ELEVENLABS_API_KEY=...  in .env next to config.json.
Voice and models: config.json voice_id, tts_model, sfx_model. The key is never printed."""
import json, os, sys, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit

API = "https://api.elevenlabs.io/v1"


def call(path, body=None, accept="audio/mpeg"):
    key = kit.api_key()
    if not key:
        sys.exit("No ElevenLabs key. Put  ELEVENLABS_API_KEY=your_key  in " + os.path.join(kit.STUDIO, ".env")
                 + "  (or set the environment variable), then run this again.")
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 method="POST" if body is not None else "GET",
                                 headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": accept})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:600]
        hint = ""
        if e.code == 401:
            hint = "\n(the key was rejected: check it in .env)"
        elif "voice" in msg.lower() and ("not found" in msg.lower() or "does not exist" in msg.lower()):
            hint = "\n(add this voice to your ElevenLabs account from the Voice Library, or set your own voice_id in config.json)"
        elif "quota" in msg.lower() or "credits" in msg.lower():
            hint = "\n(not enough ElevenLabs credits on this account)"
        sys.exit(f"ElevenLabs error {e.code}: {msg}{hint}")


def voice_settings(c, speed=None):
    """Natural-delivery settings. Speed is applied BY THE VOICE MODEL (no time-stretch artifacts); keep it <= 1.15."""
    return {"stability": c.get("tts_stability", 0.4), "similarity_boost": c.get("tts_similarity", 0.8),
            "style": c.get("tts_style", 0.4), "use_speaker_boost": True,
            **({} if (c.get("tts_speed") if speed is None else speed) is None
               else {"speed": c.get("tts_speed") if speed is None else speed})}  # hype_v3: no model speed, atempo in post


def list_voices():
    return json.loads(call("/voices", accept="application/json")).get("voices", [])


def script_text(slug):
    p = os.path.join(kit.STUDIO, "videos", slug, "script.txt")
    lines = [l.strip() for l in open(p, encoding="utf-8") if l.strip() and not l.lstrip().startswith("#")]
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    c = kit.cfg()
    what = sys.argv[1]
    if what == "check":
        info = json.loads(call(f"/voices/{c['voice_id']}", accept="application/json"))
        print(f"key ok, voice ok: {info.get('name', c['voice_id'])}")
    elif what == "voices":
        for v in list_voices():
            lb = v.get("labels", {})
            print(f"{v['voice_id']} | {v['name']} | {v.get('category')} | {lb.get('gender')} {lb.get('age')} {lb.get('descriptive') or ''} {lb.get('use_case') or ''}")
    elif what == "sample":
        text, names = sys.argv[2], [n.strip() for n in sys.argv[3].split(",")]
        opt = {sys.argv[i]: sys.argv[i + 1] for i in range(4, len(sys.argv) - 1, 2) if sys.argv[i].startswith("--")}
        model = opt.get("--model", c["tts_model"])
        speed = float(opt["--speed"]) if "--speed" in opt else c.get("tts_speed")
        vs_over = {k: float(opt[f"--{k}"]) for k in ("stability", "similarity", "style") if f"--{k}" in opt}
        out = opt.get("--out") or os.path.join(kit.STUDIO, "samples")
        os.makedirs(out, exist_ok=True)
        by = {v["name"].split(" - ")[0].lower(): v for v in list_voices()}
        by.update({v["voice_id"]: v for v in list_voices()})
        for n in names:
            v = by.get(n.lower()) or by.get(n)
            if not v:
                print("not on this account:", n); continue
            audio = call(f"/text-to-speech/{v['voice_id']}?output_format=mp3_44100_128",
                         {"text": text, "model_id": model, "voice_settings": dict(voice_settings(c, speed), **{({"similarity": "similarity_boost"}.get(k, k)): x for k, x in vs_over.items()})})
            fn = os.path.join(out, f"{v['name'].split(' - ')[0]}_{model}_x{speed}.mp3")
            open(fn, "wb").write(audio)
            print("wrote", fn)
    elif what == "tts":
        slug = sys.argv[2]
        text = script_text(slug)
        out = os.path.join(kit.STUDIO, "videos", slug, "audio", "raw.mp3")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        print(f"generating voice: {len(text)} characters (~{len(text)} credits), model {c['tts_model']}")
        # hype_v3: one call per script line (= one beat, opening with its [tag]) so v3 resets energy per beat
        chunks = text.split("\n") if c.get("tts_take_split") == "line" else [text]
        if c.get("tts_take_split") == "paragraph":  # intown_v1: consecutive lines grouped into takes <= tts_take_chars
            chunks, cur = [], ""
            for l in text.split("\n"):
                if cur and len(cur) + 1 + len(l) > c.get("tts_take_chars", 900):
                    chunks.append(cur); cur = l
                else:
                    cur = (cur + " " + l).strip()
            chunks.append(cur)
        audio = b"".join(call(f"/text-to-speech/{c['voice_id']}?output_format=mp3_44100_128",
                              {"text": t, "model_id": c["tts_model"], "voice_settings": voice_settings(c)}) for t in chunks)
        open(out, "wb").write(audio)  # mp3 frames concatenate; then post per preset: VOICE_SPEC.md INTOWN (intown_v1) / HYPE (hype_v3) recipe
        print(f"wrote {out} ({len(audio) // 1024} KB)")
    elif what == "sfx":
        name, prompt = sys.argv[2], " ".join(sys.argv[3:])
        out = os.path.join(kit.STUDIO, "sfx", "raw", name + ".mp3")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        audio = call("/sound-generation", {"text": prompt, "model_id": c["sfx_model"], "prompt_influence": 0.5})
        open(out, "wb").write(audio)
        print(f"wrote {out} ({len(audio) // 1024} KB). Next: python tools/sfxprep.py {os.path.relpath(out, kit.STUDIO)} sfx/{name}.wav")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
