"""Five-repeat direct latency probes, separate from model task comparisons."""
import json, math, statistics, subprocess, sys
from pathlib import Path

here = Path(__file__).resolve().parent
cases = {
    'ax': "for(let i=0;i<5;i++) await app.getAXState({emit:false,disableDiffing:true});",
    'screenshot': "for(let i=0;i<5;i++) await app.getScreenshot({emit:false});",
    'set-value': "for(let i=0;i<5;i++) await app.setValue(3,'Latency probe '+i);",
    'key': "for(let i=0;i<5;i++) await app.pressKey('Escape');",
}
prefix = sys.argv[1] if len(sys.argv)>1 else "probe"
if not prefix.replace("-", "").isalnum(): raise ValueError("invalid probe prefix")
output = here/(prefix+"-results.json")
if output.exists(): raise FileExistsError(output)
results = {}
for name, code in cases.items():
    path = here/'validation'/(prefix+'-'+name+'.js')
    path.parent.mkdir(exist_ok=True)
    path.write_text("let app=await cua.getApp('hypr-use-bench');\n"+code)
    subprocess.run([sys.executable,str(here/'validate.py'),prefix+'-'+name,str(path),'class:hypr-use-bench'],check=True)
    response = json.loads((here/'validation'/(prefix+'-'+name)/'response.json').read_text())['result']
    if response.get('isError'):
        results[name]={'status':'failed','response':str(here/'validation'/(prefix+'-'+name)/'response.json')}
        output.write_text(json.dumps(results,indent=2))
        raise RuntimeError(f'{name} failed; do not summarize as a latency success')
    operations = response['_meta']['hypr-use/timing']['operations'][1:]
    values = [x['duration_ms']/1000 for x in operations]
    if len(values)!=5: raise RuntimeError(f'{name}: expected 5 operations, got {len(values)}')
    results[name] = {'seconds':values,'median_s':statistics.median(values),'max_s':max(values),'p95_nearest_rank_s':sorted(values)[math.ceil(.95*len(values))-1]}
    output.write_text(json.dumps(results,indent=2))
    print(name,results[name],flush=True)
