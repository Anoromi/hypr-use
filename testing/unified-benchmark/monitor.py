import json,os,socket,subprocess,threading,time
from pathlib import Path

def ctl(action):return json.loads(subprocess.check_output(['hyprctl','-j',action],text=True))
class Monitor:
 def __init__(self,path,classes):
  self.path=Path(path);self.classes=set(classes);self.targets=set();self.stop=False;self.trigger=threading.Event();self.stage='setup';self.violations=[];self.callback=lambda:None;self.baseline=ctl('activewindow');self.active=self.baseline.get('address','');self.lock=threading.Lock()
  self.socket=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.socket.connect(os.environ['XDG_RUNTIME_DIR']+'/hypr/'+os.environ['HYPRLAND_INSTANCE_SIGNATURE']+'/.socket2.sock');self.socket.settimeout(.2)
  for w in ctl('clients'):
   if w['class'] in self.classes:self.targets.add(w['address'])
  self.record('initial-targets',sorted(self.targets))
  if self.active in self.targets:raise RuntimeError('Test target is currently your active window; choose a background target')
  self.threads=[threading.Thread(target=fn,daemon=True) for fn in (self.events,self.poll)]
  for t in self.threads:t.start()
 def record(self,kind,data):
  with self.lock:
   with self.path.open('a') as f:f.write(json.dumps({'time':time.time(),'monotonic':time.monotonic(),'stage':self.stage,'kind':kind,'data':data})+'\n')
 def check(self,address):
  if address in self.targets and not self.trigger.is_set():
   row={'address':address,'stage':self.stage,'time':time.time()};self.violations.append(row);self.record('refocus',row);self.trigger.set();self.callback()
 def events(self):
  pending=''
  while not self.stop:
   try:data=self.socket.recv(65536)
   except socket.timeout:continue
   except OSError:return
   if not data:
    if not self.stop:self.record('observer-error','socket closed');self.trigger.set();self.callback()
    return
   pending+=data.decode(errors='replace')
   while '\n' in pending:
    line,pending=pending.split('\n',1);kind,_,value=line.partition('>>')
    self.handle_event(kind,value)
 def handle_event(self,kind,value):
  if kind in ('openwindow','activewindowv2','workspacev2','movewindowv2','closewindow'):self.record(kind,value)
  if kind=='closewindow':self.targets.discard('0x'+value.removeprefix('0x'))
  if kind=='openwindow':
   parts=value.split(',',3)
   address='0x'+parts[0].removeprefix('0x')
   self.targets.discard(address)  # A compositor address can belong to a new client.
   if len(parts)>2 and parts[2] in self.classes:self.targets.add(address);self.check(self.active)
  if kind=='activewindowv2':self.active='0x'+value.removeprefix('0x') if value else '';self.check(self.active)
 def poll(self):
  while not self.stop:
   try:
    w=ctl('activewindow')
    if w.get('class') in self.classes:self.targets.add(w['address'])
    else:self.targets.discard(w.get('address'))
    self.record('sample',{'address':w.get('address'),'class':w.get('class')});self.check(w.get('address'))
   except Exception as e:self.record('observer-error',str(e));self.trigger.set();self.callback()
   time.sleep(.1)
 def close(self):self.stop=True;self.socket.close()
