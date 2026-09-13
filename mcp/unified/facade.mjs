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
      ...state.treeLines,
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
  async function getApp(input) {
    let name=aliases[string(input,'app')]??input;
    const r=await call('get_ax_state',{app:name});
    name=r.structuredContent?.target??name;bound.add(name);
    ax(r,name,{disableDiffing:true});
    let recent=null;
    const act=async(tool,args)=>{
      recent=null;const r=await call(tool,{app:name,...args});
      const state=r.structuredContent;
      if(state?.lastAction?.targetClosed)output({type:'text',text:`Target closed after action. Inspect cua.listApps() and bind the intended window again. ${JSON.stringify(state.lastAction)}`});
      if(!state?.observationDeferred&&state?.target===name&&Array.isArray(state.elements))recent={result:r,time:Date.now()};
    };
    const observe=async()=>{const saved=recent;recent=null;return saved&&Date.now()-saved.time<=100?saved.result:await call('get_ax_state',{app:name});};
    const app={
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
        key=sequence.map(combination=>combination.split('+').map(t=>['super','cmd','command'].includes(t.toLowerCase())?(options.commandModifier??'ctrl'):t).join('+')).join(' ');
        await act('press_key',{key});
      },
      typeText:async(text)=>act('type_text',{text:string(text,'text'),method:'keys'}),
      paste:async(text,opt={})=>{if(opt.format&&opt.format!=='text')throw Error('Rich paste is not implemented; use format=text');await act('paste_text',{text:string(text,'text')});},
      setValue:async(index,value)=>{const t=targetArgs(index);if(!t.element_index)throw Error('setValue requires element index');await act('set_value',{...t,value:string(value,'value')});},
      selectText:async(index,text,opt={})=>{const t=targetArgs(index);if(!t.element_index)throw Error('selectText requires element index');if(opt.selectionType&&!['text','cursor_before','cursor_after'].includes(opt.selectionType))throw Error('Invalid selectionType');await act('select_text',{...t,text:string(text,'text'),prefix:opt.prefix??'',suffix:opt.suffix??'',selection:opt.selectionType??'text'});},
      performSecondaryAction:async(index,action)=>{const t=targetArgs(index);if(!t.element_index)throw Error('Secondary action requires element index');await act('perform_secondary_action',{...t,action:string(action,'action')});}
    };
    return Object.freeze(app);
  }
  const cua={getApp,listApps:apps,getState:async(opt={})=>{const state={apps:await apps({emit:false}),browsers:[]};if(opt.emit!==false)output({type:'text',text:JSON.stringify(state)});return state;}};
  cua.initialize=cua.getState;
  return {cua,async cleanup(){for(const target of bound){await call('computer',{action:'session',session_action:'end',target}).catch(()=>{});}bound.clear();}};
}
