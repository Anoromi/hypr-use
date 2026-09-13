"""Fixed, independently reset tasks. Evaluator fields are never sent to agents."""
def catalog():
 tasks=[]
 def add(group,name,prompt,check,**extra):
  tasks.append(dict(id=f'{len(tasks)+1:02d}-{name}',group=group,prompt=prompt,check=check,**extra))
 for name,prompt,check,extra in [
 ('profile-name','Set Name to Ada Lovelace.',{'Name':'Ada Lovelace'},{}),
 ('contact-options','Set Email to ada@example.test and enable Newsletter.',{'Email':'ada@example.test','Newsletter':True},{}),
 ('country','Choose Germany in Country.',{'Country':'Germany'},{}),
 ('save-note','Write Background automation works in Note and save the note.',{'saved_note':'Background automation works'},{}),
 ('reopen-note','Replace Note with temporary edit, then reopen the saved note. It should read Original note.',{'Note':'Original note'}, {'saved_note':'Original note'}),
 ('replace-word','Set Note to alpha beta gamma, then replace only beta with DELTA.',{'Note':'alpha DELTA gamma'},{}),
 ('create-folder','Set Name to project-notes and use the create-folder button.',{'folder':'project-notes'},{}),
 ('confirm-dialog','Open the confirmation dialog and confirm it.',{'dialog_result':'confirmed'},{}),
 ('cancel-dialog','Open the confirmation dialog and cancel it.',{'dialog_result':'cancelled'},{}),
 ('delayed-dialog','Open the confirmation dialog, wait for it to appear, and confirm it.',{'dialog_result':'confirmed'},{'delay_ms':900})]:add('native',name,prompt,check,**extra)
 for name,prompt,check,extra in [
 ('google','Open a new tab at https://www.google.com.',{'url_contains':'google.com'},{}),
 ('example','Navigate to https://example.com and report the page heading.',{'url_contains':'example.com','answer':'Example Domain'},{}),
 ('wikipedia','Navigate to https://en.wikipedia.org/wiki/Ada_Lovelace and report her birth year.',{'url_contains':'Ada_Lovelace','answer':'1815'},{}),
 ('iana','Navigate to https://www.iana.org/help/example-domains and report the heading.',{'url_contains':'iana.org/help/example-domains','answer':'Example Domains'},{}),
 ('python','Navigate to https://www.python.org/about/ and report which programming language this site describes.',{'url_contains':'python.org/about','answer':'Python'},{}),
 ('restore-tab','Bring back the last tab that was closed.',{'tabs':['/start','/second','/third']},{'closed_tab':True}),
 ('back','Go to the Second page using its link, then go back to Start.',{'path':'/start','visited':'/second'},{}),
 ('forward','Visit Second using its link, go back, then go forward again.',{'path':'/second','visited':'/start'},{}),
 ('two-tabs','Open Second and Third in separate new tabs. Keep Start open.',{'tabs':['/start','/second','/third']},{}),
 ('scroll-target','Follow Long article and scroll down to its final section, then report the final code.',{'path':'/article','answer':'MAPLE-72','scrolled':True},{})]:add('navigation',name,prompt,check,**extra)
 for name,prompt,check in [
 ('web-profile','Set Full name to Grace Hopper and Email to grace@example.test, then save the profile.',{'name':'Grace Hopper','email':'grace@example.test','saved':True}),
 ('web-select','Select Japan as Country and save the profile.',{'country':'Japan','saved':True}),
 ('web-checks','Enable Email updates and disable SMS updates, then save.',{'updates':True,'sms':False,'saved':True}),
 ('web-radio','Choose Express shipping and save.',{'shipping':'Express','saved':True}),
 ('web-date','Set Appointment to 2026-10-21 and save.',{'date':'2026-10-21','saved':True}),
 ('web-modal','Open Review, then confirm the review in the dialog.',{'review':'confirmed'}),
 ('web-filter','Filter products to Accessories and sort by price, lowest first.',{'category':'Accessories','sort':'ascending'}),
 ('web-cart','Add one Cedar Keyboard and two Birch Mice to the local demo cart. Do not check out.',{'cart':{'Cedar Keyboard':1,'Birch Mouse':2}}),
 ('web-compare','Compare Cedar Keyboard and Birch Mouse. Write their combined price in Comparison total and save.',{'total':'75','saved':True}),
 ('web-edit','Change the note to alpha beta gamma, then replace beta with DELTA and save.',{'note':'alpha DELTA gamma','saved':True})]:add('web',name,prompt,check)
 calc=[
 ('table','Enter A1:C4 as Product,Quantity,Price / Pens,3,2 / Paper,5,4 / Clips,2,1.',{'cells':{'A1':'Product','B1':'Quantity','C1':'Price','A2':'Pens','B2':'3','C2':'2','A3':'Paper','B3':'5','C3':'4','A4':'Clips','B4':'2','C4':'1'}},'empty'),
 ('formula','Set D1 to Total and D2:D4 to formulas multiplying Quantity by Price for each row.',{'cells':{'D1':'Total','D2':'6','D3':'20','D4':'2'},'formulas':['D2','D3','D4']},'table'),
 ('sum','Set C5 to Grand total and D5 to the SUM of D2:D4.',{'cells':{'C5':'Grand total','D5':'28'},'formulas':['D5']},'totals'),
 ('average','Set F1 to Average quantity and F2 to a formula averaging B2:B4.',{'cells':{'F1':'Average quantity'},'numeric':{'F2':10/3},'formulas':['F2']},'totals'),
 ('sort','Sort A1:D4 by Product ascending, keeping the header.',{'cells':{'A1':'Product','A2':'Clips','A3':'Paper','A4':'Pens','B2':'2','B3':'5','B4':'3'}},'totals'),
 ('bold','Make A1:D1 bold.',{'bold':['A1','B1','C1','D1']},'totals'),
 ('replace','Replace Paper in A3 with Notebooks, leaving the numbers unchanged.',{'cells':{'A3':'Notebooks','B3':'5','C3':'4'}},'totals'),
 ('sheet-name','Rename Sheet1 to Inventory.',{'sheet':'Inventory'},'totals'),
 ('chart','Create a column chart of the products and quantities in A1:B4.',{'chart':True},'totals'),
 ('copy-range','Copy A1:C4 into F1:H4, preserving the original.',{'cells':{'F1':'Product','G1':'Quantity','H1':'Price','F2':'Pens','G2':'3','H2':'2','F3':'Paper','F4':'Clips','A1':'Product'}},'table')]
 for name,prompt,check,seed in calc:add('calc','calc-'+name,prompt+' Save the existing workbook with Ctrl+S.',check,seed=seed)
 writer=[
 ('text','Replace the document text with Meeting notes followed by a new paragraph saying Discuss the launch schedule.',{'contains':['Meeting notes','Discuss the launch schedule.']},''),
 ('append','Add a final paragraph saying Next review: Friday.',{'contains':['Project briefing','Next review: Friday.']},'Project briefing\nThe launch is planned for October.'),
 ('replace','Replace every occurrence of draft with final.',{'contains':['final plan','final review'],'absent':['draft']},'draft plan\nThe draft review is ready.'),
 ('bold','Make the words Project briefing bold.',{'bold_text':'Project briefing'},'Project briefing\nThe launch is planned for October.'),
 ('heading','Apply Heading 1 style to the first paragraph, Project briefing.',{'heading':'Project briefing'},'Project briefing\nThe launch is planned for October.'),
 ('bullets','Turn the three paragraphs Apples, Pears, and Plums into a bulleted list.',{'list':True,'contains':['Apples','Pears','Plums']},'Apples\nPears\nPlums'),
 ('table','Insert a table with two columns and three rows.',{'table_shape':[3,2]},''),
 ('undo','Append a paragraph saying Keep this addition. Then append another paragraph saying temporary text and undo that last addition.',{'contains':['Original document','Keep this addition'],'absent':['temporary text']},'Original document'),
 ('unicode','Replace the document text with Tokyo 東京 and Café résumé on separate paragraphs.',{'contains':['Tokyo 東京','Café résumé']},''),
 ('delete','Delete only the middle paragraph Remove this paragraph. Keep the first and last paragraphs.',{'contains':['First paragraph','Last paragraph'],'absent':['Remove this paragraph']},'First paragraph\nRemove this paragraph\nLast paragraph')]
 for name,prompt,check,seed in writer:add('writer','writer-'+name,prompt+' Save the existing document with Ctrl+S.',check,seed=seed)
 assert len(tasks)==50
 return tasks
if __name__=='__main__':
 import json;print(json.dumps(catalog(),indent=2))
