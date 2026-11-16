import os
import json,os,sys,urllib.request
env=dict(l.strip().split('=',1) for l in open(os.path.join(os.environ.get('RBX_HOME',os.path.expanduser('~/RobloxStories')),'.env')) if '=' in l and not l.startswith('#'))
KEY=env.get('ELEVENLABS_API_KEY','').strip().strip('"')
def call(path, body=None, accept='application/json'):
    req=urllib.request.Request('https://api.elevenlabs.io/v1'+path,data=json.dumps(body).encode() if body else None,method='POST' if body else 'GET',headers={'xi-api-key':KEY,'Content-Type':'application/json','Accept':accept})
    with urllib.request.urlopen(req,timeout=600) as r: return r.read()
if __name__=='__main__':
    s=json.loads(call('/user/subscription'))
    print('tier',s.get('tier'),'used',s.get('character_count'),'limit',s.get('character_limit'),'left',s.get('character_limit',0)-s.get('character_count',0))
