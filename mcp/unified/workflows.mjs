// Common operations share the ordinary guarded facade; no raw input bypass.
const selector={type:'object',properties:{name:{type:'string',minLength:1},role:{type:'string'}},required:['name'],additionalProperties:false};
const field={type:'object',properties:{...selector.properties,value:{type:'string'},method:{enum:['setValue','keys','paste']}},required:['name','value'],additionalProperties:false};
const schemas={
 fill_form:{fields:{type:'array',minItems:1,maxItems:20,items:field},submit:selector},
 replace_text:{target:selector,text:{type:'string'},method:{enum:['setValue','keys','paste']},submit:{type:'boolean'}},
 navigate:{url:{type:'string'},new_tab:{type:'boolean'},address:selector},
 wait_for:{target:selector,value:{type:'string'},text:{type:'string',minLength:1},dialog_title:{type:'string',minLength:1},timeout_ms:{type:'integer',minimum:1,maximum:30000}}
};
const required={fill_form:['fields'],replace_text:['target','text'],navigate:['url'],wait_for:[]};
const descriptions={
 fill_form:'Fill named editable fields in order and optionally click a named submit button. Exact accessible names; labels are excluded from field matches, and multiple editable matches fail. Default uses a supported value setter, otherwise native keys; verifies each field. Stops on first failure and reports completed steps; no rollback or retries. Final AX included.',
 replace_text:'Replace the entire contents of one named field, optionally press Enter. Default native keys: click, Ctrl+A, type; method=setValue or paste is explicit. This is not document-wide find/replace. Final AX included.',
 navigate:'Navigate a running browser via native background address-bar input, optionally opening a new tab. Uses http(s) URLs and an unambiguous known address-bar name, or an explicit address selector. Returns AX after submission; does not claim the page finished loading. Use wait_for for expected page content.',
 wait_for:'Observe until an exact named element (optionally exact value), AX text substring, or related dialog title appears. Choose exactly one condition. Bounded polling, final AX only; timeout is an error. Dialog result supplies its target for explicit binding. Does not focus windows.'
};
export const workflowTools=Object.keys(schemas).map(name=>({name,description:descriptions[name],inputSchema:{type:'object',properties:{app:{type:'string',minLength:1},...schemas[name]},required:['app',...required[name]],additionalProperties:false}}));
export const workflowMethods={fill_form:'fillForm',replace_text:'replaceText',navigate:'navigate',wait_for:'waitFor'};
function check(schema,value,path){
 if(schema.enum&&!schema.enum.includes(value))throw Error(`${path}: invalid option`);
 if(schema.type==='object'){
  if(!value||typeof value!=='object'||Array.isArray(value))throw Error(`${path} must be an object`);
  for(const key of Object.keys(value))if(!Object.hasOwn(schema.properties,key))throw Error(`${path}: unknown option ${key}`);
  for(const key of schema.required??[])if(value[key]===undefined)throw Error(`${path}.${key} is required`);
  for(const [key,v] of Object.entries(value))check(schema.properties[key],v,`${path}.${key}`);
 }else if(schema.type==='array'){
  if(!Array.isArray(value)||value.length<schema.minItems||value.length>schema.maxItems)throw Error(`${path}: invalid array length`);
  value.forEach((v,i)=>check(schema.items,v,`${path}[${i}]`));
 }else if(schema.type==='string'){
  if(typeof value!=='string'||value.length<(schema.minLength??0))throw Error(`${path} must be a${schema.minLength?' nonempty':''} string`);
 }else if(schema.type==='boolean'&&typeof value!=='boolean')throw Error(`${path} must be boolean`);
 else if(schema.type==='integer'&&(!Number.isInteger(value)||value<schema.minimum||value>schema.maximum))throw Error(`${path}: out of range`);
}
export function validateWorkflow(name,args){
 const tool=workflowTools.find(t=>t.name===name);if(!tool)throw Error('Unknown workflow');check(tool.inputSchema,args,name);
 if(name==='wait_for'&&(['target','text','dialog_title'].filter(k=>args[k]!==undefined).length!==1||args.value!==undefined&&!args.target))throw Error('wait_for requires exactly one condition; value requires target');
 if(name==='navigate'){let url;try{url=new URL(args.url);}catch{throw Error('Invalid URL');}if(!['http:','https:'].includes(url.protocol))throw Error('navigate requires http(s)');if(/[^\x20-\x7e]/.test(args.url)||args.url.length>4095)throw Error('Use an ASCII-encoded URL of at most 4095 characters');}
 const texts=name==='fill_form'?args.fields.map(f=>[f.value,f.method??'setValue']):name==='replace_text'?[[args.text,args.method??'keys']]:[];
 for(const [text,method] of texts)if(method==='keys'&&(/[^\x20-\x7e\n\r\t]/.test(text)||text.length>4096))throw Error('keys accepts at most 4096 supported characters; choose paste for Unicode');
}
function select(state,target,purpose){
 const found=(state.elements??[]).filter(e=>e.name===target.name&&(!target.role||[e.controlType,e.localizedControlType].includes(target.role))&&(purpose!=='field'||e.editable===true||e.supportsValue===true||['entry','password text','spin button'].includes(e.controlType)));
 if(found.length!==1)throw Error(`Expected one element named ${JSON.stringify(target.name)}, found ${found.length}; inspect AX and supply a role if needed`);
 return found[0];
}
export function createWorkflows(app,read,emit,showState){
 async function run(name,args){
  validateWorkflow(name,{app:'bound',...args});
  const steps=[];let state;
  async function step(label,fn){const start=performance.now();try{const v=await fn();steps.push({step:label,status:'completed',ms:performance.now()-start});return v;}catch(e){steps.push({step:label,status:'failed',ms:performance.now()-start,error:e.message});throw e;}}
  async function refresh(){state=await read();return state;}
  async function replace(target,text,method,current){
   const e=select(current??await refresh(),target,'field');
   method ??= e.supportsValue===true||(e.editable===true&&e.supportsEditableText===true)?'setValue':'keys';
   if(method==='keys'&&(/[^\x20-\x7e\n\r\t]/.test(text)||text.length>4096))throw Error('Choose method=paste for unsupported or long text');
   if(method==='setValue'&&e.supportsValue!==true&&e.supportsEditableText!==true)throw Error('Field has no setter interface; choose method=keys');
   if(method==='setValue')await step(`set ${target.name}`,()=>app.setValue(e.index,text));
   else{
    await step(`click ${target.name}`,()=>app.click(e.index));
    await step('select all',()=>app.pressKey('Ctrl+a'));
    if(text)await step(`replace ${target.name}`,()=>method==='paste'?app.paste(text):app.typeText(text));
    else await step('clear selection',()=>app.pressKey('BackSpace'));
   }
  }
  try{
   let result={status:'completed'};
   if(name==='fill_form'){
    // Validate selectors before the first mutation, then resolve afresh per field.
    await refresh();for(const f of args.fields)select(state,f,'field');if(args.submit)select(state,args.submit);
    for(const f of args.fields){
     await replace(f,f.value,f.method,state);
     await step(`verify ${f.name}`,async()=>{const actual=select(await refresh(),f,'field');if(String(actual.value??'')!==f.value)throw Error('Field value does not match requested value');});
    }
    if(args.submit){const e=select(state,args.submit);await step('submit form',()=>app.click(e.index));}
   }else if(name==='replace_text'){
    await replace(args.target,args.text,args.method??'keys');
    if(args.submit)await step('submit',()=>app.pressKey('Return'));
   }else if(name==='navigate'){
    await refresh();
    let target=args.address;
    if(!target){const known=['Address and search bar','Search or enter address','Search with Google or enter address'];const found=(state.elements??[]).filter(e=>known.includes(e.name));if(found.length!==1)throw Error('Address bar is ambiguous or unknown; provide address selector');target={name:found[0].name};}
    const e=select(state,target);
    if(args.new_tab){await step('activate address bar',()=>app.click(e.index));await step('new tab',()=>app.pressKey('Ctrl+t'));}
    await replace(target,args.url,'keys',args.new_tab?undefined:state);await step('navigate',()=>app.pressKey('Return'));
    result.status='submitted';
   }else{
    const begin=performance.now(),timeout=args.timeout_ms??10000;let polls=0;
    while(true){
     await refresh();polls++;
     let match;
     if(args.dialog_title)match=state.attention?.title===args.dialog_title?{target:state.attention.target}:null;
     else if(args.text)match=state.treeLines?.some(l=>l.includes(args.text))?{}:null;
     else{const found=(state.elements??[]).filter(e=>e.name===args.target.name&&(!args.target.role||[e.controlType,e.localizedControlType].includes(args.target.role))&&(args.value===undefined||String(e.value??'')===args.value));if(found.length===1)match={index:found[0].index};else if(found.length>1)throw Error('wait_for target is ambiguous');}
     if(match){result={status:'matched',...match,polls,elapsed_ms:performance.now()-begin};break;}
     if(performance.now()-begin>=timeout)throw Error(`wait_for timed out after ${polls} observations`);
     await new Promise(resolve=>setTimeout(resolve,Math.min(300,timeout-(performance.now()-begin))));
    }
   }
   if((name==='wait_for'||name==='fill_form'&&!args.submit)&&showState)showState(state);else await app.getAXState();return {...result,steps};
  }catch(e){emit({type:'text',text:JSON.stringify({status:'failed',steps,message:e.message,notice:'Completed steps remain applied; inspect state before retrying.'})});throw e;}
 }
 return Object.fromEntries(Object.entries(workflowMethods).map(([name,method])=>[method,args=>run(name,args)]));
}
