// Run with the Playwright browser_run_code tool, or import and call default(page)
// from an existing Playwright installation. No event injection: actions use UI.
export default async function verify(page){
 const browser=page.context().browser();const failures=[],requests=[],results=[];
 const check=(ok,message)=>{if(!ok)throw Error(message);};
 const state=p=>p.evaluate(()=>new Promise((resolve,reject)=>{const r=indexedDB.open('olist-commerce-offline',1);r.onsuccess=()=>{const db=r.result,t=db.transaction('state'),q=t.objectStore('state').get('demo');q.onsuccess=()=>{resolve(q.result);db.close();};q.onerror=()=>reject(q.error);};}));
 async function context(){const c=await browser.newContext();await c.route('**/*',r=>{const u=new URL(r.request().url());requests.push(u.href);if(u.origin!=='http://127.0.0.1:8765'){failures.push(u.href);return r.abort();}return r.continue();});return c;}
 async function open(c,scenario){const p=await c.newPage();await p.goto(`http://127.0.0.1:8765/?test_run_id=browser-oracle&scenario_id=${scenario}`);await p.getByRole('button',{name:'Allow local event recording'}).click();return p;}
 async function view(p){await p.getByRole('link',{name:'View product',exact:true}).first().click();await p.getByRole('button',{name:'Add to cart',exact:true}).waitFor();}
 async function checkout(p){await p.getByRole('button',{name:'Add to cart',exact:true}).click();await p.getByRole('link',{name:'Cart',exact:true}).click();await p.getByRole('button',{name:'Start checkout',exact:true}).click();await p.getByRole('button',{name:'Complete simulated purchase',exact:true}).waitFor();}
 let all=[];
 for(let i=0;i<10;i++){
  const c=await context(),p=await open(c,`journey-${i}`);await view(p);
  if(i>=4){if(i>=7)await checkout(p);else await p.getByRole('button',{name:'Add to cart',exact:true}).click();}
  if(i===9){await p.getByRole('button',{name:'Complete simulated purchase',exact:true}).click();await p.getByRole('heading',{name:'Simulated purchase complete'}).waitFor();}
  const s=await state(p);all.push(...s.events);await c.close();
 }
 // Independent literals, not generated from production funnel.
 const expected=[10,6,3,1],names=['product_viewed','product_added_to_cart','checkout_started','purchase_completed'];
 check(JSON.stringify(names.map(n=>all.filter(e=>e.event_name===n).length))===JSON.stringify(expected),'actual UI event oracle mismatch');
 const computed=await page.evaluate(async events=>(await import('/contract.mjs')).funnel(events),all);check(JSON.stringify(computed)===JSON.stringify(expected),'UI session funnel mismatch');results.push('10 actual browser journeys: 10/6/3/1, 20 core events');
 const c=await context(),p=await open(c,'idempotency');await view(p);await checkout(p);const url=p.url();
 await p.getByRole('button',{name:'Complete simulated purchase',exact:true}).dblclick();await p.getByRole('heading',{name:'Simulated purchase complete'}).waitFor();
 await p.reload();await p.getByRole('heading',{name:'Simulated purchase complete'}).waitFor();let s=await state(p);check(s.orders.length===1&&s.events.filter(e=>e.event_name==='purchase_completed').length===1,'double click/refresh duplicate');results.push('double click and refresh: one order/purchase');
 await p.getByRole('link',{name:'Event inspector',exact:true}).click();await p.getByRole('button',{name:'Replay latest event to local sink'}).click();await p.getByRole('button',{name:'Replay latest event to local sink'}).click();s=await state(p);check(s.attempts.length===2&&s.attempts.every(e=>e.event_id===s.events.at(-1).event_id)&&s.orders.length===1,'local retry changed event/order');results.push('two local retries: identical event ID, one order');
 await p.getByRole('button',{name:'Stop recording and clear events'}).click();s=await state(p);check(!s.identity&&!s.events.length&&!s.attempts.length&&s.orders.length===1,'withdrawal failed');await p.reload();s=await state(p);check(!s.consent&&!s.identity,'withdrawal persistence failed');results.push('withdrawal clears analytics, preserves functional order');await c.close();
 const d=await context(),a=await open(d,'concurrent');await view(a);await checkout(a);const b=await d.newPage();await b.goto(a.url());await b.getByRole('button',{name:'Complete simulated purchase',exact:true}).waitFor();
 await Promise.all([a.getByRole('button',{name:'Complete simulated purchase',exact:true}).click(),b.getByRole('button',{name:'Complete simulated purchase',exact:true}).click()]);await a.getByRole('heading',{name:'Simulated purchase complete'}).waitFor();s=await state(a);check(s.orders.length===1&&s.events.filter(e=>e.event_name==='purchase_completed').length===1,'concurrent duplicate');results.push('two tabs completing same checkout: one order/purchase');await d.close();
 const e=await context(),denied=await e.newPage();await denied.goto('http://127.0.0.1:8765');await view(denied);await checkout(denied);await denied.getByRole('button',{name:'Complete simulated purchase',exact:true}).click();await denied.getByRole('heading',{name:'Simulated purchase complete'}).waitFor();s=await state(denied);check(!s.identity&&!s.events.length&&s.orders.length===1,'denied consent collected analytics');results.push('denied consent: functional purchase, zero events/identity');await e.close();
 const f=await context(),rem=await open(f,'remove');await view(rem);await rem.getByRole('button',{name:'Add to cart',exact:true}).click();await rem.getByRole('link',{name:'Cart',exact:true}).click();await rem.getByRole('button',{name:'Remove item'}).click();await rem.waitForFunction(()=>document.querySelector('#checkout')?.disabled===true);check(await rem.getByRole('button',{name:'Start checkout'}).isDisabled(),'empty checkout enabled');s=await state(rem);check(s.events.at(-1).event_name==='product_removed_from_cart','missing removal event');results.push('removal event and empty checkout guard');await f.close();

 const shared=await context(),owner=await open(shared,'label-A');await view(owner);
 const other=await shared.newPage();await other.goto('http://127.0.0.1:8765/');await view(other);
 let sharedState=await state(other);check(sharedState.events.at(-1).activity_origin==='manual_demo','synthetic label leaked into manual visit');
 await other.getByRole('link',{name:'Event inspector',exact:true}).click();await other.locator('#counts').filter({hasText:'2 recorded events'}).waitFor();
 await owner.getByRole('button',{name:'Stop recording and clear events'}).click();await other.locator('#counts').filter({hasText:'0 recorded events'}).waitFor();
 check(!(await other.locator('#events').textContent()).includes('anonymous_id'),'stale identity after withdrawal');
 results.push('tab-local provenance and cross-tab withdrawal inspector invalidation');await shared.close();
 check(!failures.length,'external requests attempted');return {evidence:'browser_verified_offline_only',results,externalRequests:failures,requestCount:requests.length,vendorReceipt:'not_implemented',warehouseReconciliation:'not_implemented'};
}
