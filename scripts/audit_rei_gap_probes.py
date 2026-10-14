import asyncio
import inspect
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ['SUPABASE_URL'] = 'https://example.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'audit-only'
os.environ['OUTBOUND_ENABLED'] = 'false'
from backend.comps import calculator, homeharvest, redfin
from backend.lib import db
from backend.scout import cron, social_scraper, eviction_scraper
from backend.alerts import sms, email, deal_blast
from backend.api.routes import leads, calls, email_webhook
from backend.voice import tools
from backend.contracts.intel_packet import is_permission_expired
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pandas as pd

results = []
def record(key, actual, expected):
    results.append({'id': key, 'actual': actual, 'expected': expected, 'defect_observed': actual != expected})

record('R01', calculator._days_since('2026-10-01'), (__import__('datetime').datetime.now(__import__('datetime').timezone.utc).date()-__import__('datetime').date(2026,10,1)).days)
comp = {'sold_price': 100000, 'sqft': 1000, 'sold_date': '2026-10-01'}
record('R02', calculator.calculate_arv([comp] * 5, 1000)['confidence'], 'low')
record('R03', calculator.calculate_arv([comp, {'sold_price': 900000, 'sqft': 0}], None)['arv'], 10000000)
with patch.object(calculator, 'MAO_MULTIPLIER', 0.5):
    record('R04', calculator.calculate_arv([comp], 1000)['mao'], 2500000)
with patch.object(homeharvest, '_HH_AVAILABLE', True), patch.object(homeharvest, 'scrape_property', return_value=pd.DataFrame([{'list_price': 400000, 'sqft': 1000, 'beds': 3}]), create=True):
    record('R05', homeharvest.get_comps('subject', 'Stockton', 'CA', 3, 2, 1000)['arv_estimate'], 0)
with patch.object(homeharvest, 'get_comps', return_value={'arv_estimate': 1000000, 'confidence': 'LOW'}), patch.object(db, 'get_property_by_id', return_value={'city': 'Stockton', 'state': 'CA'}), patch.object(db, 'update_property_arv') as save:
    homeharvest.trigger_arv_computation('property', 'subject', 1000)
    record('R06', save.call_count, 0)
    record('R07', save.call_args.args[2], 0)

fake = MagicMock()
fake.__enter__.return_value = fake
fake.get.return_value.text = 'PRICE,SQUARE FEET,BEDS,BATHS,SOLD DATE\n100000,1000,3,2,2026-10-01\n'
with patch.object(redfin.httpx, 'Client', return_value=fake):
    redfin._get_comps_from_region('/city/stockton', 3, 2, 1000)
    first = fake.get.call_args.kwargs['params'].copy()
    redfin._get_comps_from_region('/city/tracy', 3, 2, 1000)
    record('R08', fake.get.call_args.kwargs['params'] == first, False)

with patch.object(social_scraper, 'scrape_craigslist_fsbo', return_value=[{'address': 'Synthetic'}]), patch.object(db, '_get_client') as store:
    social_scraper.run_social_scraper()
    record('R09', store.call_count > 0, True)
with patch.object(eviction_scraper, 'scrape_eviction_filings', return_value=[{'case_number': 'synthetic'}]), patch.object(db, '_get_client') as store:
    eviction_scraper.run_eviction_scraper()
    record('R10', store.call_count > 0, True)
called=[]
with patch.object(cron, 'run_rss_scraper', side_effect=lambda:called.append('rss')), patch.object(cron, 'run_expired_scraper', side_effect=lambda:called.append('expired')), patch.object(cron, 'run_eviction_scraper', side_effect=lambda:called.append('eviction')), patch.object(cron, 'run_crmls_scraper', side_effect=lambda:called.append('crmls')):
    cron.run_scout_cycle()
    record('R11', 'crmls' in called, True)

client = MagicMock()
client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = []
with patch.object(db, '_get_client', return_value=client):
    record('R12', asyncio.run(leads.update_notes('missing-lead', 'Synthetic'))['success'], False)
    record('R13', asyncio.run(calls.pause_campaign('missing-campaign'))['success'], False)

packet = {'safe_for_live_call': True, 'action_permissions': {'get_offer_range': {'level': 'quote_range'}}, 'compliance_context': {'requires_human_approval_above': 30000000}}
context = SimpleNamespace(intel_packet=packet, last_price_mentioned=None)
with patch.dict(os.environ, {'OUTBOUND_ENABLED':'true'}), patch.object(tools, 'write_tool_gate_log'), patch.object(db, 'get_lead_with_property', return_value={'properties': {'mao': 40000000, 'arv_confidence': 'high', 'updated_at': '2000-01-01T00:00:00Z'}}):
    gate = tools._preflight_gate('get_offer_range', SimpleNamespace(lead_id='lead', call_sid='sid'), context)
    quote = tools._verified_offer_range('lead', context)
    record('R14', {'blocked': gate['blocked'], 'range_dollars': quote}, {'blocked':True,'range_dollars':None})
record('R15', is_permission_expired({'level': 'quote_range'}), True)
try:
    inspect.signature(email.send_walkthrough_confirmation_email).bind({}, {}, 'synthetic-time')
    signature_result = 'compatible'
