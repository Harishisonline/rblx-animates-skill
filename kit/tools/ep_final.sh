#!/bin/zsh
# Kit v4.0: full-quality render, one shot per Blender run (crash-safe), with the blender lock and a disk guard.
# usage: tools/ep_final.sh <slug> [samples=32] [ids...]   -> videos/<slug>/frames/####.png, log videos/<slug>/out/ep_final.log
SLUG=$1; SAMPLES=${2:-32}; if (( $# >= 2 )); then shift 2; else shift 1; fi
cd ~/RobloxStories; EP=videos/$SLUG; mkdir -p $EP/out; LOG=$EP/out/ep_final.log
L=~/RobloxStories_tmp/blender.lock
until mkdir $L 2>/dev/null; do sleep 20; done
N=$(cat $EP/shots.py $EP/shots_[a-z].py 2>/dev/null | grep -c "^@S(")  # v4.2: counts split shot parts too
echo "start $(date) shots=$N samples=$SAMPLES" >> $LOG
IDS=$(cat $EP/shots.py $EP/shots_[a-z].py 2>/dev/null | grep -oE "^@S\( *[0-9]+" | grep -oE "[0-9]+" | sort -n | uniq | tr "\n" " ")  # v4.3: real @S ids (EP4 ids 1-42,50-76)
for s in ${@:-$=IDS}; do
  for try in 1 2; do
    free=$(df -g ~ | tail -1 | awk '{print $4}')
    if [ "$free" -lt 8 ]; then echo "LOW DISK ${free}G stop $(date)" >> $LOG; rmdir $L; exit 3; fi
    /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P tools/render.py -- $SLUG final $s $SAMPLES >> $EP/out/ep_final_stdout.log 2>&1; rc=$?
    echo "shot $s try $try rc=$rc $(date +%T)" >> $LOG
    [ $rc -eq 0 ] && break
  done
done
echo "ALL DONE $(date)" >> $LOG
rmdir $L
