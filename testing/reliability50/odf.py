import zipfile,xml.etree.ElementTree as E,math
from html import escape
ns={'o':'urn:oasis:names:tc:opendocument:xmlns:office:1.0','t':'urn:oasis:names:tc:opendocument:xmlns:table:1.0','x':'urn:oasis:names:tc:opendocument:xmlns:text:1.0','s':'urn:oasis:names:tc:opendocument:xmlns:style:1.0','fo':'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0','d':'urn:oasis:names:tc:opendocument:xmlns:drawing:1.0'}
def a(node,p,k):return node.get('{'+ns[p]+'}'+k)
def seed(path,group,kind):
 declaration=' '.join(f'xmlns:{k}="{v}"' for k,v in ns.items())
 if group=='calc':
  rows=[] if kind=='empty' else [['Product','Quantity','Price'],['Pens',3,2],['Paper',5,4],['Clips',2,1]]
  if kind=='totals':
   for i,row in enumerate(rows):row.append('Total' if i==0 else [6,20,2][i-1])
  content='<t:table t:name="Sheet1">'
  for row in rows:
   content+='<t:table-row>'
   for value in row:
    content+=f'<t:table-cell o:value-type="float" o:value="{value}"><x:p>{value}</x:p></t:table-cell>' if isinstance(value,int) else f'<t:table-cell o:value-type="string"><x:p>{escape(value)}</x:p></t:table-cell>'
   content+='</t:table-row>'
  content+='</t:table>';body='spreadsheet';mime='application/vnd.oasis.opendocument.spreadsheet'
 else:
  content=''.join('<x:p>'+escape(line)+'</x:p>' for line in kind.split('\n'));body='text';mime='application/vnd.oasis.opendocument.text'
 xml=f'<?xml version="1.0" encoding="UTF-8"?><o:document-content {declaration} o:version="1.3"><o:automatic-styles/><o:body><o:{body}>{content}</o:{body}></o:body></o:document-content>'
 with zipfile.ZipFile(path,'w') as z:
  z.writestr('mimetype',mime);z.writestr('content.xml',xml)
  z.writestr('META-INF/manifest.xml',f'<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.3"><manifest:file-entry manifest:full-path="/" manifest:media-type="{mime}"/><manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/></manifest:manifest>')
def inspect(path,group,check):
 with zipfile.ZipFile(path) as z:
  root=E.fromstring(z.read('content.xml'));styles={}
  for doc in [root]+([E.fromstring(z.read('styles.xml'))] if 'styles.xml' in z.namelist() else []):
   for n in doc.iter():
    if a(n,'s','name'):styles[a(n,'s','name')]=n
  def bold(style,seen=None):
   seen=set() if seen is None else seen
   if not style or style in seen or style not in styles:return False
   seen.add(style);n=styles[style];prop=n.find('s:text-properties',ns)
   return prop is not None and a(prop,'fo','font-weight')=='bold' or bold(a(n,'s','parent-style-name'),seen)
  checks={};evidence={}
  if group=='calc':
   table=root.find('.//t:table',ns);cells={};y=1
   for row in table.findall('t:table-row',ns):
    x=0
    for c in row:
     if c.tag not in ['{'+ns['t']+'}table-cell','{'+ns['t']+'}covered-table-cell']:continue
     for _ in range(min(int(a(c,'t','number-columns-repeated') or 1),26-x)):
      cells[chr(65+x)+str(y)]={'value':a(c,'o','value') or ''.join(c.itertext()),'formula':a(c,'t','formula'),'bold':bold(a(c,'t','style-name'))};x+=1
     if x>=26:break
    y+=int(a(row,'t','number-rows-repeated') or 1)
    if y>30:break
   for key,val in check.get('cells',{}).items():checks[key]=cells.get(key,{}).get('value')==val
   for key,val in check.get('numeric',{}).items():
    try:checks[key]=math.isclose(float(cells[key]['value']),val,rel_tol=1e-6)
    except (KeyError,ValueError):checks[key]=False
   for key in check.get('formulas',[]):checks[key+' formula']=bool(cells.get(key,{}).get('formula'))
   for key in check.get('bold',[]):checks[key+' bold']=cells.get(key,{}).get('bold',False)
   if 'sheet' in check:checks['sheet']=a(table,'t','name')==check['sheet']
   if 'chart' in check:checks['chart']=any(n.endswith('/content.xml') and b'urn:oasis:names:tc:opendocument:xmlns:chart:1.0' in z.read(n) for n in z.namelist())
   evidence={'cells':cells,'sheet':a(table,'t','name')}
  else:
   text='\n'.join(''.join(n.itertext()) for n in root.findall('.//x:p',ns)+root.findall('.//x:h',ns))
   for val in check.get('contains',[]):checks['contains '+val]=val in text
   for val in check.get('absent',[]):checks['absent '+val]=val not in text
   if 'bold_text' in check:checks['bold']=any(check['bold_text'] in ''.join(n.itertext()) and bold(a(n,'x','style-name')) for n in root.iter())
   if 'heading' in check:checks['heading']=any(check['heading']==''.join(n.itertext()) for n in root.findall('.//x:h',ns))
   if 'list' in check:checks['list']=root.find('.//x:list',ns) is not None
   if 'table_shape' in check:
    table=root.find('.//t:table',ns);rows=table.findall('t:table-row',ns) if table is not None else []
    checks['table_shape']=len(rows)==check['table_shape'][0] and all(len(r.findall('t:table-cell',ns))==check['table_shape'][1] for r in rows)
   evidence={'text':text}
  return {'passed':bool(checks) and all(checks.values()),'checks':checks,'evidence':evidence}
