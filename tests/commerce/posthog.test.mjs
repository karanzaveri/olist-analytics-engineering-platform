import test from 'node:test';
import assert from 'node:assert/strict';
import {createTransport} from '../../commerce_demo/posthog.mjs';
import {journeys} from './fixtures.mjs';
import {catalog} from '../../commerce_demo/catalog.mjs';
const config={mode:'posthog',host:'https://eu.i.posthog.com',token:'phc_test_public'};
test('requires explicit mode and consent; HTTP acceptance is not receipt',async()=>{
 let calls=[];const send=async(url,options)=>{calls.push({url,options});return {ok:true,status:200};};
 const t=createTransport(config,send);const e=journeys(catalog[0])[0];
 assert.equal(await t.send(e), 'disabled');assert.equal(calls.length,0);
 t.consent(true);assert.equal(await t.send(e),'transport_accepted');
 const p=JSON.parse(calls[0].options.body);assert.equal(p.timestamp,e.occurred_at);assert.equal(p.properties.event_id,e.event_id);assert.equal(p.distinct_id,e.anonymous_id);assert.equal(p.properties.$process_person_profile,false);assert.equal(p.properties.$geoip_disable,true);assert.deepEqual(p.properties.items,e.items);assert.equal(t.receipts.length,0);
 t.consent(false);assert.equal(await t.send(e),'disabled');assert.equal(calls.length,1);
});
test('offline and invalid configuration fail closed',()=>{
 assert.throws(()=>createTransport({...config,host:'https://evil.example'}));assert.throws(()=>createTransport({...config,token:'phx_secret'}));
 const t=createTransport({mode:'offline'},()=>{throw Error('network');});t.consent(true);return t.send(journeys(catalog[0])[0]).then(x=>assert.equal(x,'disabled'));
});
test('retry is explicit, bounded and preserves body; errors never mean receipt',async()=>{
 const bodies=[];const t=createTransport(config,async(_,o)=>{bodies.push(o.body);if(bodies.length===1)throw Error('network');return {ok:true,status:200};});t.consent(true);const e=journeys(catalog[0])[0];
 assert.equal(await t.send(e),'failed');assert.equal(await t.send(e),'transport_accepted');assert.equal(bodies[0],bodies[1]);assert.equal(t.receipts.length,0);
 const bad=createTransport(config,async()=>({ok:false,status:400}));bad.consent(true);assert.equal(await bad.send(e),'rejected');assert.equal(await bad.send(e),'retry_limit');
});
