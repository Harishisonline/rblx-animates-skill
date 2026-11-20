#!/bin/zsh
# Kit v6 regression suite = the weekly self-learning loop's "test cases" (docs/GROWTH_LOOP.md section 9 step 2).
# Every gate must still PASS the viral references and still FAIL our known-bad takes; if a viral reference FAILS, the
# gate's threshold is wrong -> re-measure (self-update). usage: zsh tools/v6_selftest.sh [episode dir]  (log path printed)
export PATH=/opt/homebrew/bin:/usr/local/bin:$HOME/.local/bin:$PATH
K=$HOME/RobloxStories; E=$HOME/RobloxStories_tmp/research/ears
PY=${EARS_PY:-$HOME/RobloxStories_tmp/blocky_laugh/.venv/bin/python}
EP=${1:-$(ls -td $HOME/RobloxStories_tmp/*/script.txt 2>/dev/null | head -1 | xargs dirname)}
mkdir -p $HOME/RobloxStories_tmp/research/growth; LOG=$HOME/RobloxStories_tmp/research/growth/selftest_$(date +%F_%H%M).log
{
echo "kit v6 selftest $(date)  episode: $EP"
echo "== 1 ears_check: viral references (expect 0 FAIL)"
for v in AYdbna6xYrU J0OQXSo1chk RVszt4A-ucc TAYxdugYgzg; do [ -f $E/out/$v.json ] && $PY $K/tools/ears_check.py $E/out/$v.json | tail -1; done
echo "== 2 ears_check: our old takes (expect FAIL)"
for f in $E/out/OURS_*.json; do $PY $K/tools/ears_check.py $f | tail -1; done
echo "== 3 script_lint_v3: viral transcripts (expect 0 FAIL)"
for v in AYdbna6xYrU J0OQXSo1chk RVszt4A-ucc TAYxdugYgzg; do
  [ -f $E/out/$v.json ] || continue
  $PY -c "import json,sys;print(json.load(open('$E/out/$v.json'))['transcript'])" > /tmp/v6_$v.txt
  echo "$v: $($PY $K/tools/script_lint_v3.py /tmp/v6_$v.txt | tail -1)"
done
echo "== 4 latest episode"
if [ -n "$EP" ]; then
  $PY $K/tools/script_lint_v3.py $EP/script.txt
  [ -f $EP/audio/voice.wav ] && $PY $K/tools/ears_check.py $EP/audio/voice.wav --script $EP/script.txt
  [ -f $EP/package.json ] && $PY $K/tools/package_check.py $EP || echo "no package.json yet (package_check skipped)"
  [ -f $K/tools/ep_viral_check.py ] && $PY $K/tools/ep_viral_check.py $EP 2>&1 | tail -15
fi
echo "SELFTEST DONE $(date)"
} > $LOG 2>&1
echo $LOG
