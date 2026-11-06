import test from 'node:test';
import assert from 'node:assert/strict';
import {validate, funnel} from '../../commerce_demo/contract.mjs';
import {catalog} from '../../commerce_demo/catalog.mjs';
import {journeys, expected} from './fixtures.mjs';
test('catalog has twelve unique traceable source IDs and separate fictional overlay',()=>{
 assert.equal(catalog.length,12); assert.equal(new Set(catalog.map(x=>x.source.product_id)).size,12);
 for(const p of catalog){assert.match(p.source.product_id,/^[a-f0-9]{32}$/);assert.equal(p.display.provenance,'manual_demo');assert.ok(Number.isInteger(p.display.price_minor));}
});
test('independent journey oracle and replay',()=>{
 const events=journeys(catalog[0]);events.forEach(e=>validate(e,catalog));
 assert.deepEqual(funnel(events),expected);assert.deepEqual(funnel([...events,events.at(-1)]),expected);
 assert.throws(()=>funnel([...events,{...events.at(-1),value_minor:1}]),/conflict/);
});
test('reject invalid contract inputs',()=>{
 const e=journeys(catalog[0])[0];
 for(const patch of [{schema_version:'2'},{value_minor:-1},{session_sequence:1.1},{event_id:'x'},{consent_state:'denied'},{items:[]},{occurred_at:'yesterday'},{extra:'PII'}])assert.throws(()=>validate({...e,...patch},catalog));
 assert.throws(()=>validate({...e,items:[{...e.items[0],product_id:'unknown'}]},catalog));
});

test('valid later checkout path is not masked by abandonment; strict order and window',()=>{
 const rows=journeys(catalog[0]).slice(-4);const [v,a,c,p]=rows;
 const later={...c,event_id:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',checkout_id:'later',session_sequence:4,occurred_at:p.occurred_at};
 const purchase={...p,checkout_id:'later',session_sequence:5};
 assert.deepEqual(funnel([v,a,c,later,purchase]),[1,1,1,1]);
 assert.deepEqual(funnel([v,a,c,{...p,occurred_at:'2026-01-01T01:00:00.000Z'}]),[1,1,1,0]);
 assert.deepEqual(funnel([v,{...a,occurred_at:v.occurred_at,session_sequence:v.session_sequence},c,p]),[1,0,0,0]);
});
