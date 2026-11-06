import {validate} from './contract.mjs';
import {catalog} from './catalog.mjs';
export function createTransport(config,request=globalThis.fetch){
 const enabled=config.mode==='posthog';
 if(enabled&&(!['https://eu.i.posthog.com','https://us.i.posthog.com'].includes(config.host)||!/^phc_[A-Za-z0-9_]+$/.test(config.token||'')))throw Error('Invalid public PostHog capture configuration');
 let allowed=false,generation=0;const attempts=new Map(),accepted=new Set(),inflight=new Map();
 const records=[],receipts=[];
 function consent(value){generation++;allowed=enabled&&value;if(!allowed){for(const c of inflight.values())c.abort();inflight.clear();attempts.clear();accepted.clear();records.length=0;}}
 async function send(event){
  if(!allowed)return 'disabled';validate(event,catalog);
  const epoch=generation;const id=event.event_id;if(accepted.has(id))return 'transport_accepted';if(inflight.has(id))return 'in_flight';
  const n=attempts.get(id)||0;if(n>=3)return 'retry_limit';attempts.set(id,n+1);
  const controller=new AbortController();inflight.set(id,controller);const timer=setTimeout(()=>controller.abort(),10000);
  const payload={api_key:config.token,event:event.event_name,distinct_id:event.anonymous_id,timestamp:event.occurred_at,properties:{...structuredClone(event),$process_person_profile:false,$geoip_disable:true,ip:0}};
  let status='failed',http_status;
  try{const response=await request(`${config.host}/i/v0/e/`,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'omit',referrerPolicy:'no-referrer',redirect:'error',body:JSON.stringify(payload),signal:controller.signal});http_status=response.status;status=response.ok?'transport_accepted':'rejected';if(response.ok&&allowed&&generation===epoch)accepted.add(id);if(!response.ok&&response.status>=400&&response.status<500&&response.status!==429)attempts.set(id,3);}
  catch{status=controller.signal.aborted?'cancelled_or_timeout':'failed';}
  finally{clearTimeout(timer);inflight.delete(id);}
  if(allowed&&generation===epoch)records.push({event_id:id,status,http_status,attempt:n+1});return status;
 }
 return {consent,send,records,receipts};
}
