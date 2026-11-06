import test from 'node:test';
import assert from 'node:assert/strict';
import {createGooglePreview} from '../../commerce_demo/google-preview.mjs';
import {catalog} from '../../commerce_demo/catalog.mjs';
import {journeys} from './fixtures.mjs';
const event=journeys(catalog[0])[0];
function setup(mode='ga4_gtm'){
 const target={},scripts=[],doc={cookie:'',createElement:()=>({remove(){}}),head:{appendChild:s=>scripts.push(s)}};
 const adapter=createGooglePreview({mode,containerId:'GTM-PHWDGH9B',measurementId:'G-BSKG5RGN4Y'},{target,document:doc,preview:true,synthetic:true});
 return {target,scripts,adapter,doc};
}
test('default offline and explicit grant gate all loader requests',()=>{
 const off=setup('offline');off.adapter.consent(true);assert.equal(off.scripts.length,0);
 const s=setup();assert.equal(s.scripts.length,0);assert.equal(s.adapter.send(event),'disabled');
 s.adapter.consent(true);assert.equal(s.scripts.length,1);assert.equal(s.scripts[0].src,'https://www.googletagmanager.com/gtm.js?id=GTM-PHWDGH9B');
 assert.equal(s.adapter.send(event),'gtm_queued');assert.equal(s.adapter.send(event),'already_queued');
 assert.equal(s.target.dataLayer.filter(e=>e.event==='view_item').length,1);
 assert.equal(s.target.dataLayer.at(-1).event_id,event.event_id);
});
test('revoke suppresses measurement, clears journal and prevents sends',()=>{
 const s=setup();s.adapter.consent(true);s.adapter.send(event);s.adapter.consent(false);
 assert.equal(s.target['ga-disable-G-BSKG5RGN4Y'],true);
 assert.equal(s.adapter.send(event),'disabled');assert.deepEqual(s.adapter.records,[]);
 assert.equal(s.target.dataLayer.at(-1).commerce_google_consent,'denied');
});
test('foreign configuration, non-preview and unlabelled visits cannot load',()=>{
 for(const extra of [{preview:false,synthetic:true},{preview:true,synthetic:false}]){
  let loads=0;
  const a=createGooglePreview({mode:'ga4_gtm',containerId:'GTM-PHWDGH9B',measurementId:'G-BSKG5RGN4Y'},{target:{},document:{createElement:()=>({}),head:{appendChild:()=>loads++}},...extra});
  assert.throws(()=>a.consent(true),/Preview/);assert.equal(loads,0);
 }
 assert.throws(()=>createGooglePreview({mode:'ga4_gtm',containerId:'GTM-OTHER',measurementId:'G-BSKG5RGN4Y'},{}),/dedicated/);
});

test('late loader failures cannot repopulate a withdrawn journal',()=>{
 const s=setup();s.adapter.consent(true);s.adapter.consent(false);s.scripts[0].onerror();assert.deepEqual(s.adapter.records,[]);
});
