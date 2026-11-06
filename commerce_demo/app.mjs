import {runtime} from './runtime.mjs';
import {createLocalDataLayer, previewManifestArmed, previewPurchaseAllowed} from './ga4.mjs';
const localLayer=createLocalDataLayer(runtime),layerPending=new Set();
async function flushLocal(){const s=await transaction();localLayer.consent(s.consent);if(s.consent)for(const e of s.events.filter(e=>layerPending.has(e.event_id)))localLayer.send(e);layerPending.clear();}
let google,googleAllowed=false,googleEpoch=0;const googlePending=new Set();
function stopGoogle(){googleEpoch++;googleAllowed=false;google?.consent(false);googlePending.clear();return google?.loaded||false;}
async function flushGoogle(){
 if(!liveManifest||!googleAllowed||manifestFailed)return;
 const epoch=googleEpoch,s=await transaction();
 if(epoch!==googleEpoch||!googleAllowed||manifestFailed)return;
 if(!s.consent){if(stopGoogle())location.reload();return;}
 for(const e of s.events.filter(e=>googlePending.has(e.event_id))){
  google.send(e);googlePending.delete(e.event_id);
 }
}
let transport,cloudAllowed=false,grantEpoch=0;const pending=new Set();
async function flushCloud(){if(!cloudAllowed||!transport)return;const s=await transaction();if(!s.consent){cloudAllowed=false;transport.consent(false);pending.clear();return;}for(const e of s.events.filter(e=>pending.has(e.event_id))){const result=await transport.send(e);if(result==='transport_accepted'||result==='retry_limit')pending.delete(e.event_id);}if(location.hash==='#inspect')await render();}
import {catalog} from './catalog.mjs';
import {validate,funnel} from './contract.mjs';
const channel=new BroadcastChannel('olist-commerce-offline');
const params=new URLSearchParams(location.search);
const testContext=params.get('test_run_id')?{test_run_id:params.get('test_run_id'),scenario_id:params.get('scenario_id')||'browser'}:null;
const liveManifest=previewManifestArmed(runtime,params,location.hostname);
const manifestArmed=liveManifest||(runtime.mode==='offline'&&params.get('source_manifest')==='1'&&
 /^ga4-rehearsal-[0-9]{25}$/.test(testContext?.test_run_id||'')&&
 /^[a-z0-9-]{1,40}$/.test(params.get('scenario_id')||''));