except TypeError:
    signature_result = 'TypeError_missing_appointment_str'
record('R16', signature_result, 'compatible')

with patch.object(email_webhook, '_verify_signature', return_value=True), patch.object(db, '_get_client', side_effect=RuntimeError('Synthetic database outage')):
    app = FastAPI(); app.include_router(email_webhook.router, prefix='/api')
    response = TestClient(app).post('/api/email/webhook', json=[{'event': 'unsubscribe', 'lead_id': 'synthetic-lead', 'email': 'synthetic@example.invalid'}])
    record('R17', response.status_code, 503)
with patch.object(db, '_get_client', side_effect=RuntimeError('Synthetic database outage')), patch.object(email, 'verify_unsubscribe_token', return_value=('synthetic-lead','synthetic@example.invalid')):
    page = asyncio.run(email_webhook.unsubscribe_page('synthetic-token'))
    record('R18', 'unsubscribed successfully' in page, False)

with patch.object(db, 'phone_is_do_not_call', return_value=False), patch.object(sms, '_is_tcpa_hours', return_value=True), patch.object(sms, '_from_number', return_value='+12095550100'), patch.object(sms, 'signalwire_post', return_value={'sid':'synthetic-accepted','status':'queued'}) as provider, patch.object(sms, 'insert_sms', side_effect=RuntimeError('Synthetic logging outage')):
    outcome=sms.send_sms('+12095550123','Synthetic')
    record('R19', {'provider_accepts': provider.call_count, 'returned_success': outcome}, {'provider_accepts':1,'returned_success':True})

client = MagicMock()
responses = [SimpleNamespace(data=[{'address':'Synthetic','city':'Stockton','arv':40000000,'mao':25000000}]), SimpleNamespace(data=[{'id':'buyer','owner_phone':'+12095550123','owner_email':'synthetic@example.invalid'}]), SimpleNamespace(data=[])]
client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [responses[0],responses[2]]
client.table.return_value.select.return_value.eq.return_value.execute.return_value = responses[1]
with patch.object(db, '_get_client', return_value=client), patch.object(deal_blast, '_send_buyer_sms', return_value=False), patch.object(deal_blast, '_send_buyer_email', return_value=False):
    deal_blast.blast_deal('property')
    payload=client.table.return_value.insert.call_args.args[0]
    record('R20', {'sms_sent':payload['sms_sent'],'email_sent':payload['email_sent']}, {'sms_sent':False,'email_sent':False})

with patch.dict(os.environ, {'SENDGRID_API_KEY':'synthetic-audit-key','OUTBOUND_ENABLED':'false'}), patch('httpx.post', return_value=SimpleNamespace(status_code=202, raise_for_status=lambda: None)) as provider:
    outcome=email.send_email('synthetic@example.invalid','Synthetic','Synthetic')
    record('R21', {'outbound_disabled':True,'provider_requests':provider.call_count,'accepted':outcome}, {'outbound_disabled':True,'provider_requests':0,'accepted':False})

from backend.voice import appointment_scheduler
now=__import__('datetime').datetime.now(__import__('datetime').timezone.utc)
lead={'id':'synthetic-lead','owner_phone':'+12095550123','appointment_at':(now-__import__('datetime').timedelta(hours=3)).isoformat(),'appointment_status':'confirmed','walkthrough_state':'completed','properties':{'address':'Synthetic'}}
with patch.object(appointment_scheduler,'_send_reminder',return_value=True) as sender, patch.object(appointment_scheduler,'update_appt_reminder_flags'):
    appointment_scheduler._process_lead(lead,now,now)
    record('R22',sender.call_count,0)

from backend.karpathys import outbox, business
async def backfill_poison():
    calls=[]
    async def publish(partition,lead):
        calls.append(lead)
        if lead=='bad':raise ValueError('Missing canonical property')
    with patch.object(db,'dashboard_lead_refresh_ids',return_value=['bad','healthy']),patch.object(business,'publish_business',side_effect=publish),patch.object(outbox,'recover_events',new=__import__('unittest').mock.AsyncMock()),patch.object(db,'dashboard_event_journal_health',return_value={'dead':0,'oldest_pending_seconds':0}),patch.object(outbox.asyncio,'sleep',side_effect=asyncio.CancelledError):
        try:await outbox.recovery_loop()
        except asyncio.CancelledError:pass
    return calls
record('R23',asyncio.run(backfill_poison()),['bad','healthy'])

lead={'id':'synthetic-email-only','owner_email':'synthetic@example.invalid','email_day':0,'last_email_at':(now-__import__('datetime').timedelta(days=40)).isoformat(),'properties':{'address':'Synthetic'}}
with patch.object(email,'send_drip_email',return_value=True) as sender,patch.object(email,'update_lead_email_progress'):
    email._process_email_lead(lead)
    record('R24',sender.call_count,1)

print(json.dumps({'suite':'REI merged-source isolated defect probes','limits':'Synthetic source/provider/datastore mocks; no live requests, messages or database writes','results':results},indent=2))
