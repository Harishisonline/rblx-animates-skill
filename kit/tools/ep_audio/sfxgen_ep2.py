import os
import json,sys,os,base64
sys.path.insert(0,os.path.expanduser('~/w'))
from el import call
D=os.path.join(os.environ['EP'],'sfx')+'/'
jobs={
 'ohhh':('School crowd of kids going "Ooooh!" together, teasing reaction, short, indoor hallway',2.0),
 'dundun':('Dramatic three note orchestral sting, dun dun dunnn, cartoon suspense reveal',3.0),
 'scratch':('Vinyl record scratch stop, comedic',1.0),
 'trombone':('Sad trombone wah wah wah waaah, comedic fail',3.0),
}
for n,(p,d) in jobs.items():
    a=call('/sound-generation',{"text":p,"duration_seconds":d,"prompt_influence":0.6,"model_id":"eleven_text_to_sound_v2"},accept='audio/mpeg')
    open(D+n+'.mp3','wb').write(a); print(n,len(a))
for n,t in {'bruh':'[deadpan] Bruh.','fahhh':'[exasperated] Fahhhh!'}.items():
    a=call('/text-to-speech/yl2ZDV1MzN4HbQJbMihG?output_format=mp3_44100_128',{"text":t,"model_id":"eleven_v3","voice_settings":{"stability":0.0,"similarity_boost":0.75,"style":0.25,"use_speaker_boost":True}},accept='audio/mpeg')
    open(D+n+'.mp3','wb').write(a); print(n,len(a))
