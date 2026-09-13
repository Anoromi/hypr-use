"""Record plugin identity; label a declared-path fallback when /proc is restricted."""
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
instances=json.loads(subprocess.check_output(['hyprctl','instances','-j'],text=True))
signature=os.environ.get('HYPRLAND_INSTANCE_SIGNATURE')
matches=[i for i in instances if i['instance']==signature] if signature else instances
assert len(matches)==1,'Cannot identify the current compositor'
instance=matches[0];paths=set();verification='mapped binary'
try:lines=Path(f"/proc/{instance['pid']}/maps").read_text().splitlines()
except PermissionError:
 assert len(sys.argv)==3,'Pass the exact loaded plugin path when compositor maps are not readable'
 lines=[];paths.add(str(Path(sys.argv[2]).resolve()));verification='declared load-command path; compositor maps not readable'
for line in lines:
 parts=line.split(maxsplit=5)
 if len(parts)==6 and parts[5].endswith('/libhypr-agent-portal.so'):paths.add(parts[5])
assert len(paths)==1,'Expected exactly one mapped portal plugin'
plugins=json.loads(subprocess.check_output(['hyprctl','-j','plugin','list'],text=True));plugins=[p for p in plugins if p['name']=='hypr-agent-portal'];assert len(plugins)==1
path=Path(next(iter(paths)));result={'time':time.time(),'compositor_pid':instance['pid'],'instance':instance['instance'],'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'verification':verification,'plugin_metadata':plugins[0]}
Path(sys.argv[1]).write_text(json.dumps(result,indent=2));print(json.dumps(result))
