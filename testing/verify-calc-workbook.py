"""Read-only verification of the workbook saved by the GUI agent."""
import csv,json,zipfile
from pathlib import Path
from decimal import Decimal
import xml.etree.ElementTree as ET
r=Path(__file__).resolve().parent
p=r/'calc-data/usa-age-groups-1950-2026.ods'
ns={'table':'urn:oasis:names:tc:opendocument:xmlns:table:1.0','office':'urn:oasis:names:tc:opendocument:xmlns:office:1.0','text':'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
def attr(node,prefix,name):return node.get('{'+ns[prefix]+'}'+name)
with zipfile.ZipFile(p) as z:
 assert z.read('mimetype')==b'application/vnd.oasis.opendocument.spreadsheet'
 root=ET.fromstring(z.read('content.xml'))
rows=[];types=[]
for row in root.findall('.//table:table',ns)[0].findall('table:table-row',ns):
 cells=[];celltypes=[]
 for c in row:
  if c.tag.rsplit('}',1)[-1] not in ('table-cell','covered-table-cell'):continue
  t=attr(c,'office','value-type');value=attr(c,'office','value') if t=='float' else '\n'.join(''.join(p.itertext()) for p in c.findall('text:p',ns))
  repeat=min(int(attr(c,'table','number-columns-repeated') or '1'),20-len(cells))
  cells.extend([value or '']*repeat);celltypes.extend([t]*repeat)
  if len(cells)>=20:break
 if any(cells):
  rows.append(cells);types.append(celltypes)
with (r/'calc-data/usa-age-groups-1950-2026.csv').open() as f:expected=list(csv.reader(f))
assert rows[0][:12]==expected[0],('headers',rows[0][:12])
assert len(rows)==len(expected)==78,(len(rows),len(expected))
for n,(actual,want) in enumerate(zip(rows[1:],expected[1:]),start=1):
 for col in [0,2,3,4,5,6,7]:
  assert types[n][col]=='float',('not numeric',n,col,types[n][col])
  assert Decimal(actual[col])==Decimal(want[col]),('value mismatch',n,col)
 for col in [1,8,9,10,11]:assert actual[col]==want[col],('text mismatch',n,col)
result={'file':str(p),'format':'ODF Spreadsheet','data_rows':77,'columns':12,'numeric_cells_verified':77*7,'all_cells_match_csv':True,'first_year':rows[1][0],'last_year':rows[-1][0],'projection_status':rows[-1][1]}
(r/'calc-session/workbook-verification.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
