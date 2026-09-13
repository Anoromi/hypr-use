// Common operations share the ordinary guarded facade; no raw input bypass.
const selector={type:'object',properties:{name:{type:'string',minLength:1},role:{type:'string'}},required:['name'],additionalProperties:false};
const field={type:'object',properties:{...selector.properties,value:{type:['string','boolean']},method:{enum:['setValue','keys','paste']}},required:['name','value'],additionalProperties:false};
const choice={type:'object',properties:{...selector.properties,option:{type:'string',minLength:1}},required:['name','option'],additionalProperties:false};
const schemas={
 select_options:{choices:{type:'array',minItems:1,maxItems:20,items:choice},submit:selector},
 fill_form:{fields:{type:'array',minItems:1,maxItems:20,items:field},submit:selector},
 replace_text:{target:selector,text:{type:'string'},method:{enum:['setValue','keys','paste']},submit:{type:'boolean'}},
 navigate:{url:{type:'string'},new_tab:{type:'boolean'},address:selector},
 wait_for:{target:selector,value:{type:['string','boolean']},text:{type:'string',minLength:1},dialog_title:{type:'string',minLength:1},timeout_ms:{type:'integer',minimum:1,maximum:30000}}
};
const required={select_options:['choices'],fill_form:['fields'],replace_text:['target','text'],navigate:['url'],wait_for:[]};
const descriptions={
 select_options:'Select options in named single-choice combo boxes, in order, and optionally click submit. choices contains {name,role?,option}, using exact accessible names. Opens a combo box when its options are not yet exposed in AX. Uses an exposed select action or GTK menu click action; verifies the selected option or combo-box value. Skips selected options, verifies each selection and the final set, stops on failure without retry or rollback. Final AX included.',
 fill_form:'Fill named text fields and checkboxes in order and optionally click a named submit button. Exact accessible names; labels are excluded from field matches, and multiple editable matches fail. String values use a supported setter or native keys; already matching visible text is skipped unless an explicit method requests re-entry. Boolean values set checkbox state, clicking only when it differs. Verifies changes; mixed checkbox states fail before input. Stops on first failure and reports completed steps; no rollback or retries. Final AX included.',
 replace_text:'Replace the entire contents of one named field, optionally press Enter. Default native keys: click, Ctrl+A, type; method=setValue or paste is explicit. This is not document-wide find/replace. Final AX included.',
 navigate:'Navigate a running browser via native background address-bar input, optionally opening a new tab. Uses http(s) URLs and an unambiguous known address-bar name, or an explicit address selector. Returns AX after submission; does not claim the page finished loading. Use wait_for for expected page content.',
 wait_for:'Observe until an exact named element (optionally exact text value or boolean checked state), AX text substring, or related dialog title appears. Choose exactly one condition. Bounded polling, final AX only; timeout is an error. Dialog result supplies its target for explicit binding. Does not focus windows.'
};
export const workflowTools=Object.keys(schemas).map(name=>({name,description:descriptions[name],inputSchema:{type:'object',properties:{app:{type:'string',minLength:1},...schemas[name]},required:['app',...required[name]],additionalProperties:false}}));
export const workflowMethods={select_options:'selectOptions',fill_form:'fillForm',replace_text:'replaceText',navigate:'navigate',wait_for:'waitFor'};
function check(schema,value,path){
 if(Array.isArray(schema.type)){if(!schema.type.includes(typeof value))throw Error(`${path} must be a string or boolean`);return;}
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
 if(name==='fill_form'&&args.fields.some(f=>typeof f.value==='boolean'&&f.method!==undefined))throw Error('Checkbox values do not take a text method');
 const texts=name==='fill_form'?args.fields.filter(f=>typeof f.value==='string').map(f=>[f.value,f.method??'setValue']):name==='replace_text'?[[args.text,args.method??'keys']]:[];
 for(const [text,method] of texts)if(method==='keys'&&(/[^\x20-\x7e\n\r\t]/.test(text)||text.length>4096))throw Error('keys accepts at most 4096 supported characters; choose paste for Unicode');
}
function select(state,target,purpose){
 const found=(state.elements??[]).filter(e=>e.name===target.name&&(!target.role||[e.controlType,e.localizedControlType].includes(target.role))&&(purpose!=='field'||e.editable===true||e.supportsValue===true||['entry','password text','spin button'].includes(e.controlType))&&(purpose!=='choice'||e.controlType==='combo box')&&(purpose!=='checkbox'||['check box','check menu item','toggle button'].includes(e.controlType)));
 if(found.length!==1)throw Error(`Expected one element named ${JSON.stringify(target.name)}, found ${found.length}; inspect AX and supply a role if needed`);
 return found[0];
}
function choiceOption(state,choice,allowUnexposed=false){
 const control=select(state,choice,'choice'),path=control.runtimeId;
 if(control.value===choice.option)return {control,option:null,selected:true};
 if(!Array.isArray(path)||!path.length)throw Error('Combo box has no AX ancestry; inspect its options');
 const options=(state.elements??[]).filter(e=>Array.isArray(e.runtimeId)&&e.runtimeId.length>path.length&&path.every((v,i)=>e.runtimeId[i]===v)&&['menu item','list item','radio button'].includes(e.controlType));
 const matches=options.filter(e=>e.name===choice.option);
 if(!options.length&&allowUnexposed)return {control,option:null,selected:false,unexposed:true};
 if(matches.length!==1)throw Error(`Expected one exposed option ${JSON.stringify(choice.option)} under ${JSON.stringify(choice.name)}, found ${matches.length}; open the control and inspect AX if necessary`);
 const option=matches[0],selected=(option.states??[]).includes('selected');
 const action=(option.actions??[]).includes('select')?'select':String(option.className??'').toLowerCase()==='gtk'&&(option.actions??[]).includes('click')?'click':null;
 if(!selected&&!action)throw Error('Option has no supported selection action; inspect available actions');
 return {control,option,selected,action};
}
export function createWorkflows(app,read,emit,showState){
 async function run(name,args){
  validateWorkflow(name,{app:'bound',...args});
  const steps=[];let state;
  async function step(label,fn){const start=performance.now();try{const v=await fn();steps.push({step:label,status:'completed',ms:performance.now()-start});return v;}catch(e){steps.push({step:label,status:'failed',ms:performance.now()-start,error:e.message});throw e;}}
  async function refresh(){state=await read();return state;}
  async function replace(target,text,method,current,submit=false){
   const e=select(current??await refresh(),target,'field');
   method ??= e.supportsValue===true||(e.editable===true&&e.supportsEditableText===true)?'setValue':'keys';
   if(method==='keys'&&(/[^\x20-\x7e\n\r\t]/.test(text)||text.length>4096))throw Error('Choose method=paste for unsupported or long text');
   if(method==='setValue'&&e.supportsValue!==true&&e.supportsEditableText!==true)throw Error('Field has no setter interface; choose method=keys');
   if(method==='setValue')await step(`set ${target.name}`,()=>app.setValue(e.index,text));
   else{
    await step(`click ${target.name}`,()=>app.click(e.index));
    if(method==='keys'&&text.length+1+(submit?1:0)<=4096){
     await step(`replace ${target.name}${submit?' and submit':''}`,()=>app.typeText(text,{replaceAll:true,submit}));
     return;
    }
    await step('select all',()=>app.pressKey('Ctrl+a'));
    if(text)await step(`replace ${target.name}`,()=>method==='paste'?app.paste(text):app.typeText(text));
    else await step('clear selection',()=>app.pressKey('BackSpace'));
   }
   if(submit)await step('submit',()=>app.pressKey('Return'));
  }
  try{
   let result={status:'completed'};
   if(name==='select_options'){
    await refresh();const controls=new Set();
    for(const c of args.choices){const {control}=choiceOption(state,c,true);if(controls.has(control.index))throw Error('Each combo box must appear only once');controls.add(control.index);}
    if(args.submit)select(state,args.submit);
    for(const c of args.choices){
     let found=choiceOption(state,c,true);
     if(found.unexposed){
      await step(`open ${c.name}`,()=>app.click(found.control.index));
      await step(`inspect ${c.name} options`,refresh);found=choiceOption(state,c);
     }
     const {option,selected,action}=found;
     if(selected){steps.push({step:`keep ${c.name}`,status:'unchanged',ms:0});continue;}
     await step(`select ${c.option} in ${c.name}`,()=>app.performSecondaryAction(option.index,action));
     await step(`verify ${c.name}`,async()=>{if(!choiceOption(await refresh(),c,true).selected)throw Error('Option selection does not match the request');});
    }
    await step('verify final choices',async()=>{for(const c of args.choices)if(!choiceOption(state,c,true).selected)throw Error(`Selection in ${JSON.stringify(c.name)} changed after a later input`);});
    if(args.submit){const e=select(state,args.submit);await step('submit choices',()=>app.click(e.index));}
   }else if(name==='fill_form'){
    // Validate selectors before the first mutation, then resolve afresh per field.
    await refresh();for(const f of args.fields){const e=select(state,f,typeof f.value==='boolean'?'checkbox':'field');if(typeof f.value==='boolean'&&typeof e.checked!=='boolean')throw Error('Checkbox state is mixed or unavailable; inspect it before changing it');}if(args.submit)select(state,args.submit);
    for(const f of args.fields){
     const checkbox=typeof f.value==='boolean';
     if(checkbox){
      const e=select(state,f,'checkbox');
      if(typeof e.checked!=='boolean')throw Error('Checkbox state is mixed or unavailable');
      if(e.checked===f.value){steps.push({step:`keep ${f.name}`,status:'unchanged',ms:0});continue;}
      await step(`set ${f.name} to ${f.value}`,()=>app.click(e.index));
     }else{
      const e=select(state,f,'field');
      if(f.method===undefined&&typeof e.value==='string'&&e.value===f.value&&e.controlType!=='password text'){steps.push({step:`keep ${f.name}`,status:'unchanged',ms:0});continue;}
      await replace(f,f.value,f.method,state);
     }
     await step(`verify ${f.name}`,async()=>{const actual=select(await refresh(),f,checkbox?'checkbox':'field');if((checkbox?actual.checked:String(actual.value??''))!==f.value)throw Error('Field value does not match requested value');});
    }
    await step('verify final form',async()=>{
     for(const f of args.fields){
      const checkbox=typeof f.value==='boolean';const e=select(state,f,checkbox?'checkbox':'field');
      if((checkbox?e.checked:String(e.value??''))!==f.value){
       if(showState)showState(state);
       throw Error(`Field ${JSON.stringify(f.name)} changed after a later input; inspect the form before submitting`);
      }
     }
    });
    if(args.submit){const e=select(state,args.submit);await step('submit form',()=>app.click(e.index));}
   }else if(name==='replace_text'){
    await replace(args.target,args.text,args.method??'keys',undefined,args.submit??false);
   }else if(name==='navigate'){
    await refresh();
    let target=args.address;
    if(!target){const known=['Address and search bar','Search or enter address','Search with Google or enter address'];const found=(state.elements??[]).filter(e=>known.includes(e.name));if(found.length!==1)throw Error('Address bar is ambiguous or unknown; provide address selector');target={name:found[0].name};}
    const e=select(state,target);
    if(args.new_tab){await step('activate address bar',()=>app.click(e.index));await step('new tab',()=>app.pressKey('Ctrl+t'));}
    await replace(target,args.url,'keys',args.new_tab?undefined:state,true);
    result.status='submitted';
   }else{
    const begin=performance.now(),timeout=args.timeout_ms??10000;let polls=0;
    while(true){
     await refresh();polls++;
     let match;
     if(args.dialog_title)match=state.attention?.title===args.dialog_title?{target:state.attention.target}:null;
     else if(args.text)match=state.treeLines?.some(l=>l.includes(args.text))?{}:null;
     else{const found=(state.elements??[]).filter(e=>e.name===args.target.name&&(!args.target.role||[e.controlType,e.localizedControlType].includes(args.target.role))&&(args.value===undefined||(typeof args.value==='boolean'?e.checked===args.value:String(e.value??'')===args.value)));if(found.length===1)match={index:found[0].index};else if(found.length>1)throw Error('wait_for target is ambiguous');}
     if(match){result={status:'matched',...match,polls,elapsed_ms:performance.now()-begin};break;}
     if(performance.now()-begin>=timeout)throw Error(`wait_for timed out after ${polls} observations`);
     await new Promise(resolve=>setTimeout(resolve,Math.min(300,timeout-(performance.now()-begin))));
    }
   }
   if((name==='wait_for'||['fill_form','select_options'].includes(name)&&!args.submit)&&showState)showState(state);else await app.getAXState();return {...result,steps};
  }catch(e){emit({type:'text',text:JSON.stringify({status:'failed',steps,message:e.message,notice:'Completed steps remain applied; inspect state before retrying.'})});throw e;}
 }
 return Object.fromEntries(Object.entries(workflowMethods).map(([name,method])=>[method,args=>run(name,args)]));
}
