"""Kit v4.0 render ETA. usage: python tools/ep_eta.py <episode_dir> [log=out/ep_final.log]
Render cost scales with SCREEN TIME, not shot count: EP2 measured 1.3-1.7 min of render per second of shot
(1080x1920, 32 samples, M-series Mac; 105 s video = 142 min). Uses the live rate once 5 shots are done."""
import json, os, re, sys, datetime
ep = os.path.abspath(os.path.expanduser(sys.argv[1]))
logp = os.path.join(ep, sys.argv[2] if len(sys.argv) > 2 else "out/ep_final.log")
W = json.load(open(os.path.join(ep, "audio", "words.json")))
src = open(os.path.join(ep, "shots.py")).read()
spans = {int(a): (int(b), c) for a, b, c in re.findall(r"@S\((\d+), (\d+), (\w+),", src)}
def length(i):
    a, c = spans[i]
    return (W[int(c)]["start"] if c != "None" else W[-1]["end"]) - W[a]["start"]
txt = open(logp).read().split("start ")[-1] if os.path.exists(logp) else ""
done = [int(s) for s in re.findall(r"shot (\d+) try \d rc=0", txt)]
m = re.search(r"(\d+):(\d+):(\d+)", txt)
now = datetime.datetime.now()
if done and m:
    t0 = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=int(m.group(3)))
    spent = (now - t0).total_seconds() / 60
    secs_done = sum(length(i) for i in done)
    rate = spent / secs_done if len(done) >= 5 and secs_done > 0 else 1.45
    rate = rate if 0.3 < rate < 6 else 1.45   # clock/timezone mismatch guard (run it on the Mac)
else:
    rate = 1.45
left = sum(length(i) for i in spans if i not in done)
eta = now + datetime.timedelta(minutes=left * rate)
print(f"shots done {len(done)}/{len(spans)} | screen time left {left:.0f} s | rate {rate:.2f} min/s | "
      f"render ETA {eta:%H:%M} | files ready ~{(eta + datetime.timedelta(minutes=5)):%H:%M}")
