// Explicit live test: requires configured cloud server and user authorization.
export default async function live(page){
 const run=`commerce-live-${Date.now()}`,events=[],transport=[];
 for(let i=0;i<10;i++){
  const c=await page.context().browser().newContext(),p=await c.newPage();
  await p.goto(`http://127.0.0.1:8765/?test_run_id=${run}&scenario_id=journey-${i}`);
  await p.getByRole('button',{name:'Allow new events to PostHog in this tab',exact:true}).click();await p.waitForFunction(()=>document.querySelector('#cloud-status').textContent.includes('enabled in this tab'));
  await p.getByRole('link',{name:'View product',exact:true}).first().click();await p.getByRole('button',{name:'Add to cart',exact:true}).waitFor();
  if(i>=4){await p.getByRole('button',{name:'Add to cart',exact:true}).click();await p.waitForFunction(()=>document.querySelector('#add')?.disabled);}
  if(i>=7){await p.getByRole('link',{name:'Cart',exact:true}).click();await p.getByRole('button',{name:'Start checkout',exact:true}).click();await p.getByRole('button',{name:'Complete simulated purchase',exact:true}).waitFor();}
  if(i===9){await p.getByRole('button',{name:'Complete simulated purchase',exact:true}).click();await p.getByRole('heading',{name:'Simulated purchase complete'}).waitFor();}
  await p.getByRole('link',{name:'Event inspector',exact:true}).click();
  try{await p.waitForFunction(()=>{try{const d=JSON.parse(document.querySelector('#events').textContent);return d.cloudPending===0&&d.cloudTransport.length===d.events.length;}catch{return false;}},{},{timeout:15000});}catch{return {run,failedScenario:i,debug:await p.locator('#events').textContent()};}
  const d=JSON.parse(await p.locator('#events').textContent());events.push(...d.events);transport.push(...d.cloudTransport);await c.close();
 }
 const names=['product_viewed','product_added_to_cart','checkout_started','purchase_completed'];const counts=names.map(n=>events.filter(e=>e.event_name===n).length);
 if(JSON.stringify(counts)!=='[10,6,3,1]'||transport.some(x=>x.status!=='transport_accepted'))throw Error('Live expectation/transport failure');return {run,counts,events,transport,vendorReceipt:'unverified'};
}
