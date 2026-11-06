// Dedicated, explicit-consent GTM Preview transport. Queueing is not vendor receipt.
import {mapEcommerce} from './ga4.mjs';
const CONTAINER='GTM-PHWDGH9B',MEASUREMENT='G-BSKG5RGN4Y';
export function createGooglePreview(config={},options={}){
 const enabled=config.mode==='ga4_gtm';
 if(enabled&&(config.containerId!==CONTAINER||config.measurementId!==MEASUREMENT))throw Error('Only the dedicated demo destination is allowed');
 const target=options.target||globalThis,doc=options.document||globalThis.document;
 let allowed=false,loaded=false,layer;const seen=new Map(),journal=[];
 function consent(value){
  if(!enabled)return;
  if(value===true){
   if(!options.preview||!options.synthetic)throw Error('Labelled synthetic Preview visit required');
   if(loaded&&!allowed)throw Error('Reload after consent withdrawal before re-enabling Preview');
   if(allowed)return;
   if('dataLayer' in target)throw Error('A foreign dataLayer already exists');
   layer=[];target.dataLayer=layer;allowed=true;target['ga-disable-'+MEASUREMENT]=false;
   layer.push({commerce_google_consent:'granted'},{'gtm.start':Date.now(),event:'gtm.js'},{event:'commerce_google_ready',commerce_google_consent:'granted'});
   const script=doc.createElement('script');script.async=true;script.src='https://www.googletagmanager.com/gtm.js?id='+CONTAINER;
   script.onerror=()=>{if(allowed)journal.push({status:'loader_failed',vendorReceipt:'unverified'});};
   doc.head.appendChild(script);loaded=true;
  }else{
   allowed=false;target['ga-disable-'+MEASUREMENT]=true;seen.clear();journal.length=0;
   if(layer)layer.push({ecommerce:null,commerce:null,event:'commerce_consent_update',commerce_google_consent:'denied'});
   if(doc&&typeof doc.cookie==='string')for(const cookie of doc.cookie.split(';')){const name=cookie.split('=')[0].trim();if(/^_ga(?:_|$)/.test(name))doc.cookie=name+'=; Max-Age=0; Path=/; SameSite=Lax';}
  }
 }
 function send(event){
  if(!allowed)return 'disabled';
  if(event.activity_origin!=='synthetic_test')throw Error('Only synthetic demo events may leave this adapter');
  const mapped=mapEcommerce(event),key=event.environment+'/'+event.event_id,body=JSON.stringify(event);
  if(seen.has(key)){if(seen.get(key)!==body)throw Error('event conflict');return 'already_queued';}
  layer.push({ecommerce:null,commerce:null},{...mapped,commerce_google_consent:'granted'});
  seen.set(key,body);journal.push({event_id:event.event_id,status:'gtm_queued',vendorReceipt:'unverified'});return 'gtm_queued';
 }
 return {consent,send,get loaded(){return loaded;},get records(){return structuredClone(journal);}};
}
