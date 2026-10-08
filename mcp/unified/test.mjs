import test from 'node:test';import assert from 'node:assert/strict';import {spawn} from 'node:child_process';import readline from 'node:readline';import {createFacade} from './facade.mjs';
test('AX clicks use guarded semantic input and key sequences preserve order',async()=>{
 const calls=[];const {cua}=createFacade(async(n,a)=>{calls.push([n,a]);return {content:[],structuredContent:{target:'owned'}};},()=>{});
 const app=await cua.getApp('Editor');await app.click(3);
 assert.equal(calls.at(-1)[1].element_click_mode,'auto');
 await app.pressKey('  CMD+a   1 0 Return  ');
 assert.equal(calls.at(-1)[1].key,'ctrl+a 1 0 Return');
 await app.pressKey('ArrowDown SHIFT+ArrowUp ctrl+ArrowLeft CMD+ArrowRight');
 assert.equal(calls.at(-1)[1].key,'down SHIFT+up ctrl+left ctrl+right');
 const count=calls.length;await assert.rejects(app.pressKey('  '),/empty/);assert.equal(calls.length,count);
});
test('facade bindings, numeric targets, diff output and images',async()=>{const calls=[],out=[];const response={content:[{type:'text',text:'1: Button\n2: Entry'},{type:'image',mimeType:'image/png',data:'YQ=='}],structuredContent:{target:'address:owned'}};const {cua}=createFacade(async(n,a)=>{calls.push([n,a]);return response;},b=>out.push(b));const app=await cua.getApp('Editor');assert.equal(out.length,1);await app.click(1);assert.equal(calls.at(-1)[1].element_index,'1');assert.equal(calls.at(-1)[1].app,'address:owned');await app.selectText(2,'x',{selectionType:'cursor_after'});assert.equal(calls.at(-1)[1].selection,'cursor_after');assert.equal(await app.getAXState(),'Accessibility state unchanged.');assert.equal((await app.getScreenshot({emit:false}))[0],97);assert.equal(out.length,2);await assert.rejects(app.click([1]),/target/);await assert.rejects(app.paste('x',{format:'html'}),/Rich paste/);});
test('binding retries a partial window title with a qualified live target',async()=>{
 const calls=[];const {cua}=createFacade(async(name,args)=>{
  calls.push([name,args]);
  if(name==='get_ax_state'&&args.app==='Target')throw Error('appNotFound');
  if(name==='list_apps')return {content:[],structuredContent:{windows:[{title:'Target [old]',target:'address:old',processStartTime:4},{title:'Target [task]',target:'address:new',processStartTime:9}]}};
  return {content:[],structuredContent:{target:args.app,treeLines:[],elements:[],accessibility:{status:'ok'}}};
 },()=>{});
 await cua.getApp('Target');assert.deepEqual(calls.map(([name,args])=>[name,args.app]),[['get_ax_state','Target'],['list_apps',undefined],['get_ax_state','address:new']]);
});
test('stdio MCP persistence, reset, validation, timeout',async()=>{const child=spawn(process.execPath,[new URL('./server.mjs',import.meta.url).pathname],{stdio:['pipe','pipe','pipe']});let id=0;const pending=new Map();readline.createInterface({input:child.stdout}).on('line',s=>{const r=JSON.parse(s);pending.get(r.id)?.(r);});const rpc=(method,params)=>new Promise(resolve=>{pending.set(++id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method,params})+'\n');});const call=(name,a)=>rpc('tools/call',{name,arguments:a});try{assert.equal((await rpc('tools/list',{})).result.tools.length,9);assert.equal((await call('js',{code:'let a=5;'})).result.isError,false);const r=await call('js',{code:'let a=6; nodeRepl.write(a);'});assert.equal(r.result.content[0].text,'6');const timed=await call('js',{code:"nodeRepl.write('partial output'); await new Promise(()=>{});",timeout_ms:100});assert.equal(timed.result.isError,true);assert.equal(timed.result.content[0].text,'partial output');assert.match(timed.result.content.at(-1).text,/timed out after 100 ms/);await call('js_reset',{});assert.equal((await call('js',{code:'nodeRepl.write(typeof a);'})).result.content[0].text,'undefined');assert.equal((await call('js',{code:'',permission:'full'})).result.isError,true);}finally{child.stdin.end();}});
test('stdio runtime provides bounded timers and top-level early return',async()=>{const child=spawn(process.execPath,[new URL('./server.mjs',import.meta.url).pathname],{stdio:['pipe','pipe','pipe']});let id=0;const pending=new Map();readline.createInterface({input:child.stdout}).on('line',s=>{const r=JSON.parse(s);pending.get(r.id)?.(r);});const call=(code,timeout_ms=1000)=>new Promise(resolve=>{pending.set(++id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method:'tools/call',params:{name:'js',arguments:{code,timeout_ms}}})+'\n');});try{let r=await call("await new Promise(resolve=>setTimeout(resolve,10));nodeRepl.write('done');");assert.equal(r.result.content[0].text,'done');r=await call("nodeRepl.write('before');return;nodeRepl.write('after');");assert.equal(r.result.isError,false);assert.deepEqual(r.result.content.map(x=>x.text),['before']);r=await call("setTimeout(()=>{},30001);");assert.equal(r.result.isError,true);assert.match(r.result.content.at(-1).text,/30000/);}finally{child.stdin.end();}});

