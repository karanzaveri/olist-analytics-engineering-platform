// Intercepted requests only: this test never sends to PostHog.
export default async function verifyCloud(page){
 const c=await page.context().browser().newContext();const sent=[];let loads=0;
 await c.route('**/*',async r=>{const url=r.request().url();if(url.startsWith('https://eu.i.posthog.com/')){sent.push(r.request().postDataJSON());return r.fulfill({status:200,contentType:'application/json',body:'{"status":1}'});}if(!url.startsWith('http://127.0.0.1:8765/'))throw Error('Unexpected network');
 if(url.endsWith('/runtime.mjs'))return r.fulfill({contentType:'text/javascript',body:"export const runtime={mode:'posthog',host:'https://eu.i.posthog.com',token:'phc_test_public'};"});
 if(url.endsWith('/posthog.mjs'))loads++;
 if(new URL(url).pathname==='/'){const response=await r.fetch();return r.fulfill({response,body:(await response.text()).replace("connect-src 'self'","connect-src 'self' https://eu.i.posthog.com")});}return r.continue();});
 const p=await c.newPage();await p.goto('http://127.0.0.1:8765/?test_run_id=mock-cloud&scenario_id=consent');
 await p.getByRole('button',{name:'Allow local event recording',exact:true}).click();await p.getByRole('link',{name:'View product',exact:true}).first().click();await p.getByRole('button',{name:'Add to cart',exact:true}).waitFor();
 if(loads||sent.length)throw Error('Tracking loaded before cloud consent');
 await p.getByRole('button',{name:'Allow new events to PostHog in this tab',exact:true}).click();await p.getByRole('button',{name:'Add to cart',exact:true}).click();await p.waitForFunction(()=>document.querySelector('#add')?.disabled);
 await p.getByRole('link',{name:'Event inspector',exact:true}).click();await p.waitForFunction(()=>document.querySelector('#events')?.textContent.includes('transport_accepted'));
 if(sent.length!==1||sent[0].event!=='product_added_to_cart'||sent[0].properties.test_run_id!=='mock-cloud')throw Error('Unexpected capture or pre-consent replay');
 await p.getByRole('button',{name:'Stop recording and clear events',exact:true}).click();await p.getByRole('link',{name:'Catalog',exact:true}).click();await p.getByRole('link',{name:'View product',exact:true}).first().click();await p.getByRole('button',{name:'Add to cart',exact:true}).waitFor();if(sent.length!==1)throw Error('Capture after withdrawal');
 await c.close();return {adapterLoadedAfterConsent:true,interceptedCaptures:sent.length,preConsentReplay:false,postWithdrawalCapture:false,vendorReceipt:'unverified'};
}
