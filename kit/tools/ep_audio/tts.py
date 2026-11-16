import os
import json,base64,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); 
from el import call
D=os.environ['EP'].rstrip('/')+'/audio/'
lines=[l.strip() for l in open(D+'../tts_script.txt') if l.strip()]
text=" ".join(lines)
body={"text":"[fast, urgent, breathless] "+text,"model_id":"eleven_v3","voice_settings":{"stability":0.0,"similarity_boost":0.75,"style":0.25,"use_speaker_boost":True}}
r=json.loads(call('/text-to-speech/yl2ZDV1MzN4HbQJbMihG/with-timestamps?output_format=mp3_44100_192',body))
open(D+'raw.mp3','wb').write(base64.b64decode(r['audio_base64']))
json.dump(r.get('normalized_alignment') or r.get('alignment'),open(D+'alignment.json','w'))
json.dump(r.get('alignment'),open(D+'alignment_raw.json','w'))
print('chars',len(body['text']))
