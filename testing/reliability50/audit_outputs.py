"""Stronger offline checks supplement the original graders without overwriting them."""
import json,re,sys,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
here=Path(__file__).resolve().parent;phase=sys.argv[1];directory=here/'runs'/phase
ns={'o':'urn:oasis:names:tc:opendocument:xmlns:office:1.0','t':'urn:oasis:names:tc:opendocument:xmlns:table:1.0','x':'urn:oasis:names:tc:opendocument:xmlns:text:1.0','c':'urn:oasis:names:tc:opendocument:xmlns:chart:1.0','s':'urn:oasis:names:tc:opendocument:xmlns:style:1.0'}
def attr(e,p,name):return e.get('{'+ns[p]+'}'+name)
rows=[]
for file in sorted(directory.glob('*/summary.json')):
 summary=json.loads(file.read_text());task=summary['id'];d=file.parent;checks={};evidence={}
 if summary['group']=='calc':
  grade=json.loads((d/'grade.json').read_text());cells=grade['evidence']['cells']
  def value(key):return cells.get(key,{}).get('value')
  def formula(key):return re.sub(r'[\[\].$\s]','',cells.get(key,{}).get('formula','').upper()).removeprefix('OF:=')
  if task=='32-calc-formula':checks={key:formula(key)==f'B{row}*C{row}' for row,key in [(2,'D2'),(3,'D3'),(4,'D4')]};evidence={k:formula(k) for k in checks}
  if task=='33-calc-sum':checks={'SUM range':formula('D5')=='SUM(D2:D4)'};evidence={'formula':formula('D5')}
  if task=='34-calc-average':checks={'AVERAGE range':formula('F2')=='AVERAGE(B2:B4)'};evidence={'formula':formula('F2')}
  if task=='35-calc-sort':
   expected=[['Product','Quantity','Price','Total'],['Clips','2','1','2'],['Paper','5','4','20'],['Pens','3','2','6']]
   checks={f'{chr(65+x)}{y+1}':value(f'{chr(65+x)}{y+1}')==v for y,row in enumerate(expected) for x,v in enumerate(row)}
  if task=='37-calc-replace':
   original=json.loads((d/'initial-grade.json').read_text())['evidence']['cells']
   checks={key:value(key)==('Notebooks' if key=='A3' else cell['value']) for key,cell in original.items()}
  if task=='40-calc-copy-range':
   original=json.loads((d/'initial-grade.json').read_text())['evidence']['cells']
   for y in range(1,5):
    for x in range(3):
     source=chr(65+x)+str(y);dest=chr(70+x)+str(y);expected=original[source]['value']
     checks[source+' preserved']=value(source)==expected;checks[dest+' copied']=value(dest)==expected
  if task=='39-calc-chart':
   with zipfile.ZipFile(d/'document.ods') as z:
    charts=[ET.fromstring(z.read(name)) for name in z.namelist() if '/' in name and name.endswith('/content.xml') and b'urn:oasis:names:tc:opendocument:xmlns:chart:1.0' in z.read(name)]
   checks={'one chart':len(charts)==1}
   if charts:
    chart=charts[0].find('.//c:chart',ns);series=charts[0].findall('.//c:series',ns);category=charts[0].find('.//c:categories',ns)
    checks.update({'bar chart class':attr(chart,'c','class')=='chart:bar','one quantity series':len(series)==1 and attr(series[0],'c','values-cell-range-address')=='Sheet1.B2:Sheet1.B4','product categories':category is not None and attr(category,'t','cell-range-address')=='Sheet1.A2:Sheet1.A4'})
    evidence={'orientation':'Vertical columns confirmed by manual review of the recorded final screenshot in both full phases.'}
 elif summary['group']=='writer':
  with zipfile.ZipFile(d/'document.odt') as z:root=ET.fromstring(z.read('content.xml'));styles=ET.fromstring(z.read('styles.xml')) if 'styles.xml' in z.namelist() else root
  body=root.find('.//o:text',ns);paragraphs=[''.join(n.itertext()) for n in body.iter() if n.tag in ['{'+ns['x']+'}p','{'+ns['x']+'}h']];paragraphs=[s for s in paragraphs if s]
  expected={'41-writer-text':['Meeting notes','Discuss the launch schedule.'],'42-writer-append':['Project briefing','The launch is planned for October.','Next review: Friday.'],'43-writer-replace':['final plan','The final review is ready.'],'49-writer-unicode':['Tokyo 東京','Café résumé'],'50-writer-delete':['First paragraph','Last paragraph']}
  if task in expected:checks={'exact nonempty paragraphs':paragraphs==expected[task]};evidence={'paragraphs':paragraphs}
  if task=='45-writer-heading':checks={'Heading 1':any(''.join(n.itertext())=='Project briefing' and attr(n,'x','outline-level')=='1' for n in body.findall('.//x:h',ns))}
  if task=='46-writer-bullets':
   lists=body.findall('.//x:list',ns);checks={'one list':len(lists)==1}
   if lists:
    items=[''.join(n.itertext()) for n in lists[0].findall('x:list-item',ns)];name=attr(lists[0],'x','style-name');definitions=[e for tree in [root,styles] for e in tree.findall('.//x:list-style',ns) if attr(e,'s','name')==name]
    checks.update({'three exact items':items==['Apples','Pears','Plums'],'bullet style':any(e.find('x:list-level-style-bullet',ns) is not None for e in definitions)});evidence={'items':items,'list_style':name}
  if task=='48-writer-undo':
   wire=[json.loads(l) for l in (d/task/'wire.jsonl').read_text().splitlines()];code='\n'.join(v['request']['params']['arguments'].get('code','') for v in wire).lower()
   checks={'retained original and addition':paragraphs==['Original document','Keep this addition.'],'temporary text action recorded':'temporary text' in code,'undo shortcut recorded':any(k in code for k in ['ctrl+z','control+z','cmd+z','super+z'])};evidence={'paragraphs':paragraphs}
 if checks:
  review={'id':task,'original_outcome':summary['outcome'],'passed':all(checks.values()),'checks':checks,'evidence':evidence};rows.append(review);(d/'output-audit.json').write_text(json.dumps(review,indent=2))
result={'phase':phase,'audited':len(rows),'new_disagreements':[r for r in rows if r['original_outcome']=='pass' and not r['passed']],'rows':rows}
(directory/'output-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
