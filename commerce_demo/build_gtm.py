"""Build the dedicated, importable, unpublished commerce GTM draft. Stdlib only."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ACCOUNT='6402242168'
CONTAINER='285052342'
MEASUREMENT='G-BSKG5RGN4Y'
# Container-export enums are uppercase; REST consentStatus spellings are different.
FIELDS=['canonical_event_name','occurred_at','session_sequence','schema_version','app_version','catalog_version','environment','activity_origin','catalog_origin','display_provenance','simulation','consent_state','device_class','app_session_id','app_anonymous_id','test_run_id','scenario_id','checkout_id','order_id']
def parameter(key,value,type='TEMPLATE'):
    return {'type':type,'key':key,'value':value}
def table(key,rows):
    return {'type':'LIST','key':key,'list':[{'type':'MAP','map':[parameter('parameter',k),parameter('parameterValue',v)]} for k,v in rows]}
def condition(type,left,right):
    return {'type':type,'parameter':[parameter('arg0',left),parameter('arg1',right)]}
def build_container():
    variables=[]
    for index,(name,key) in enumerate([('event_id','event_id'),('google_consent','commerce_google_consent')]+[(f,'commerce.'+f) for f in FIELDS],1):
        variables.append({'accountId':ACCOUNT,'containerId':CONTAINER,'variableId':str(index),'name':'Commerce - '+name,'type':'v','parameter':[parameter('name',key),parameter('dataLayerVersion','2','INTEGER'),parameter('setDefaultValue','false','BOOLEAN')]})
    gate=[condition('EQUALS','{{Debug Mode}}','true'),condition('EQUALS','{{Commerce - google_consent}}','granted'),condition('EQUALS','{{Page Hostname}}','127.0.0.1')]
    event_gate=gate+[condition('EQUALS','{{Commerce - activity_origin}}','synthetic_test'),condition('MATCH_REGEX','{{Commerce - test_run_id}}','^ga4-live-[0-9]+$')]
    triggers=[{'triggerId':'100','name':'Commerce - Consent initialization','type':'CONSENT_INIT'}]
    for id,name,filters in [('101','commerce_consent_update',[]),('102','commerce_google_ready',gate)]+[(str(110+i),n,event_gate) for i,n in enumerate(['view_item','add_to_cart','remove_from_cart','begin_checkout','purchase'])]:
        triggers.append({'triggerId':id,'name':'Commerce - '+name,'type':'CUSTOM_EVENT','customEventFilter':[condition('EQUALS','{{_event}}',name)],'filter':filters})
    tags=[{'tagId':'1','name':'Commerce - analytics-only consent','type':'cvt_'+CONTAINER+'_3','firingTriggerId':['100','101'],'tagFiringOption':'ONCE_PER_EVENT'},
          {'tagId':'2','name':'Commerce - Google tag','type':'googtag','parameter':[parameter('tagId',MEASUREMENT),table('configSettingsTable',[('send_page_view','false'),('allow_google_signals','false'),('allow_ad_personalization_signals','false'),('debug_mode','true')])],'firingTriggerId':['102'],'tagFiringOption':'ONCE_PER_LOAD','consentSettings':{'consentStatus':'NEEDED','consentType':{'type':'LIST','list':[{'type':'TEMPLATE','value':'analytics_storage'}]}}}]
    for i,name in enumerate(['view_item','add_to_cart','remove_from_cart','begin_checkout','purchase']):
        tags.append({'tagId':str(10+i),'name':'Commerce - '+name,'type':'gaawe','parameter':[parameter('measurementIdOverride',MEASUREMENT),parameter('eventName',name),parameter('sendEcommerceData','true','BOOLEAN'),parameter('getEcommerceDataFrom','dataLayer'),table('eventSettingsTable',[('event_id','{{Commerce - event_id}}'),('debug_mode','true')]+[(f,'{{Commerce - '+f+'}}') for f in FIELDS])],'firingTriggerId':[str(110+i)],'tagFiringOption':'ONCE_PER_EVENT','setupTag':[{'tagName':'Commerce - Google tag','stopOnSetupFailure':True}],'consentSettings':{'consentStatus':'NEEDED','consentType':{'type':'LIST','list':[{'type':'TEMPLATE','value':'analytics_storage'}]}}})
    return {'exportFormatVersion':2,'containerVersion':{'accountId':ACCOUNT,'containerId':CONTAINER,'containerVersionId':'0','container':{'accountId':ACCOUNT,'containerId':CONTAINER,'name':'Commerce Demo Local','publicId':'GTM-PHWDGH9B','usageContext':['WEB']},'builtInVariable':[{'accountId':ACCOUNT,'containerId':CONTAINER,'type':t,'name':n} for t,n in [('PAGE_URL','Page URL'),('PAGE_HOSTNAME','Page Hostname'),('PAGE_PATH','Page Path'),('REFERRER','Referrer'),('EVENT','Event'),('DEBUG_MODE','Debug Mode')]],'tag':tags,'trigger':triggers,'variable':variables,'customTemplate':[{'accountId':ACCOUNT,'containerId':CONTAINER,'templateId':'3','name':'Commerce analytics-only consent','templateData':(ROOT/'consent-template.tpl').read_text(encoding='utf-8')}]}}
if __name__=='__main__':
    path=ROOT/'gtm-container.json'
    path.write_text(json.dumps(build_container(),indent=2),encoding='utf-8')
    print(str(path))

