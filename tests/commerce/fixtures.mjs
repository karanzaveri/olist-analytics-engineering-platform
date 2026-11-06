// Literal journey specification and expected results, independent of funnel implementation.
export const expected = [10,6,3,1];
const paths=[1,1,1,1,2,2,2,3,3,4];
export function journeys(product){
 const events=[];const names=['product_viewed','product_added_to_cart','checkout_started','purchase_completed'];
 paths.forEach((length,s)=>{for(let i=0;i<length;i++)events.push({
 event_id:`00000000-0000-4000-8000-${String(s*4+i).padStart(12,'0')}`,event_name:names[i],occurred_at:new Date(Date.UTC(2026,0,1,0,i)).toISOString(),
 anonymous_id:`visitor-${s}`,session_id:`session-${s}`,session_sequence:i+1,schema_version:'1.0.0',environment:'local_demo',activity_origin:'synthetic_test',catalog_origin:'olist_historical',display_provenance:'manual_demo',simulation:true,test_run_id:'oracle',scenario_id:`journey-${s}`,consent_state:'granted',app_version:'1.0.0',catalog_version:'1.0.0',device_class:'desktop',
 items:[{product_id:product.source.product_id,category:product.source.product_category_name,demo_title:product.display.title,price_minor:product.display.price_minor,quantity:1}],currency:'BRL',value_minor:product.display.price_minor,
 ...(i>=2?{checkout_id:`checkout-${s}`} :{}),...(i===3?{order_id:`demo_${s}`}:{})
 });});return events;
}