test('post-action AX reuse stays separate from explicit screenshots',async()=>{
 const calls=[];let state='before';const {cua}=createFacade(async(name,args)=>{calls.push(name);if(name==='click')state='after';return {content:[{type:'text',text:state},{type:'image',mimeType:'image/png',data:'YQ=='}],structuredContent:{target:'address:owned',elements:[]}};},()=>{});
 const app=await cua.getApp('Editor');assert.equal(calls[0],'get_ax_state');await app.click(1);const count=calls.length;assert.match(await app.getAXState(),/after/);assert.equal(calls.length,count);await app.getScreenshot({emit:false});assert.equal(calls.at(-1),'get_screenshot');await app.getAXState();assert.equal(calls.at(-1),'get_ax_state');
});
test('large AX observations pass bounded extraction budgets and bypass cached state',async()=>{
 const calls=[];const {cua}=createFacade(async(name,args)=>{calls.push([name,args]);return {content:[],structuredContent:{target:'owned',treeLines:[],elements:[],accessibility:{status:'ok'}}};},()=>{});
 const app=await cua.getApp('Editor');await app.getAXState({maxRecords:1500,timeBudgetMs:12000,emit:false});
 assert.deepEqual(calls.at(-1),['get_ax_state',{app:'owned',max_records:1500,ax_time_budget_ms:12000}]);
 await assert.rejects(app.getAXState({maxRecords:99}),/100 to 10000/);await assert.rejects(app.getAXState({timeBudgetMs:30001}),/500 to 30000/);
});

test('deferred mutations require a real AX read and output avoids duplicate hints',async()=>{
 const calls=[],out=[];const {cua}=createFacade(async name=>{calls.push(name);return {content:[{type:'text',text:'duplicate hints'}],structuredContent:{target:'owned',windowTitle:'Editor',app:{name:'test'},accessibility:{status:'ok'},treeLines:['1 button Save'],elements:[],observationDeferred:name==='press_key'}};},b=>out.push(b));
 const app=await cua.getApp('test');assert.match(out[0].text,/1 button Save/);assert.doesNotMatch(out[0].text,/duplicate hints/);await app.pressKey('Escape');await app.getAXState();assert.equal(calls.at(-1),'get_ax_state');
});

test('large AX changes emit a complete tree while small changes retain diffs',async()=>{
 let lines=['0 frame Editor',...Array.from({length:30},(_,i)=>`${i+1} button Old ${i}`)];
 const {cua}=createFacade(async()=>({content:[],structuredContent:{target:'owned',windowTitle:'Editor',app:{name:'test'},accessibility:{status:'ok'},treeLines:lines}}),()=>{});
 const app=await cua.getApp('test');
 lines=lines.map(s=>s.replace('Old','New'));
 const changed=await app.getAXState({emit:false});assert.match(changed,/^App:/);assert.match(changed,/30 button New 29/);assert.doesNotMatch(changed,/Old/);
 lines[4]='4 button Updated';const small=JSON.parse(await app.getAXState({emit:false}));assert.deepEqual(small.added,['4 button Updated']);assert.deepEqual(small.removed,['4 button New 3']);
 assert.equal(await app.getAXState({emit:false}),'Accessibility state unchanged.');
});

