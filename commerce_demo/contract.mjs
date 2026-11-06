export const names=['product_viewed','product_added_to_cart','product_removed_from_cart','checkout_started','purchase_completed'];
const common=['event_id','event_name','occurred_at','anonymous_id','session_id','session_sequence','schema_version','environment','activity_origin','catalog_origin','display_provenance','simulation','consent_state','app_version','catalog_version','device_class','items','currency','value_minor'];
export function validate(e,catalog){
 const fail=m=>{throw new Error(m);};
 if(!e||typeof e!=='object')fail('event object required');
 for(const k of common)if(!(k in e))fail(`missing ${k}`);
 const allowed=[...common,'test_run_id','scenario_id','checkout_id','order_id'];
 if(Object.keys(e).some(k=>!allowed.includes(k)))fail('unknown property');
 for(const k of common.filter(k=>!['items','simulation','session_sequence','value_minor'].includes(k)))if(typeof e[k]!=='string'||!e[k])fail(`invalid ${k}`);
 if(!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/i.test(e.event_id))fail('invalid event_id');
 if(!names.includes(e.event_name)||e.schema_version!=='1.0.0'||e.app_version!=='1.0.0'||e.catalog_version!=='1.0.0'||e.environment!=='local_demo'||e.catalog_origin!=='olist_historical'||e.display_provenance!=='manual_demo'||e.simulation!==true||e.currency!=='BRL'||e.consent_state!=='granted')fail('invalid contract constant');
 if(!['manual_demo','synthetic_test'].includes(e.activity_origin)||!['desktop','tablet','mobile','unknown'].includes(e.device_class))fail('invalid enum');
 if(!/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(e.occurred_at)||!Number.isFinite(Date.parse(e.occurred_at))||new Date(e.occurred_at).toISOString()!==e.occurred_at)fail('invalid timestamp');
 if(!Number.isSafeInteger(e.session_sequence)||e.session_sequence<1||!Number.isSafeInteger(e.value_minor)||e.value_minor<0)fail('invalid integer');
 if(e.activity_origin==='synthetic_test'&&(!e.test_run_id||!e.scenario_id))fail('synthetic provenance required');
 if(e.activity_origin==='manual_demo'&&('test_run_id'in e||'scenario_id'in e))fail('manual provenance conflict');
 for(const k of ['test_run_id','scenario_id','checkout_id','order_id'])if(k in e&&(typeof e[k]!=='string'||!e[k]))fail(`invalid ${k}`);
 if(['checkout_started','purchase_completed'].includes(e.event_name)&&!e.checkout_id)fail('checkout required');
 if(e.event_name==='purchase_completed'&&!e.order_id?.startsWith('demo_'))fail('demo order required');
 if(!Array.isArray(e.items)||!e.items.length)fail('items required');
 if(e.event_name.startsWith('product_')&&e.items.length!==1)fail('one product required');
 const seen=new Set();let sum=0;
 for(const item of e.items){
  if(!item||Object.keys(item).sort().join(',')!=='category,demo_title,price_minor,product_id,quantity')fail('invalid item shape');
  const p=catalog.find(p=>p.source.product_id===item.product_id);
  if(!p||seen.has(item.product_id)||item.category!==p.source.product_category_name||item.demo_title!==p.display.title||item.price_minor!==p.display.price_minor||item.quantity!==1)fail('invalid catalog item');
  seen.add(item.product_id);sum+=item.price_minor;
 }
 if(sum!==e.value_minor)fail('total mismatch');return e;
}
export function funnel(events){
 const ids=new Map(),orders=new Map(),sessions=new Map();
 for(const e of events){
  const key=`${e.environment}/${e.event_id}`,body=JSON.stringify(e);
  if(ids.has(key)){if(ids.get(key)!==body)throw Error('event conflict');continue;}ids.set(key,body);
  if(e.event_name==='purchase_completed'){
   const k=`${e.environment}/${e.order_id}`;if(orders.has(k))throw Error('purchase conflict');orders.set(k,e);
  }
  const sk=`${e.environment}/${e.activity_origin}/${e.test_run_id||''}/${e.anonymous_id}/${e.session_id}`;
  if(!sessions.has(sk))sessions.set(sk,[]);sessions.get(sk).push(e);
 }
 const totals=[0,0,0,0];
 for(const rows of sessions.values()){
  rows.sort((a,b)=>Date.parse(a.occurred_at)-Date.parse(b.occurred_at)||a.session_sequence-b.session_sequence);
  const before=(a,b)=>a.occurred_at<b.occurred_at||(a.occurred_at===b.occurred_at&&a.session_sequence<b.session_sequence);
  const v=rows.find(e=>e.event_name==='product_viewed');if(!v)continue;totals[0]++;
  const within=rows.filter(e=>before(v,e)&&Date.parse(e.occurred_at)-Date.parse(v.occurred_at)<=1800000);
  const adds=within.filter(e=>e.event_name==='product_added_to_cart');if(!adds.length)continue;totals[1]++;
  const checkouts=within.filter(e=>e.event_name==='checkout_started'&&adds.some(a=>before(a,e)&&e.items.some(i=>i.product_id===a.items[0].product_id)));if(!checkouts.length)continue;totals[2]++;
  if(within.some(e=>e.event_name==='purchase_completed'&&checkouts.some(c=>c.checkout_id===e.checkout_id&&before(c,e)&&JSON.stringify(c.items)===JSON.stringify(e.items))))totals[3]++;
 }return totals;
}
