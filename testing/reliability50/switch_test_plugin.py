"""Switch explicitly recorded test builds; restore the old build on load failure."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
record_path=root/'testing/live-session/active-plugin.json'
def ctl(*args):return subprocess.check_output(['hyprctl',*args],text=True).strip()
def save(path,reason):
 record={'time':time.time(),'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'hyprland':json.loads(ctl('version','-j')),'plugins':json.loads(ctl('plugins','list','-j')),'load':'ok','reason':reason,'provenance':'Explicit load command and binary hash; process mappings are not readable.'}
 record_path.write_text(json.dumps(record,indent=2)+'\n');(root/f'testing/reliability50/diagnostics/plugin-switch-{time.time_ns()}.json').write_text(json.dumps(record,indent=2)+'\n');return record
if __name__=='__main__':
 target=(root/'testing/plugin-reliability-sequence-result/lib/libhypr-agent-portal.so') if sys.argv[1]=='baseline' else Path(sys.argv[1]).resolve()
 assert target.is_file();previous=json.loads(record_path.read_text());old=Path(previous['path'])
 current=json.loads(ctl('plugins','list','-j'));assert [p for p in current if p['name']=='hypr-agent-portal']==[p for p in previous['plugins'] if p['name']=='hypr-agent-portal'],'Loaded plugin differs from recorded build'
 assert json.loads(ctl('version','-j'))['commit']=='efb50993780079460b0cbed1363e2166a2de1d9f'
 assert not any(w['class'] in ['hypr-use-bench','hypr-use-r50-browser','libreoffice-calc','libreoffice-writer'] for w in json.loads(ctl('clients','-j'))),'Owned test windows remain'
 assert ctl('plugin','unload',str(old))=='ok'
 try:
  assert ctl('plugin','load',str(target))=='ok'
  assert any(p['name']=='hypr-agent-portal' for p in json.loads(ctl('plugins','list','-j')))
 except Exception:
  assert ctl('plugin','load',str(old))=='ok';save(old,'Restored after candidate load failure');raise
 record=save(target,'Explicit test build switch');print(json.dumps({k:record[k] for k in ['path','sha256']}))