test('fused typing keeps flags explicit and validates key budget before dispatch',async()=>{
 const calls=[];const {cua}=createFacade(async(n,a)=>{calls.push([n,a]);return {content:[],structuredContent:{target:'owned'}};},()=>{});
 const app=await cua.getApp('Editor');await app.typeText('hello',{replaceAll:true,submit:true});
 assert.deepEqual(calls.at(-1),['type_text',{app:'owned',text:'hello',method:'keys',replace_all:true,submit:true}]);
 const count=calls.length;await assert.rejects(app.typeText('x'.repeat(4096),{replaceAll:true}),/4096/);await assert.rejects(app.typeText('x',{submit:'yes'}),/booleans/);assert.equal(calls.length,count);
});

test('compact geometry preserves every coordinate and offers full labels',async()=>{
 const line='\t9 button Move Secondary Actions: press Frame: {x: -5, y: 10, width: 30, height: 40}';
 const state={target:'owned',treeLines:[line],accessibility:{status:'ok'}};const out=[];
 const {cua}=createFacade(async()=>({content:[],structuredContent:state}),x=>out.push(x));const app=await cua.getApp('Editor');
 assert.match(out[0].text,/Frame: \[-5,10,30,40\]/);assert.match(out[0].text,/\[x,y,width,height\]/);
 const full=await app.getAXState({compactGeometry:false,disableDiffing:true,emit:false});assert.ok(full.includes(line));
 assert.equal(state.treeLines[0],line);
});

test('direct workflow reuses binding read and emits only the final observation',async()=>{
 const calls=[],out=[];let value='old';
 const {executeWorkflow}=createFacade(async(name,args)=>{
  calls.push(name);if(name==='set_value'){value=args.value;return {structuredContent:{observationDeferred:true}};}
  return {content:[],structuredContent:{target:'owned',accessibility:{status:'ok'},elements:[{index:1,name:'Name',value,editable:true,supportsEditableText:true}],treeLines:[`1 text Name Value: ${value}`]}};
 },b=>out.push(b));
 await executeWorkflow('fill_form',{app:'Editor',fields:[{name:'Name',value:'new'}]});
 assert.deepEqual(calls,['get_ax_state','set_value','get_ax_state']);
 assert.equal(out.length,1);assert.match(out[0].text,/Value: new/);assert.doesNotMatch(out[0].text,/Value: old/);
 calls.length=0;await assert.rejects(executeWorkflow('fill_form',{app:'Editor',fields:[]}),/array length/);assert.equal(calls.length,0);
});

test('paste preserves the current edit context instead of guessing from table presence',async()=>{
 const calls=[];const {cua}=createFacade(async(name,args)=>{calls.push([name,args]);return {content:[],structuredContent:{target:'owned'}};},()=>{});
 const app=await cua.getApp('Editor');await app.paste('text\nmore text');
 assert.deepEqual(calls.at(-1),['paste_text',{app:'owned',text:'text\nmore text',prepare_grid:false}]);
});

