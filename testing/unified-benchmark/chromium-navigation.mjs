// Read-only controller inspection; never exposed to the benchmark agent.
const port=Number(process.argv[2]);
const tabs=(await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).filter(x=>x.type==='page');
const out=[];
for(const tab of tabs){
 const ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise((ok,no)=>{ws.onopen=ok;ws.onerror=no;});
 let id=0;const pending=new Map();ws.onmessage=e=>{const r=JSON.parse(e.data);if(pending.has(r.id)){pending.get(r.id)(r);pending.delete(r.id);}};
 const call=method=>new Promise(resolve=>{const n=++id;pending.set(n,resolve);ws.send(JSON.stringify({id:n,method}));});
 const history=await call('Page.getNavigationHistory');ws.close();out.push({id:tab.id,url:tab.url,title:tab.title,history});
}
console.log(JSON.stringify(out));
