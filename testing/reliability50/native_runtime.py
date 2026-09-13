"""Validate the explicitly recorded native plugin used by desktop benchmarks."""
import hashlib,json,subprocess
from pathlib import Path

def native_runtime(root,run=subprocess.check_output):
 record_path=Path(root)/'testing/live-session/active-plugin.json'
 record=json.loads(record_path.read_text());binary=Path(record['path'])
 digest=hashlib.sha256(binary.read_bytes()).hexdigest()
 if digest!=record['sha256']:raise RuntimeError('Recorded native plugin binary changed')
 loaded=json.loads(run(['hyprctl','plugins','list','-j'],text=True))
 current=[p for p in loaded if p['name']=='hypr-agent-portal']
 expected=[p for p in record['plugins'] if p['name']=='hypr-agent-portal']
 if not current or current!=expected:raise RuntimeError('Loaded native plugin differs from the recorded build')
 version=json.loads(run(['hyprctl','version','-j'],text=True))
 if version.get('commit')!=record['hyprland'].get('commit'):raise RuntimeError('Compositor changed since recorded plugin load')
 return {'path':str(binary),'sha256':digest,'plugins':current,'hyprland':version,'provenance':'Explicit load record and binary hash, checked against current plugin metadata. Process mappings are not readable.'}
