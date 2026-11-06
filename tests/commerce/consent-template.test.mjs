import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

test('unchanged consent template denies by default and grants only analytics explicitly',()=>{
 const template=readFileSync(new URL('../../commerce_demo/consent-template.tpl',import.meta.url),'utf8');
 const code=template.split('___SANDBOXED_JS_FOR_WEB_TEMPLATE___')[1].split('___WEB_PERMISSIONS___')[0].trim();
 for(const choice of [undefined,'denied','granted']){
  const calls=[];let successes=0;
  vm.runInNewContext(code,{require(name){
   if(name==='setDefaultConsentState')return value=>calls.push(['default',JSON.parse(JSON.stringify(value))]);
   if(name==='updateConsentState')return value=>calls.push(['update',JSON.parse(JSON.stringify(value))]);
   if(name==='copyFromDataLayer')return key=>{assert.equal(key,'commerce_google_consent');return choice;};
   throw Error('Unexpected template API '+name);
  },data:{gtmOnSuccess(){successes++;}}},{timeout:1000});
  assert.equal(successes,1);
  assert.deepEqual(calls[0],['default',{analytics_storage:'denied',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'}]);
  assert.deepEqual(calls[1],['update',{analytics_storage:choice==='granted'?'granted':'denied',ad_storage:'denied',ad_user_data:'denied',ad_personalization:'denied'}]);
 }
});

