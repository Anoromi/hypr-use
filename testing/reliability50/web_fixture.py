import json,threading
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
PAGE='''<!doctype html><html><meta charset="utf-8"><title>Hypr-use local demo</title><style>body{font:18px sans-serif;max-width:850px;margin:30px auto}label{display:block;margin:12px 0}input,select,button{font:inherit;padding:6px}button{margin:5px}table{width:100%}td{padding:8px;border-bottom:1px solid #ddd}</style><body>
<h1>Local workflow demo</h1><p>This is a local test page. Nothing is purchased or sent externally.</p>
<label>Full name <input id="name"></label><label>Email <input id="email" type="email"></label>
<label>Country <select id="country"><option>Germany</option><option>Japan</option><option>United States</option></select></label>
<label><input type="checkbox" id="updates">Email updates</label><label><input type="checkbox" id="sms" checked>SMS updates</label>
<label><input type="radio" name="shipping" value="Standard" checked>Standard shipping</label><label><input type="radio" name="shipping" value="Express">Express shipping</label>
<label>Appointment <input id="date" type="date"></label><label>Note <input id="note"></label><label>Comparison total <input id="total"></label>
<button onclick="save()">Save profile</button><button onclick="document.querySelector('dialog').showModal()">Review</button><p id="status">Not saved</p>
<dialog><h2>Review changes</h2><button onclick="state.review='confirmed';sync();this.closest('dialog').close()">Confirm review</button><button onclick="this.closest('dialog').close()">Cancel</button></dialog>
<h2>Products</h2><label>Category <select id="category" onchange="render()"><option>All</option><option>Accessories</option><option>Storage</option></select></label><label>Sort by price <select id="sort" onchange="render()"><option value="default">Default</option><option value="ascending">Lowest first</option><option value="descending">Highest first</option></select></label><table><thead><tr><th>Product</th><th>Price</th><th>Action</th></tr></thead><tbody id="products"></tbody></table><p id="cart">Cart empty</p>
<script>
let state={cart:{}},items=[['Cedar Keyboard',50,'Accessories'],['Birch Mouse',25,'Accessories'],['Oak Drive',90,'Storage']];
function read(){for(let k of ['name','email','country','date','note','total','category','sort'])state[k]=document.getElementById(k).value;state.updates=document.getElementById('updates').checked;state.sms=document.getElementById('sms').checked;state.shipping=document.querySelector('input[name=shipping]:checked').value}
function sync(){read();fetch('/state',{method:'POST',body:JSON.stringify(state)})}
function save(){state.saved=true;document.getElementById('status').textContent='Profile saved';sync()}
function add(n){state.cart[n]=(state.cart[n]||0)+1;document.getElementById('cart').textContent='Cart: '+JSON.stringify(state.cart);sync()}
function render(){let c=document.getElementById('category').value,s=document.getElementById('sort').value,a=items.filter(i=>c==='All'||i[2]===c);if(s!=='default')a.sort((x,y)=>(x[1]-y[1])*(s==='ascending'?1:-1));document.getElementById('products').innerHTML=a.map(i=>`<tr><td>${i[0]}</td><td>$${i[1]}</td><td><button onclick="add('${i[0]}')">Add ${i[0]}</button></td></tr>`).join('');sync()}render();
</script></body></html>'''
class Fixture:
 def __init__(self):
  self.state={};self.state_history=[];self.visited=[];owner=self
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    if self.path=='/state':
     owner.state=json.loads(self.rfile.read(int(self.headers['Content-Length'])));owner.state_history.append(owner.state.copy())
    self.send_response(204);self.end_headers()
   def do_GET(self):
    owner.visited.append(self.path)
    if self.path=='/web':body=PAGE
    else:
     name={'/start':'Start','/second':'Second','/third':'Third','/article':'Long article'}.get(self.path,'Start')
     body=f'<!doctype html><html><meta charset="utf-8"><title>{name}</title><body><h1>{name}</h1><p><a href="/start">Start</a> | <a href="/second">Second</a> | <a href="/third">Third</a> | <a href="/article">Long article</a></p>'
     if self.path=='/article':body+=''.join(f'<section style="height:500px"><h2>Section {i}</h2><p>Local reference material for background scrolling.</p></section>' for i in range(1,7))+'<h2>Final section</h2><p>Final code: MAPLE-72</p>'
     body+='</body></html>'
    self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(body.encode())
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler);self.port=self.server.server_port
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
 def close(self):self.server.shutdown();self.server.server_close()
