// Local preparation only: no Google loader, gtag, cookies or network transport.
import {validate} from './contract.mjs';
import {catalog} from './catalog.mjs';
const mapping={product_viewed:'view_item',product_added_to_cart:'add_to_cart',product_removed_from_cart:'remove_from_cart',checkout_started:'begin_checkout',purchase_completed:'purchase'};
export function previewManifestArmed(runtime,params,hostname){
 const run=params.get('test_run_id');
 return hostname==='127.0.0.1'&&runtime.mode==='ga4_gtm'&&runtime.containerId==='GTM-PHWDGH9B'&&
  runtime.measurementId==='G-BSKG5RGN4Y'&&runtime.streamId==='16265125392'&&
  params.get('source_manifest')==='1'&&params.get('ga4_preview')==='1'&&
  /^ga4-live-[0-9]{25}$/.test(run||'')&&runtime.liveRunId===run&&
  /^(journey-0[0-9]|remove-00)$/.test(params.get('scenario_id')||'');
}

export function previewPurchaseAllowed(runtime,authorized,scenario,orders){
 return runtime.mode!=='ga4_gtm'||(authorized&&scenario?.scenario_id==='journey-09'&&orders.length===0);
}

export function mapEcommerce(event){
 validate(event,catalog);
 const {items,value_minor,currency,event_id,event_name,session_id,anonymous_id,...metadata}=structuredClone(event);
 return {event:mapping[event_name],event_id,
  commerce:{...metadata,canonical_event_name:event_name,app_session_id:session_id,app_anonymous_id:anonymous_id,checkout_id:event.checkout_id??null,order_id:event.order_id??null,test_run_id:event.test_run_id??null,scenario_id:event.scenario_id??null},
  ecommerce:{currency,value:value_minor/100,items:items.map(i=>({item_id:i.product_id,item_name:i.demo_title,item_category:i.category,price:i.price_minor/100,quantity:i.quantity})),...(event_name==='purchase_completed'?{transaction_id:event.order_id}:{})}};
}
export function createLocalDataLayer(config={},target=globalThis){
 let allowed=false,layer;const seen=new Map();
 function consent(value){
  allowed=config.dataLayer==='local'&&value===true;
  if(allowed){
   if(!layer){if('dataLayer' in target)throw Error('dataLayer must be owned by this local adapter');layer=[];target.dataLayer=layer;}
  }else{
   seen.clear();if(layer){layer.length=0;if(target.dataLayer===layer)delete target.dataLayer;layer=undefined;}
  }
 }
 function send(event){
  if(!allowed)return 'disabled';
  const mapped=mapEcommerce(event),key=event.environment+'/'+event.event_id,body=JSON.stringify(event);
  if(seen.has(key)){if(seen.get(key)!==body)throw Error('event conflict');return 'already_queued';}
  if(target.dataLayer!==layer||layer.push!==Array.prototype.push)throw Error('Local dataLayer ownership changed');
  layer.push({ecommerce:null,commerce:null},mapped);seen.set(key,body);return 'local_queued';
 }
 return {consent,send,get records(){return structuredClone(layer||[]);}};
}
