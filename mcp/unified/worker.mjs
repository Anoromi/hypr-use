import {validateWorkflow,workflowMethods} from './workflows.mjs';
import vm from 'node:vm';
import {spawn} from 'node:child_process';
import readline from 'node:readline';
import {parse} from 'acorn';
import {fileURLToPath} from 'node:url';
import {createFacade} from './facade.mjs';
const backend=spawn(process.env.HYPR_USE_PYTHON??'python3',[fileURLToPath(new URL('./backend-launch.py',import.meta.url))],{stdio:['pipe','pipe','inherit']});
let next=0,content=[],timings=[];const pending=new Map();const inFlight=new Set();
readline.createInterface({input:backend.stdout}).on('line',line=>{try{const r=JSON.parse(line),p=pending.get(r.id);if(!p)return;pending.delete(r.id);r.error?p.reject(Error(r.error.message)):p.resolve(r.result);}catch(e){for(const p of pending.values())p.reject(e);pending.clear();}});
backend.on('exit',()=>{for(const p of pending.values())p.reject(Error('Portal process exited'));pending.clear();});
async function dispatch(name,args){const start=performance.now();try{
 const r=await new Promise((resolve,reject)=>{const id=++next;pending.set(id,{resolve,reject});backend.stdin.write(JSON.stringify({jsonrpc:'2.0',id,method:'tools/call',params:{name,arguments:args}})+'\n');});
 const timing={name,duration_ms:performance.now()-start,backend:r._meta?.['hypr-use/timing']};timings.push(timing);process.send({event:'operation',timing});
 if(r.isError)throw Error(r.content.filter(x=>x.type==='text').map(x=>x.text).join('\n'));
 return r;
}catch(e){throw Error(`${name}: ${e.message}`);}}
function call(name,args){const p=dispatch(name,args);inFlight.add(p);p.then(()=>inFlight.delete(p),()=>inFlight.delete(p));return p;}
const output=block=>{content.push(block);process.send({event:'output',block});};
const {cua,cleanup}=createFacade(call,output,{aliases:JSON.parse(process.env.HYPR_USE_APP_ALIASES??'{}'),commandModifier:process.env.HYPR_USE_COMMAND_MODIFIER??'ctrl'});
const context=vm.createContext({cua,nodeRepl:Object.freeze({write:v=>output({type:'text',text:typeof v==='string'?v:JSON.stringify(v)}),emitImage:async v=>{if(v instanceof Uint8Array||ArrayBuffer.isView(v))output({type:'image',mimeType:'image/png',data:Buffer.from(v).toString('base64')});else if(v?.bytes)output({type:'image',mimeType:v.mimeType??'image/png',data:Buffer.from(v.bytes).toString('base64')});else throw Error('emitImage expects image bytes');}})}, {codeGeneration:{strings:false,wasm:false}});
function names(pattern){if(pattern.type==='Identifier')return [pattern.name];if(pattern.type==='ObjectPattern')return pattern.properties.flatMap(p=>names(p.value??p.argument));if(pattern.type==='ArrayPattern')return pattern.elements.filter(Boolean).flatMap(names);if(pattern.type==='RestElement')return names(pattern.argument);if(pattern.type==='AssignmentPattern')return names(pattern.left);return [];}
function rewrite(code){const ast=parse(code,{ecmaVersion:'latest',allowAwaitOutsideFunction:true});let out='',last=0;for(const n of ast.body){let replacement;
 if(n.type==='VariableDeclaration')replacement=n.declarations.map(d=>{for(const name of names(d.id))if(!(name in context))context[name]=undefined;return d.init?`(${code.slice(d.id.start,d.id.end)} = ${code.slice(d.init.start,d.init.end)});`:'';}).join('\n');
 else if(n.type==='FunctionDeclaration'||n.type==='ClassDeclaration')replacement=`globalThis.${n.id.name} = (${code.slice(n.start,n.end)});`;
 else if(n.type==='ImportDeclaration'||n.type.startsWith('Export'))throw Error('Imports and exports are unavailable in this desktop runtime');
 if(replacement!==undefined){out+=code.slice(last,n.start)+replacement;last=n.end;}}
 return out+code.slice(last);
}
process.on('message',async msg=>{content=[];timings=[];try{if(msg.kind==='cleanup'){await cleanup();process.send({ok:true,content:[],timings});return;}
 if(msg.kind==='workflow'){validateWorkflow(msg.name,msg.args);const {app:target,...args}=msg.args;const app=await cua.getApp(target);const value=await app[workflowMethods[msg.name]](args);output({type:'text',text:JSON.stringify(value)});process.send({ok:true,content,timings});return;}
 const transformed=rewrite(msg.code);await new vm.Script(`(async()=>{${transformed}\n})()`).runInContext(context,{timeout:Math.min(msg.timeout,1000)});
 while(inFlight.size)await Promise.all([...inFlight]);
 process.send({ok:true,content,timings});
}catch(e){while(inFlight.size)await Promise.allSettled([...inFlight]);process.send({ok:false,content:[...content,{type:'text',text:e.message}],timings});}});
