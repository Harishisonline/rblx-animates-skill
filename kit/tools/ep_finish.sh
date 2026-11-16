#!/bin/zsh
# Kit v4.3: captions + ending pop-ups + ONE final export for one episode (no episode-specific names, words or durations).
# usage: tools/ep_finish.sh <episode_dir>
# needs: frames/####.png, audio/words.json, audio/mix_nomusic.wav (sets the length), audio/mix_final.wav (the mix with the bed)
# out:   out/video_only.mp4, out/final.mp4 (the one video to deliver)
EP=${1:A}; cd ~/RobloxStories
export PATH=/opt/homebrew/bin:/usr/local/bin:$PATH
LOG=$EP/out/ep_finish.log; mkdir -p $EP/out
for f in audio/words.json audio/mix_nomusic.wav audio/mix_final.wav frames/0001.png; do
  [ -e $EP/$f ] || { echo "MISSING $EP/$f" | tee -a $LOG; exit 2; }
done
echo "captions start $(date)" > $LOG
.venv/bin/python tools/ep_captions.py $EP final >> $LOG 2>&1 || { echo "CAPTIONS FAILED" >> $LOG; exit 1; }
for m in final; do
  ffmpeg -v error -y -i $EP/out/video_only.mp4 -i $EP/audio/mix_$m.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k \
    -shortest -movflags +faststart $EP/out/$m.mp4 >> $LOG 2>&1
  echo "$m: $(ffprobe -v error -show_entries format=duration -of csv=p=0 $EP/out/$m.mp4) s" >> $LOG
  ffmpeg -hide_banner -i $EP/out/$m.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "I:|Peak:" | tail -2 >> $LOG
done
echo "ALL DONE $(date)" >> $LOG