test('dialog binding follows fresh relationship and checks title again',async()=>{
 const calls=[],out=[];let pending=true;
 const facade=createFacade(async(tool,args)=>{
  calls.push([tool,args.app]);
  const target=args.app==='Root'?'root':args.app;
  const state={target,windowTitle:target==='dialog-new'?'Find and Replace':'Root',treeLines:['ready'],elements:[],accessibility:{status:'ok'}};
  if(target==='root'&&!pending)state.attention={type:'active-related-popup',title:'Find and Replace',target:'dialog-new'};
  return {structuredContent:state,content:[]};
 },v=>out.push(v));
 const root=await facade.cua.getApp('Root');pending=false;const dialog=await root.getDialog({title:'Find and Replace'});
 await dialog.pressKey('Escape');assert.deepEqual(calls.slice(-3),[['get_ax_state','root'],['get_ax_state','dialog-new'],['press_key','dialog-new']]);
 await assert.rejects(root.getDialog({title:'',timeout_ms:1}),/nonempty/);
 await assert.rejects(root.getDialog({title:'Missing',timeout_ms:1}),/timed out/);
});
test('dialog recycled into a different title is not returned as requested dialog',async()=>{
 const f=createFacade(async(tool,args)=>({structuredContent:{target:args.app,windowTitle:args.app==='child'?'Other':'Root',attention:{type:'active-related-popup',title:'Wanted',target:'child'},elements:[],treeLines:[]},content:[]}),()=>{});
 const root=await f.cua.getApp('root');await assert.rejects(root.getDialog({title:'Wanted'}),/changed before binding/);
});

test('a bound dialog becomes the hyprnav target so the live view follows it',async()=>{
 const beats=[];const hyprnav={beat:b=>beats.push(b)};
 const state=target=>({content:[],structuredContent:{target,windowTitle:target==='address:0xdlg'?'Save File':'Editor',app:{name:'test'},accessibility:{status:'ok'},treeLines:['1 button Save'],elements:[],
  attention:target==='address:0xapp'?{type:'active-related-popup',title:'Save File',target:'address:0xdlg'}:undefined}});
 const {cua}=createFacade(async(n,a)=>state(a.app==='address:0xdlg'?'address:0xdlg':'address:0xapp'),()=>{},{hyprnav});
 const app=await cua.getApp('address:0xapp');
 assert.deepEqual(beats,[],'binding the root app beats through the worker, not the facade');
 const dialog=await app.getDialog({title:'Save File'});
 assert.deepEqual(beats,[{state:'working',target:'address:0xdlg',action:'dialog Save File'}]);
 await dialog.click(1);
});

test('recorder reads frame sizes and rejects bad options',async()=>{
 const {imageSize,createRecorder}=await import('./recorder.mjs');
 const png=Buffer.alloc(24);png.writeUInt32BE(0x89504e47,0);png.writeUInt32BE(641,16);png.writeUInt32BE(480,20);
 assert.deepEqual(imageSize(png),{width:641,height:480});
 const jpeg=Buffer.from([0xff,0xd8,0xff,0xe0,0,4,0,0,0xff,0xc0,0,11,8,0,200,1,44,3,0,0,0]);
 assert.deepEqual(imageSize(jpeg),{width:300,height:200});
 assert.throws(()=>imageSize(Buffer.from('nope')),/PNG or JPEG/);
 const recorder=createRecorder(async()=>png);
 await assert.rejects(recorder.start('app',{fps:60}),/fps/);
 await assert.rejects(recorder.start('app',{path:'relative.mp4'}),/absolute/);
 await assert.rejects(recorder.stop(),/No recording/);
});
test('stdio output is capped per call',async()=>{const child=spawn(process.execPath,[new URL('./server.mjs',import.meta.url).pathname],{stdio:['pipe','pipe','pipe'],env:{...process.env,HYPR_USE_MAX_OUTPUT_BYTES:'1000',HYPR_USE_NO_HYPRNAV:'1'}});let id=0;const pending=new Map();readline.createInterface({input:child.stdout}).on('line',s=>{const r=JSON.parse(s);pending.get(r.id)?.(r);});const call=code=>new Promise(resolve=>{pending.set(++id,resolve);child.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method:'tools/call',params:{name:'js',arguments:{code}}})+'\n');});try{let r=await call("for(let i=0;i<10;i++)nodeRepl.write('x'.repeat(300));");assert.equal(r.result.isError,false);assert.equal(r.result.content.length,4);assert.match(r.result.content.at(-1).text,/7 later block\(s\) dropped/);r=await call("nodeRepl.write('small');");assert.deepEqual(r.result.content.map(x=>x.text),['small']);}finally{child.stdin.end();}});
