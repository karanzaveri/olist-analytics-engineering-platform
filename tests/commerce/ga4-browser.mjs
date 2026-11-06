// CUA/browser-tab API regression, with actual clicks. No injected events.
// Run verify(tab, createTab) on the offline COMMERCE_DATALAYER=local server.
// createTab(url) must return another tab in the same browser profile.
export default async function verify(tab,createTab){
 const all=[],checks=[];
 const inspect=async t=>{await t.playwright.getByRole('link',{name:'Event inspector',exact:true}).click();return JSON.parse(await t.playwright.locator('#events').textContent());};
 const assert=(ok,message)=>{if(!ok)throw Error(message);};
 async function start(){
  await tab.playwright.locator('#reset').click();
  await tab.playwright.getByRole('link',{name:'View product',exact:true}).first().waitFor({state:'visible'});
  await tab.playwright.locator('#grant').click();
  await tab.playwright.getByRole('link',{name:'View product',exact:true}).first().click();
  await tab.playwright.locator('#add').waitFor({state:'visible'});
 }
 async function checkout(){
  await tab.playwright.getByRole('link',{name:'Cart',exact:true}).click();
  await tab.playwright.locator('#checkout').click();
  await tab.playwright.locator('#complete').waitFor({state:'visible'});
 }
 for(let i=0;i<10;i++){
  await start();
  if(i>=4)await tab.playwright.locator('#add').click();
  if(i>=7)await checkout();
  if(i===9){await tab.playwright.locator('#complete').click();await tab.playwright.getByRole('heading',{name:'Simulated purchase complete'}).waitFor({state:'visible'});}
  const s=await inspect(tab),mapped=s.localDataLayer.filter(e=>e.event);
  assert(mapped.every(e=>s.events.some(c=>c.event_id===e.event_id&&c.occurred_at===e.commerce.occurred_at)),'canonical identity/timestamp mismatch');
  all.push(...mapped);
 }
 const counts=['view_item','add_to_cart','begin_checkout','purchase'].map(n=>all.filter(e=>e.event===n).length);
 assert(JSON.stringify(counts)==='[10,6,3,1]','independent UI oracle mismatch');
 assert(new Set(all.map(e=>e.commerce.app_session_id)).size===10,'session grain mismatch');
 checks.push('10 actual UI journeys: 20 mapped events, ten sessions, 10/6/3/1');
 await tab.reload();const refreshed=JSON.parse(await tab.playwright.locator('#events').textContent());
 assert(!refreshed.localDataLayer.length,'refresh requeued old events');checks.push('refresh does not replay historical purchase');
 await start();await tab.playwright.locator('#add').click();await tab.playwright.getByRole('link',{name:'Cart',exact:true}).click();
 await tab.playwright.getByRole('button',{name:'Remove item',exact:true}).click();
 assert((await inspect(tab)).localDataLayer.filter(e=>e.event==='remove_from_cart').length===1,'missing removal');checks.push('remove_from_cart from real UI');
 await start();await tab.playwright.locator('#add').click();await checkout();
 const other=await createTab(await tab.url());
 try{
  await other.playwright.locator('#complete').waitFor({state:'visible'});
  await Promise.all([tab.playwright.locator('#complete').click(),other.playwright.locator('#complete').click()]);
  const a=await inspect(tab),b=await inspect(other);
  assert([...a.localDataLayer,...b.localDataLayer].filter(e=>e.event==='purchase').length===1,'concurrent duplicate');
  await tab.playwright.locator('#retry').click();const retried=await inspect(tab);
  assert(retried.localDataLayer.length===a.localDataLayer.length,'retry requeued');
  checks.push('concurrent tabs: one purchase; local replay does not requeue');
  await tab.playwright.locator('#deny').click();
  await other.playwright.locator('#counts').filter({hasText:'0 recorded events'}).waitFor({state:'visible'});
  assert(!(await inspect(tab)).localDataLayer.length&&!(await inspect(other)).localDataLayer.length,'withdrawal retained data');
  checks.push('withdrawal clears both tab-local queues');
 }finally{await other.close();}
 return {evidence:'browser_verified_local_data_layer_only',counts,events:all,checks,googleTrackingLoaded:false,googleVendorReceipt:'not_attempted'};
}
