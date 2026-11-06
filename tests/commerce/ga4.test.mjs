import test from 'node:test';
import assert from 'node:assert/strict';
import {catalog} from '../../commerce_demo/catalog.mjs';
import {journeys} from './fixtures.mjs';
import {mapEcommerce,createLocalDataLayer} from '../../commerce_demo/ga4.mjs';
const events=journeys(catalog[0]);
test('five mappings, original provenance, decimal money and purchase ID',()=>{
 const names={product_viewed:'view_item',product_added_to_cart:'add_to_cart',product_removed_from_cart:'remove_from_cart',checkout_started:'begin_checkout',purchase_completed:'purchase'};
 for(const [canonical,google] of Object.entries(names)){
  const source=structuredClone(events.find(e=>e.event_name===canonical)||events[0]); source.event_name=canonical;
  const mapped=mapEcommerce(source);
  assert.equal(mapped.event,google); assert.equal(mapped.event_id,source.event_id);
  assert.equal(mapped.commerce.occurred_at,source.occurred_at);
  assert.equal(mapped.commerce.app_session_id,source.session_id);
  assert.equal(mapped.commerce.activity_origin,'synthetic_test');
  assert.equal(mapped.ecommerce.value,source.value_minor/100);
  assert.deepEqual(mapped.ecommerce.items,[{item_id:source.items[0].product_id,item_name:source.items[0].demo_title,item_category:source.items[0].category,price:source.items[0].price_minor/100,quantity:1}]);
  assert.equal(mapped.ecommerce.transaction_id,canonical==='purchase_completed'?source.order_id:undefined);
 }
 const result=events.map(mapEcommerce);
 assert.deepEqual(['view_item','add_to_cart','begin_checkout','purchase'].map(n=>result.filter(e=>e.event===n).length),[10,6,3,1]);
 assert.throws(()=>mapEcommerce({...events[0],value_minor:1}),/total/);
});
test('default disabled; explicit local config plus consent required',()=>{
 const target={};const disabled=createLocalDataLayer({},target);disabled.consent(true);
 assert.equal(disabled.send(events[0]),'disabled');assert.equal(target.dataLayer,undefined);
 const local=createLocalDataLayer({dataLayer:'local'},target);
 assert.equal(local.send(events[0]),'disabled');assert.equal(target.dataLayer,undefined);
 local.consent(true);assert.equal(local.send(events[0]),'local_queued');
 assert.equal(target.dataLayer.length,2);assert.deepEqual(target.dataLayer[0],{ecommerce:null,commerce:null});
 assert.equal(local.send(events[0]),'already_queued');assert.equal(target.dataLayer.length,2);
 local.consent(false);assert.equal(target.dataLayer,undefined);assert.equal(local.send(events[1]),'disabled');
});
test('snapshot copies, conflict protection and existing layer ownership',()=>{
 const target={};const local=createLocalDataLayer({dataLayer:'local'},target);local.consent(true);
 const source=structuredClone(events[0]);local.send(source);source.items[0].demo_title='modified';
 assert.notEqual(target.dataLayer[1].ecommerce.items[0].item_name,'modified');
 assert.throws(()=>local.send({...events[0],device_class:'mobile'}),/conflict/);
 const occupied={dataLayer:[]};assert.throws(()=>createLocalDataLayer({dataLayer:'local'},occupied).consent(true),/owned/);
});
