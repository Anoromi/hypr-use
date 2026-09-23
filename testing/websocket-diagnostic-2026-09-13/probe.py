import os,struct,zlib,subprocess,time,json
from pathlib import Path
p=Path('/tmp/hypr-ws-diagnostic')
def chunk(t,d):return struct.pack('!I',len(d))+t+d+struct.pack('!I',zlib.crc32(t+d)&0xffffffff)
w,h=1200,800
for i in range(8):
 raw=b''.join(b'\0'+os.urandom(w*3) for _ in range(h))
 (p/f'noise{i}.png').write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
for label,n in [('small',1),('large',8)]:
 cmd=['codex','exec','--ignore-user-config','--skip-git-repo-check','--ephemeral','--json','-C',str(p),'-m','gpt-6-astra','-s','read-only','-c','features.shell_tool=false','-c','features.plugins=false']
 for i in range(n):cmd+=['-i',str(p/f'noise{i}.png')]
 cmd+=['--','These are synthetic noise test images. Reply exactly CONNECTION_OK. Do not use tools.']
 start=time.monotonic()
 with (p/f'{label}.jsonl').open('w') as out,(p/f'{label}.stderr').open('w') as err:
  try:r=subprocess.run(cmd,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=90);code=r.returncode
  except subprocess.TimeoutExpired:code='timeout'
 print(json.dumps({'case':label,'seconds':time.monotonic()-start,'exit':code}),flush=True)
