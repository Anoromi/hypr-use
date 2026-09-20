import {createWorkflows,validateWorkflow,workflowMethods} from './workflows.mjs';
export function createFacade(call, output, options={}) {
  const aliases=options.aliases??{};
  const diffs=new Map();
  const bound=new Set();
  const string=(v,name)=>{if(typeof v!=='string')throw Error(`${name} must be a string`);return v;};
  const targetArgs=v=>{
    if(Number.isInteger(v)&&v>=0)return {element_index:String(v)};
    if(Array.isArray(v)&&v.length===2&&v.every(Number.isFinite))return {x:v[0],y:v[1]};
    throw Error('target must be an integer element index or [x,y]');
  };
  function ax(result,key,opt={}) {
    const state=result.structuredContent;
    const text=Array.isArray(state?.treeLines)?[
      `App: ${state.app?.name??''}; Window: ${state.windowTitle??''}; Target: ${state.target??key}`,
      ...(state.attention?[`Attention: ${JSON.stringify(state.attention)}`]:[]),
      ...(state.lastAction?.windowDelta?[`Window changes: ${JSON.stringify(state.lastAction.windowDelta)}`]:[]),
      ...(opt.compactGeometry===false?state.treeLines:[
        'Frame arrays are [x,y,width,height] in the same screenshot coordinate space.',
        ...state.treeLines.map(line=>line.replace(/ Frame: \{x: (-?\d+), y: (-?\d+), width: (-?\d+), height: (-?\d+)\}$/, ' Frame: [$1,$2,$3,$4]'))
      ]),
      ...(state.accessibility?.status!=='ok'?[`Accessibility: ${state.accessibility?.status??'unavailable'}. ${state.accessibility?.error??''}`]:[]),
      ...(state.accessibility?.treeTruncated?[`Tree truncated: ${state.accessibility.treeTruncatedReason??'limit'}`]:[])
    ].join('\n'):result.content.filter(x=>x.type==='text').map(x=>x.text).join('\n');
    const lines=text.split('\n'),before=diffs.get(key);diffs.set(key,lines);
    let value=text;
    if(before&&!opt.disableDiffing){
      const old=new Set(before),now=new Set(lines);
      const add=lines.filter(x=>!old.has(x)),remove=before.filter(x=>!now.has(x));
      if(add.length||remove.length){
        const delta=JSON.stringify({removed:remove,added:add});
        value=delta.length<text.length?delta:text;
      }else value='Accessibility state unchanged.';
    }
    if(opt.emit!==false)output({type:'text',text:value});return value;
  }
  function image(result,opt={}) {
    const block=result.content.filter(x=>x.type==='image').at(-1);
    if(!block)throw Error('Screenshot unavailable');
    if(opt.emit!==false)output(block);
    return Uint8Array.from(Buffer.from(block.data,'base64'));
  }
  async function apps(opt={}) {
    const r=await call('list_apps',{});
    const windows=r.structuredContent?.windows??[];
    const rows=windows.map(w=>({id:w.target,displayName:w.class,isRunning:true,title:w.title}));
    if(opt.emit!==false)output({type:'text',text:JSON.stringify(rows)});return rows;
  }
  async function bindApp(input,workflow=false,expectedTitle) {
    let name=aliases[string(input,'app')]??input;
    const r=await call('get_ax_state',{app:name});
    if(expectedTitle!==undefined&&r.structuredContent?.windowTitle!==expectedTitle)throw Error('Related dialog changed before binding; inspect the root app again');
    name=r.structuredContent?.target??name;bound.add(name);
    if(!workflow)ax(r,name,{disableDiffing:true});
    let recent=workflow?{result:r,time:Date.now()}:null;
    const act=async(tool,args)=>{
      recent=null;const r=await call(tool,{app:name,...args});
      const state=r.structuredContent;
      if(state?.lastAction?.targetClosed)output({type:'text',text:`Target closed after action. Inspect cua.listApps() and bind the intended window again. ${JSON.stringify(state.lastAction)}`});
      if(!state?.observationDeferred&&state?.target===name&&Array.isArray(state.elements))recent={result:r,time:Date.now()};
    };
    const observe=async()=>{const saved=recent;recent=null;return saved&&Date.now()-saved.time<=100?saved.result:await call('get_ax_state',{app:name});};
    const app={
      getDialog:async(opt={})=>{
        if(!opt||typeof opt!=='object'||Array.isArray(opt)||Object.keys(opt).some(k=>!['title','timeout_ms'].includes(k))||typeof opt.title!=='string'||!opt.title)throw Error('getDialog requires an exact nonempty title');
        const timeout=opt.timeout_ms??10000;
        if(!Number.isInteger(timeout)||timeout<1||timeout>30000)throw Error('getDialog timeout_ms must be 1–30000');
        const start=Date.now();
        while(true){
          const state=(await observe()).structuredContent,attention=state?.attention;
          if(attention?.type==='active-related-popup'&&attention.title===opt.title&&typeof attention.target==='string'&&attention.target&&attention.target!==name)return bindApp(attention.target,false,opt.title);
          if(Date.now()-start>=timeout)throw Error(`getDialog timed out waiting for ${JSON.stringify(opt.title)}`);
          await new Promise(resolve=>setTimeout(resolve,Math.min(300,timeout-(Date.now()-start))));
        }
      },
      getAXState:async(opt={})=>ax(await observe(),name,opt),
      getScreenshot:async(opt={})=>{recent=null;diffs.delete(name);return image(await call('get_screenshot',{app:name}),opt);},
      getAXStateAndScreenshot:async(opt={})=>{recent=null;const r=await call('get_app_state',{app:name});const state=ax(r,name,opt);const has=r.content.some(x=>x.type==='image');return {state,...(has?{screenshot:image(r,opt)}:{})};},
      click:async(target,opt={})=>{
        const args=targetArgs(target);const button={l:'left',r:'right',m:'middle'}[opt.mouseButton]??opt.mouseButton??'left';
        if(!['left','right','middle'].includes(button))throw Error('Invalid mouseButton');
        const count=opt.clickCount??1;if(!Number.isInteger(count)||count<1||count>3)throw Error('clickCount must be 1–3');
        await act('click',{...args,mouse_button:button,click_count:count,...(args.element_index&&button==='left'&&count===1?{element_click_mode:'pointer'}:{})});
      },
      drag:async(from,to)=>{const a=targetArgs(from),z=targetArgs(to);if(a.x===undefined||z.x===undefined)throw Error('drag needs two points');await act('drag',{from_x:a.x,from_y:a.y,to_x:z.x,to_y:z.y});},
      scroll:async(target,direction,pages=1)=>{direction={u:'up',d:'down',l:'left',r:'right'}[direction]??direction;if(!['up','down','left','right'].includes(direction)||!Number.isFinite(pages)||pages<=0)throw Error('Invalid scroll direction/pages');await act('scroll',{...targetArgs(target),direction,pages});},
      pressKey:async(key)=>{
        const sequence=string(key,'key').trim().split(/\s+/);
        if(!sequence[0])throw Error('key must not be empty');
        const arrowKeys={arrowup:'up',arrowdown:'down',arrowleft:'left',arrowright:'right'};
        key=sequence.map(combination=>combination.split('+').map(t=>['super','cmd','command'].includes(t.toLowerCase())?(options.commandModifier??'ctrl'):(arrowKeys[t.toLowerCase()]??t)).join('+')).join(' ');
        await act('press_key',{key});
      },
      typeText:async(text,opt={})=>{
        string(text,'text');
        if(!opt||typeof opt!=='object'||Array.isArray(opt)||Object.keys(opt).some(k=>!['replaceAll','submit'].includes(k))||Object.values(opt).some(v=>typeof v!=='boolean'))throw Error('typeText options must be replaceAll/submit booleans');
        const keys=text.length+(opt.replaceAll?1:0)+(opt.replaceAll&&!text?1:0)+(opt.submit?1:0);
        if(keys>4096)throw Error('typeText supports at most 4096 keys including selection/submission; use paste for longer text');
        await act('type_text',{text,method:'keys',...(opt.replaceAll?{replace_all:true}:{}),...(opt.submit?{submit:true}:{})});
      },
      paste:async(text,opt={})=>{if(opt.format&&opt.format!=='text')throw Error('Rich paste is not implemented; use format=text');await act('paste_text',{text:string(text,'text'),prepare_grid:false});},
      setValue:async(index,value)=>{const t=targetArgs(index);if(!t.element_index)throw Error('setValue requires element index');await act('set_value',{...t,value:string(value,'value')});},
      selectText:async(index,text,opt={})=>{const t=targetArgs(index);if(!t.element_index)throw Error('selectText requires element index');if(opt.selectionType&&!['text','cursor_before','cursor_after'].includes(opt.selectionType))throw Error('Invalid selectionType');await act('select_text',{...t,text:string(text,'text'),prefix:opt.prefix??'',suffix:opt.suffix??'',selection:opt.selectionType??'text'});},
      performSecondaryAction:async(index,action)=>{const t=targetArgs(index);if(!t.element_index)throw Error('Secondary action requires element index');await act('perform_secondary_action',{...t,action:string(action,'action')});}
    };
    Object.assign(app,createWorkflows(app,async()=> (await observe()).structuredContent,output,state=>ax({structuredContent:state,content:[]},name,{disableDiffing:true})));
    return Object.freeze(app);
  }
  const cua={getApp:input=>bindApp(input),listApps:apps,getState:async(opt={})=>{const state={apps:await apps({emit:false}),browsers:[]};if(opt.emit!==false)output({type:'text',text:JSON.stringify(state)});return state;}};
  const hyprnav=options.hyprnav??null;
  cua.myWorkspace=()=>{const w=hyprnav?.myWorkspace()??null;output({type:'text',text:JSON.stringify(w)});return w;};
  cua.setLabel=async text=>{const r=await (hyprnav?hyprnav.setLabel(string(text,'label')):Promise.resolve({label:text}));output({type:'text',text:JSON.stringify(r)});return r;};
  cua.listWorkspaceApps=async(opt={})=>{const rows=hyprnav?(await hyprnav.workspaceWindows()).map(w=>({id:`address:${w.address}`,displayName:w.class,isRunning:true,title:w.title,workspace:w.workspace,mine:w.mine})):[];if(opt.emit!==false)output({type:'text',text:JSON.stringify(rows)});return rows;};
  cua.launch=async(argv,opt={})=>{if(!Array.isArray(argv)||!argv.length||argv.some(a=>typeof a!=='string'))throw Error('launch takes an argv array of strings');if(!hyprnav)throw Error('hyprnav is not available in this session');const w=await hyprnav.launch(argv,{timeoutMs:opt.timeoutMs??15000});output({type:'text',text:`Launched ${argv[0]} on workspace ${w.workspace.id} as address:${w.address} (${w.class}: ${w.title})`});return bindApp(`address:${w.address}`);};
  cua.initialize=cua.getState;
  return {cua,async executeWorkflow(name,args){validateWorkflow(name,args);const {app:target,...options}=args;const app=await bindApp(target,true);return app[workflowMethods[name]](options);},async cleanup(){for(const target of bound){await call('computer',{action:'session',session_action:'end',target}).catch(()=>{});}bound.clear();}};
}