const manifestPrefix='source-manifest/';
const manifestScope=manifestArmed?manifestPrefix+testContext.test_run_id+'/'+testContext.scenario_id+'/':null;
const manifestRange=prefix=>IDBKeyRange.bound(prefix,prefix+'\uffff');
let manifestFailed=false;
const db=await new Promise((resolve,reject)=>{const r=indexedDB.open('olist-commerce-offline',1);r.onupgradeneeded=()=>r.result.createObjectStore('state');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
const fresh=()=>({consent:false,cart:[],checkout:null,orders:[],events:[],attempts:[],identity:null,sequence:0,lastActivity:0});
function transaction(update){
 return new Promise((resolve,reject)=>{
  const t=db.transaction('state',update?'readwrite':'readonly'),store=t.objectStore('state'),r=store.get('demo');
  let state,result,emitted=[],failure,journaling=false;
  r.onsuccess=()=>{
   try{
    state=r.result||fresh();
    if(!update)return;
    const count=state.events.length;
    result=update(state);
    emitted=state.events.slice(count);
    if(!state.consent)store.delete(manifestRange(manifestPrefix));
    if(manifestScope&&emitted.length){
     journaling=true;
     for(const event of emitted){
      store.add({manifest_version:1,capture_stage:'source_committed_before_dispatch',
       event,expected_transaction_id:event.order_id??null},manifestScope+event.event_id);
     }
    }
    store.put(state,'demo');
   }catch(e){failure=e;t.abort();}
  };
  t.oncomplete=()=>{
   // Only committed events may enter a delivery queue.
   for(const event of emitted){
    layerPending.add(event.event_id);
    if(googleAllowed)googlePending.add(event.event_id);
    if(cloudAllowed)pending.add(event.event_id);
   }
   if(update)channel.postMessage('changed');
   resolve(update?result:state);
  };
  t.onabort=()=>{
   if(journaling){
    manifestFailed=true;
    layerPending.clear();stopGoogle();pending.clear();
    reject(Error('Source manifest transaction failed; stop this run'));
   }else reject(failure||t.error||Error('Local transaction aborted'));
  };
 });
}

function readManifest(){
 return new Promise((resolve,reject)=>{
  const t=db.transaction('state','readonly'),store=t.objectStore('state');
  const state=store.get('demo'),rows=store.getAll(manifestRange(manifestScope));
  t.oncomplete=()=>{
   if(!state.result?.consent){reject(Error('Local recording consent is required'));return;}
   resolve(rows.result.sort((a,b)=>a.event.session_sequence-b.event.session_sequence||
    a.event.event_id.localeCompare(b.event.event_id)));
  };
  t.onabort=()=>reject(t.error||Error('Source manifest read aborted'));
 });
}
const item=id=>{const p=catalog.find(p=>p.source.product_id===id);if(!p)throw Error('Unknown product');return {product_id:id,category:p.source.product_category_name,demo_title:p.display.title,price_minor:p.display.price_minor,quantity:1};};
const money=n=>new Intl.NumberFormat('en',{style:'currency',currency:'BRL'}).format(n/100);
function emit(s,name,items,extra={}){
 if(manifestFailed)throw Error('Source manifest transaction failed; stop this run');
 if(!s.consent||(runtime.mode==='ga4_gtm'&&!googleAllowed))return;
 const now=Date.now();if(!s.identity||now-s.lastActivity>=1800000){s.identity={anonymous_id:s.identity?.anonymous_id||crypto.randomUUID(),session_id:crypto.randomUUID()};s.sequence=0;}s.lastActivity=now;
 const e={event_id:crypto.randomUUID(),event_name:name,occurred_at:new Date(now).toISOString(),...s.identity,session_sequence:++s.sequence,schema_version:'1.0.0',environment:'local_demo',activity_origin:testContext?'synthetic_test':'manual_demo',catalog_origin:'olist_historical',display_provenance:'manual_demo',simulation:true,consent_state:'granted',app_version:'1.0.0',catalog_version:'1.0.0',device_class:innerWidth<700?'mobile':'desktop',items,currency:'BRL',value_minor:items.reduce((n,i)=>n+i.price_minor,0),...(testContext||{}),...extra};validate(e,catalog);s.events.push(e);
}
let pageState;
const main=document.querySelector('#main');
async function render(){
 pageState=await transaction();const s=pageState;
 document.querySelector('#google-grant').hidden=!liveManifest;document.querySelector('#google-grant').disabled=googleAllowed||googleGranting||manifestFailed;document.querySelector('#google-status').textContent=googleAllowed?'GA4 Preview enabled in this tab; vendor receipt unverified.':'Google tracking disabled.';
 document.querySelector('#cloud-status').textContent=cloudAllowed?'Cloud sending enabled in this tab; receipt unverified.':'External sending disabled until explicit cloud consent.';
 document.querySelector('.notice').textContent=runtime.mode==='ga4_gtm'?'Google Preview configured. Only a separate explicit Google grant can load tracking. Synthetic demo events only.':runtime.mode==='posthog'?'Cloud mode configured. Only explicit cloud consent sends new events to PostHog. Historical IDs; fictional display content and purchases.':'Offline demonstration. Historical Olist IDs; fictional display content and purchases. No external telemetry.';
 document.querySelector('#cloud-grant').hidden=runtime.mode!=='posthog';document.querySelector('#cloud-grant').disabled=cloudAllowed;
 document.querySelector('#consent-status').textContent=s.consent?'Local recording allowed. External sending requires a separate tab grant.':'Local recording stopped. External telemetry disabled.';
 document.querySelector('#grant').disabled=s.consent;
 const route=location.hash.slice(1)||'catalog';
 if(route.startsWith('product/')){
  const p=catalog.find(p=>p.source.product_id===route.split('/')[1]);if(!p)throw Error('Unknown product');
  main.innerHTML=`<article class="detail"><a href="#catalog">Back to catalog</a><h1>${p.display.title}</h1><div class="placeholder" aria-label="Generic placeholder, not a source photo">◇</div><p>${p.display.description}</p><p>Fictional price: ${money(p.display.price_minor)}</p><p class="muted">Original Olist category: ${p.source.product_category_name}<br>Original product ID: <code>${p.source.product_id}</code></p><button class="primary" id="add" ${s.cart.includes(p.source.product_id)?'disabled':''}>Add to cart</button></article>`;
  document.querySelector('#add').onclick=()=>action(x=>{if(!x.cart.includes(p.source.product_id)){x.cart.push(p.source.product_id);x.checkout=null;emit(x,'product_added_to_cart',[item(p.source.product_id)]);}});
 }else if(route==='cart'){
  main.innerHTML=`<h1>Your demonstration cart</h1>${s.cart.length?s.cart.map(id=>{const i=item(id);return `<div class="row"><span>${i.demo_title} — ${money(i.price_minor)}</span><button data-remove="${id}">Remove item</button></div>`;}).join(''):'<p>Your cart is empty.</p>'}<p>Fictional total: ${money(s.cart.reduce((n,id)=>n+item(id).price_minor,0))}</p><button class="primary" id="checkout" ${s.cart.length?'':'disabled'}>Start checkout</button>`;
  main.querySelectorAll('[data-remove]').forEach(b=>b.onclick=()=>action(x=>{const id=b.dataset.remove;if(x.cart.includes(id)){x.cart=x.cart.filter(v=>v!==id);x.checkout=null;emit(x,'product_removed_from_cart',[item(id)]);}}));
  document.querySelector('#checkout').onclick=()=>action(x=>{if(!x.cart.length)throw Error('Empty cart');if(!x.checkout){x.checkout={id:crypto.randomUUID(),items:x.cart.map(item)};emit(x,'checkout_started',x.checkout.items,{checkout_id:x.checkout.id});}return x.checkout.id;},id=>location.hash=`checkout/${id}`);
 }else if(route.startsWith('checkout/')){
  const id=route.split('/')[1],order=s.orders.find(o=>o.checkout_id===id),c=s.checkout?.id===id?s.checkout:null;
  main.innerHTML=order?`<h1>Simulated purchase complete</h1><p>No payment was taken.</p><p>Order: <code>${order.order_id}</code></p><p>Fictional total: ${money(order.value_minor)}</p><a href="#catalog">Continue browsing</a>`:c?`<h1>Review simulated purchase</h1>${c.items.map(i=>`<p>${i.demo_title} — ${money(i.price_minor)}</p>`).join('')}<p>Fictional total: ${money(c.items.reduce((n,i)=>n+i.price_minor,0))}</p><p>No payment, address or account required.</p><button id="complete" class="primary">Complete simulated purchase</button>`:'<h1>Checkout unavailable</h1><p>Your cart changed or this checkout was reset.</p><a href="#cart">Return to cart</a>';
  const b=document.querySelector('#complete');
  if(b)b.disabled=!previewPurchaseAllowed(runtime,liveManifest&&googleAllowed&&!manifestFailed,testContext,s.orders);
  if(b)b.onclick=()=>action(x=>{
   if(!previewPurchaseAllowed(runtime,liveManifest&&googleAllowed&&!manifestFailed,testContext,x.orders))throw Error('Simulated purchase is outside the authorized Preview scenario');
   if(x.orders.some(o=>o.checkout_id===id))return;if(x.checkout?.id!==id)throw Error('Checkout changed');const c=x.checkout,order={checkout_id:id,order_id:`demo_${crypto.randomUUID()}`,items:c.items,value_minor:c.items.reduce((n,i)=>n+i.price_minor,0)};x.orders.push(order);emit(x,'purchase_completed',c.items,{checkout_id:id,order_id:order.order_id});x.cart=[];x.checkout=null;});
 }else if(route==='inspect'){
  main.innerHTML=`<h1>Offline event inspector</h1><p>Vendor receipt: unverified. Warehouse reconciliation: not implemented. HTTP acceptance is not verified receipt.</p><p id="counts">${s.events.length} recorded events; ${s.orders.length} simulated orders.</p><p>Ordered session funnel: ${funnel(s.events).join(' → ')}</p><button id="export">Download local events</button> <button id="retry" ${s.events.length?'':'disabled'}>Replay latest event to local sink</button><p>Retries repeat the same payload locally. This does not test vendor delivery.</p><pre id="events"></pre>`;
  document.querySelector('#events').textContent=JSON.stringify({events:s.events,localDeliveryAttempts:s.attempts,cloudTransport:transport?.records||[],cloudPending:pending.size,localDataLayer:localLayer.records,googlePreview:google?.records||[]},null,2);
  if(manifestScope){
   const button=document.createElement('button');
   button.textContent='Download source manifest';button.disabled=!s.consent;
   button.onclick=async()=>{
    try{
     const rows=await readManifest();
     const a=document.createElement('a');
     a.href=URL.createObjectURL(new Blob(rows.map(row=>JSON.stringify(row)+'\n'),{type:'application/x-ndjson'}));
     a.download=testContext.test_run_id+'-'+testContext.scenario_id+'-source-events.ndjson';
     a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
    }catch(e){document.querySelector('#error').textContent=e.message;}
   };
   document.querySelector('#export').after(button);
  }
  document.querySelector('#retry').onclick=()=>action(x=>{if(x.consent&&x.events.length)x.attempts.push(structuredClone(x.events.at(-1)));});
  document.querySelector('#export').onclick=async()=>{const latest=await transaction();const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify({evidence:'offline_only',events:latest.events,attempts:latest.attempts},null,2)],{type:'application/json'}));a.download='commerce-offline-events.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
 }else{
  main.innerHTML=`<h1>A small catalog.<br>A complete measurement journey.</h1><p>Browse historical identifiers, build a cart and try a simulated purchase.</p><label>Category <select id="category"><option value="">All categories</option>${[...new Set(catalog.map(p=>p.source.product_category_name))].map(c=>`<option>${c}</option>`).join('')}</select></label><div class="grid" id="products"></div>`;
  const draw=value=>{document.querySelector('#products').innerHTML=catalog.filter(p=>!value||p.source.product_category_name===value).map((p,i)=>`<article class="product"><div class="placeholder" aria-hidden="true">${String(i+1).padStart(2,'0')}</div><h2>${p.display.title}</h2><p class="muted">Fictional display item</p><p>${money(p.display.price_minor)}</p><a href="#product/${p.source.product_id}">View product</a></article>`).join('');};draw('');document.querySelector('#category').onchange=e=>draw(e.target.value);
 }
}
async function action(fn,after){try{document.querySelector('#error').textContent='';const result=await transaction(fn);after?.(result);await render();await flushLocal();await flushGoogle();await flushCloud();}catch(e){document.querySelector('#error').textContent=e.message;}}
async function navigate(){const route=location.hash.slice(1);if(route.startsWith('product/'))await transaction(s=>emit(s,'product_viewed',[item(route.split('/')[1])]));await render();await flushLocal();await flushGoogle();await flushCloud();}
window.addEventListener('hashchange',()=>navigate().catch(e=>document.querySelector('#error').textContent=e.message));
channel.onmessage=async()=>{const latest=await transaction();if(!latest.consent){if(stopGoogle()){location.reload();return;}grantEpoch++;cloudAllowed=false;transport?.consent(false);pending.clear();localLayer.consent(false);layerPending.clear();}if(location.hash==='#inspect')await render();else{const s=await transaction();document.querySelector('#consent-status').textContent=s.consent?'Local recording allowed. External sending requires a separate tab grant.':'Local recording stopped. External telemetry disabled.';document.querySelector('#grant').disabled=s.consent;}};
document.querySelector('#grant').onclick=()=>action(s=>{s.consent=true;});
document.querySelector('#deny').onclick=()=>{const reload=stopGoogle();grantEpoch++;cloudAllowed=false;transport?.consent(false);pending.clear();localLayer.consent(false);layerPending.clear();return action(s=>{s.consent=false;s.identity=null;s.sequence=0;s.lastActivity=0;s.events=[];s.attempts=[];}).then(()=>{if(reload)location.reload();});};
document.querySelector('#reset').onclick=()=>{const reload=stopGoogle();grantEpoch++;cloudAllowed=false;transport?.consent(false);pending.clear();localLayer.consent(false);layerPending.clear();return action(s=>Object.assign(s,fresh()),()=>location.hash='catalog').then(()=>{if(reload)location.reload();});};
document.querySelector('#cloud-grant').onclick=async()=>{try{if(runtime.mode!=='posthog'||cloudAllowed)return;const epoch=++grantEpoch;const module=await import('./posthog.mjs');if(epoch!==grantEpoch)return;transport?.consent(false);transport=module.createTransport(runtime);cloudAllowed=true;transport.consent(true);await action(s=>{s.consent=true;});}catch{document.querySelector('#error').textContent='Cloud configuration failed; telemetry disabled.';cloudAllowed=false;}};
document.querySelector('#cloud-retry').onclick=async()=>{await flushCloud();await render();};
let googleGranting=false;
document.querySelector('#google-grant').onclick=async event=>{
 if(!event.isTrusted||!liveManifest||googleAllowed||googleGranting||manifestFailed)return;
 googleGranting=true;
 const epoch=++googleEpoch;
 event.currentTarget.disabled=true;
 try{
  const assertFresh=state=>{
   if(state.cart.length||state.checkout||state.orders.length||state.events.length||state.identity)
    throw Error('Use a fresh browser context for this scenario');
  };
  assertFresh(await transaction());
  if(epoch!==googleEpoch)return;
  const claim=await fetch('/preview-claim',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({run_id:testContext.test_run_id,scenario_id:testContext.scenario_id})});
  if(claim.status!==204)throw Error('Preview scenario authorization is unavailable or already used');
  if(epoch!==googleEpoch)return;
  const module=await import('./google-preview.mjs');
  if(epoch!==googleEpoch)return;
  await transaction(s=>{assertFresh(s);s.consent=true;});
  if(epoch!==googleEpoch)return;
  google=module.createGooglePreview(runtime,{target:window,document,preview:true,synthetic:true});
  google.consent(true);googleAllowed=true;
  await render();
 }catch(e){stopGoogle();document.querySelector('#error').textContent=e.message;}
 finally{googleGranting=false;document.querySelector('#google-grant').disabled=googleAllowed||manifestFailed;}
};
// Test labels are tab-local and never persist into manual visits.
await navigate();
