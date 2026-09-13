"""Read-only URL grading matching OSWorld's expected-tab set."""
import json,urllib.request,hashlib,os
from pathlib import Path
from urllib.parse import urlparse
here=Path(__file__).resolve().parent;p=here/os.environ.get('HYPR_USE_RESTORE_PHASE','astra-published-restore')
owned=json.loads((p/'owned-browser.json').read_text())
tabs=[x for x in json.load(urllib.request.urlopen(f"http://127.0.0.1:{owned['port']}/json/list")) if x['type']=='page']
(p/'tabs-final.json').write_text(json.dumps(tabs,indent=2))
expected={'lonelyplanet.com','airbnb.com','tripadvisor.com'}
actual={urlparse(x['url']).hostname.removeprefix('www.') for x in tabs}
result=json.loads((p/'restore-last-tab/result.json').read_text())
passed=actual==expected and len(tabs)==3 and not result['refocus'] and result['exit']==0
review={'outcome':'pass' if passed else 'fail','method':'Controller read-only CDP inventory after agent exits, exact three expected page hosts; no browser state mutation.','expected_hosts':sorted(expected),'actual_hosts':sorted(actual),'page_count':len(tabs),'refocus':result['refocus'],'notes':'Only page type counted. This reproduces the requested URL set, not a visual-content test of third-party sites.'}
(p/'restore-last-tab/review.json').write_text(json.dumps(review,indent=2))
manifest=json.loads((p/'manifest.json').read_text());checks={f:hashlib.sha256((here.parents[1]/f).read_bytes()).hexdigest()==h for f,h in manifest['source_hashes'].items()};assert all(checks.values()),checks
(p/'source-verification.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(review))
