"""Verify actual saved workbook data, formulas, and chart presence."""
import json,sys,zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
path=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parent/'live/benchmark.ods'
ns={'t':'urn:oasis:names:tc:opendocument:xmlns:table:1.0','o':'urn:oasis:names:tc:opendocument:xmlns:office:1.0','x':'urn:oasis:names:tc:opendocument:xmlns:text:1.0','d':'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0','s':'urn:oasis:names:tc:opendocument:xmlns:style:1.0','n':'urn:oasis:names:tc:opendocument:xmlns:datastyle:1.0','fo':'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0'}
def attr(n,p,k):return n.get('{'+ns[p]+'}'+k)
r={'path':str(path),'exists':path.exists(),'checks':{}}
if path.exists():
 try:
  with zipfile.ZipFile(path) as z:
   root=ET.fromstring(z.read('content.xml'));table=root.find('.//t:table',ns);rows=[]
   if table is None:raise ValueError('Missing spreadsheet table')
   for row in table.findall('t:table-row',ns):
    cells=[]
    for c in row:
     if c.tag not in ['{'+ns['t']+'}table-cell','{'+ns['t']+'}covered-table-cell']:continue
     value=attr(c,'o','value') or ''.join(c.itertext()).strip()
     cell={'value':value,'formula':attr(c,'t','formula'),'style':attr(c,'t','style-name')}
     cells.extend([cell]*min(int(attr(c,'t','number-columns-repeated') or 1),8-len(cells)))
     if len(cells)>=8:break
    rows.extend([cells]*min(int(attr(row,'t','number-rows-repeated') or 1),8-len(rows)))
    if len(rows)>=8:break
   r['cells']=rows
   def v(y,x):return rows[y][x]['value'] if y<len(rows) and x<len(rows[y]) else ''
   expected=[['Product','Quantity','Price','Total'],['Clips','2','1','2'],['Paper','5','4','20'],['Pens','3','2','6']]
   r['checks']['sorted_table_and_values']=all(v(y,x)==value for y,row in enumerate(expected) for x,value in enumerate(row))
   r['checks']['grand_total']=v(4,2)=='Grand total' and v(4,3)=='28'
   r['checks']['formulas_retained']=all(y<len(rows) and len(rows[y])>3 and bool(rows[y][3]['formula']) for y in range(1,5))
   r['checks']['embedded_chart']=any(name.endswith('/content.xml') and b'urn:oasis:names:tc:opendocument:xmlns:chart:1.0' in z.read(name) for name in z.namelist())
   styles={}
   for document in [root,ET.fromstring(z.read('styles.xml'))]:
    for element in document.iter():
     if attr(element,'s','name'):styles[attr(element,'s','name')]=element
   def style_property(name,child,namespace,key,seen=None):
    seen=set() if seen is None else seen
    if not name or name in seen or name not in styles:return None
    seen.add(name);style=styles[name];node=style.find('s:'+child,ns)
    value=attr(node,namespace,key) if node is not None else None
    return value if value is not None else style_property(attr(style,'s','parent-style-name'),child,namespace,key,seen)
   def number_style(name,seen=None):
    seen=set() if seen is None else seen
    if not name or name in seen or name not in styles:return None
    seen.add(name);style=styles[name]
    data=attr(style,'s','data-style-name')
    return styles.get(data) if data else number_style(attr(style,'s','parent-style-name'),seen)
   headers=[style_property(rows[0][x]['style'],'text-properties','fo','font-weight') for x in range(min(4,len(rows[0])))] if rows else []
   r['checks']['header_bold']=len(headers)==4 and all(x=='bold' for x in headers)
   decimals=[]
   for y in range(1,5):
    name=rows[y][3]['style'] if y<len(rows) and len(rows[y])>3 else None
    style=number_style(name);number=style.find('n:number',ns) if style is not None else None
    decimals.append(attr(number,'n','decimal-places') if number is not None else None)
   r['checks']['totals_two_decimals']=all(v=='2' for v in decimals)
   r['formatting_evidence']={'header_weights':headers,'decimal_places':decimals,'scope':'Cell styles and parent styles; row/column default styles are not resolved.'}
 except Exception as ex:r['error']=str(ex)
print(json.dumps(r,indent=2))
