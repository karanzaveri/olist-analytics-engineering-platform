import {previewManifestArmed,previewPurchaseAllowed} from '../../commerce_demo/ga4.mjs';
import test from 'node:test';
import assert from 'node:assert/strict';

const run='ga4-live-1793890387648262484762878';
const runtime={mode:'ga4_gtm',containerId:'GTM-PHWDGH9B',measurementId:'G-BSKG5RGN4Y',
 streamId:'16265125392',liveRunId:run};
const params=new URLSearchParams({test_run_id:run,scenario_id:'journey-09',
 source_manifest:'1',ga4_preview:'1'});

test('only matching local Preview authorization arms the source journal',()=>{
 assert.equal(previewManifestArmed(runtime,params,'127.0.0.1'),true);
 for(const [key,value] of Object.entries(runtime)){
  assert.equal(previewManifestArmed({...runtime,[key]:'wrong'},params,'127.0.0.1'),false);
 }
 for(const [key,value] of [['test_run_id','ga4-live-2026110302'],['scenario_id','journey-10'],
  ['source_manifest','0'],['ga4_preview','0']]){
  const changed=new URLSearchParams(params);changed.set(key,value);
  assert.equal(previewManifestArmed(runtime,changed,'127.0.0.1'),false);
 }
 assert.equal(previewManifestArmed(runtime,params,'localhost'),false);
});

test('live completion is restricted to the one consented final scenario purchase',()=>{
 const final={scenario_id:'journey-09'};
 assert.equal(previewPurchaseAllowed(runtime,false,final,[]),false);
 assert.equal(previewPurchaseAllowed(runtime,true,{scenario_id:'remove-00'},[]),false);
 assert.equal(previewPurchaseAllowed(runtime,true,final,[{order_id:'demo_1'}]),false);
 assert.equal(previewPurchaseAllowed(runtime,true,final,[]),true);
 assert.equal(previewPurchaseAllowed({mode:'offline'},false,null,[]),true);
});
