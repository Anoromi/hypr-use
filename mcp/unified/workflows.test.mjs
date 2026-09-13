import test from 'node:test';
import assert from 'node:assert/strict';
import {createWorkflows,validateWorkflow,workflowTools} from './workflows.mjs';
function fixture(){
 const calls=[],out=[];let elements=[{index:1,name:'Name',value:'old',editable:true,supportsEditableText:true},{index:2,name:'Email',value:'',editable:true,supportsEditableText:true},{index:3,name:'Save',value:''}];
 const app={setValue:async(i,v)=>{calls.push(['set',i,v]);elements.find(e=>e.index===i).value=v;},click:async i=>calls.push(['click',i]),pressKey:async k=>calls.push(['key',k]),typeText:async t=>calls.push(['text',t]),paste:async t=>calls.push(['paste',t]),getAXState:async()=>calls.push(['observe'])};
 const read=async()=>({elements,treeLines:['Ready']});
 return {calls,out,app,elements,workflow:createWorkflows(app,read,v=>out.push(v))};
}
test('four explicit tools and strict preflight',()=>{
 assert.equal(workflowTools.length,4);
 for(const a of [{app:'a',target:{name:'Name'},text:'東京'},{app:'a',target:{name:'Name'},text:'x',typo:true}])assert.throws(()=>validateWorkflow('replace_text',a));
 assert.throws(()=>validateWorkflow('navigate',{app:'a',url:'file:///tmp/x'}));
 assert.throws(()=>validateWorkflow('wait_for',{app:'a',text:'a',target:{name:'b'}}));
});
test('invalid later field fails before any mutation; ambiguity also fails',async()=>{
 const f=fixture();await assert.rejects(f.workflow.fillForm({fields:[{name:'Name',value:'new'},{name:'Missing',value:'x'}]}),/found 0/);assert.equal(f.calls.length,0);
 f.elements.push({index:4,name:'Name',editable:true,supportsEditableText:true});await assert.rejects(f.workflow.replaceText({target:{name:'Name'},text:'new'}),/found 2/);assert.equal(f.calls.length,0);
});
test('fill verifies each field and submits once',async()=>{
 const f=fixture();const r=await f.workflow.fillForm({fields:[{name:'Name',value:'Ada'},{name:'Email',value:'ada@test'}],submit:{name:'Save'}});
 assert.equal(r.status,'completed');assert.deepEqual(f.calls,[['set',1,'Ada'],['set',2,'ada@test'],['click',3],['observe']]);
});
test('failed verification stops later mutations and reports partial progress',async()=>{
 const f=fixture();f.app.setValue=async()=>{};
 await assert.rejects(f.workflow.fillForm({fields:[{name:'Name',value:'new'}],submit:{name:'Save'}}),/does not match/);
 assert.equal(f.calls.length,0);assert.equal(JSON.parse(f.out[0].text).steps.at(-1).status,'failed');
});
test('empty replacement deletes selection; no implicit paste',async()=>{
 const f=fixture();await f.workflow.replaceText({target:{name:'Name'},text:''});assert.deepEqual(f.calls,[['click',1],['key','Ctrl+a'],['key','BackSpace'],['observe']]);
});
test('wait condition, dialog target and timeout',async()=>{
 const f=fixture();assert.equal((await f.workflow.waitFor({target:{name:'Name'},value:'old'})).status,'matched');
 await assert.rejects(f.workflow.waitFor({text:'missing',timeout_ms:1}),/timed out/);
 const w=createWorkflows(f.app,async()=>({attention:{title:'Confirm',target:'owned-dialog'}}),()=>{});
 assert.equal((await w.waitFor({dialog_title:'Confirm'})).target,'owned-dialog');
});
test('wait emits its matched snapshot without a second scan',async()=>{
 const f=fixture();let count=0,shown;
 const w=createWorkflows(f.app,async()=>{count++;return {elements:[{index:7,name:'Ready'}]};},()=>{},s=>shown=s);
 const r=await w.waitFor({target:{name:'Ready'}});assert.equal(count,1);assert.equal(shown.elements[0].index,r.index);assert.equal(f.calls.length,0);
});
test('navigate avoids double activation and reports submission only',async()=>{
 const f=fixture();f.elements[0].name='Address and search bar';
 const r=await f.workflow.navigate({url:'https://example.com'});assert.equal(r.status,'submitted');assert.equal(f.calls.filter(c=>c[0]==='click').length,1);assert.deepEqual(f.calls.at(-2),['key','Return']);
});

test('prototype property names are rejected as unknown arguments',()=>{
 assert.throws(()=>validateWorkflow('navigate',JSON.parse('{"app":"a","url":"https://example.com","__proto__":{}}')),/unknown option/);
});

test('field workflows ignore same-name labels but reject an explicit label',async()=>{
 const f=fixture();f.elements.push({index:4,name:'Name',controlType:'label',value:'Name',editable:false});
 await f.workflow.fillForm({fields:[{name:'Name',value:'Ada'}]});assert.deepEqual(f.calls[0],['set',1,'Ada']);
 f.calls.length=0;await assert.rejects(f.workflow.replaceText({target:{name:'Name',role:'label'},text:'x'}),/found 0/);assert.equal(f.calls.length,0);
});

test('Chromium entry without editable flags uses native keys, not a setter',async()=>{
 const f=fixture();Object.assign(f.elements[0],{controlType:'entry',editable:false,supportsEditableText:false});
 f.app.typeText=async text=>{f.calls.push(['text',text]);f.elements[0].value=text;};
 await f.workflow.fillForm({fields:[{name:'Name',value:'Ada'}]});assert.deepEqual(f.calls.slice(0,3),[['click',1],['key','Ctrl+a'],['text','Ada']]);
 f.calls.length=0;await assert.rejects(f.workflow.fillForm({fields:[{name:'Name',value:'Ada',method:'setValue'}]}),/no setter/);assert.equal(f.calls.length,0);
});

test('form reuses each verification snapshot until the next action',async()=>{
 const f=fixture();let reads=0;const w=createWorkflows(f.app,async()=>{reads++;return {elements:f.elements};},()=>{});
 await w.fillForm({fields:[{name:'Name',value:'Ada'},{name:'Email',value:'a@test'}],submit:{name:'Save'}});
 assert.equal(reads,3);assert.deepEqual(f.calls,[['set',1,'Ada'],['set',2,'a@test'],['click',3],['observe']]);
});
