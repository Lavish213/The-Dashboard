import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

os.environ['DATABASE_URL']='postgresql+asyncpg://audit:audit@127.0.0.1:1/audit_test'
os.environ['SECRET_KEY']='synthetic-audit-only-not-for-production-123456789'
os.environ['APP_ENV']='development'
from fastapi import FastAPI
from fastapi.testclient import TestClient
from db.session import get_session
from security.auth import get_current_active_user
import importlib
from pathlib import Path
for model_path in Path('backend/models').glob('*.py'):
    if model_path.name != '__init__.py': importlib.import_module('models.'+model_path.stem)
from models.enums import UserRole
from api.routes import instantdm_webhook, social, email_drip, leads, auth, curator
from services.business_evidence import read_business
from services.lead_creation import create_manual_lead

results=[]
def record(key, actual, expected):
    results.append({'id':key,'actual':actual,'expected':expected,'defect_observed':actual != expected})
class Session:
    def __init__(self,row=None): self.rows=[];self.row=row;self.statements=[]
    def add(self,row):
        if getattr(row,'id',None) is None:row.id=uuid4()
        row.created_at=row.updated_at=datetime.now(UTC)
        self.rows.append(row)
    async def commit(self):pass
    async def refresh(self,row):pass
    async def flush(self):pass
    async def execute(self,statement):
        self.statements.append(str(statement))
        return SimpleNamespace(scalar_one_or_none=lambda:self.row)
    async def scalars(self,statement):return SimpleNamespace(all=lambda:[])
    async def scalar(self,statement):return self.row

def app_for(router,session,reviewer=False):
    app=FastAPI();app.include_router(router,prefix='/api')
    async def database():yield session
    app.dependency_overrides[get_session]=database
    if reviewer:app.dependency_overrides[get_current_active_user]=lambda:SimpleNamespace(id=uuid4(),role=UserRole.reviewer)
    return app

session=Session()
client=TestClient(app_for(instantdm_webhook.router,session))
payload={'contact':{'name':'Synthetic'},'messages':[{'text':'I owe 1000 dollars'}]}
response=client.post('/api/instantdm',json=payload)
record('D01',response.status_code,401)
record('D02',response.json()['address_detected'],None)
client.post('/api/instantdm',json=payload)
record('D03',len(session.rows),1)

session=Session()
client=TestClient(app_for(social.router,session,reviewer=True))
record('D04',client.post('/api',json={'content':'Synthetic','status':'posted'}).status_code,403)
record('D05',session.rows[0].status,'draft_pending_verified_publication')

row=SimpleNamespace(id=uuid4(),lead_id=None,email='synthetic@example.invalid',full_name='Synthetic',sequence='nurture',step=0,status='active',next_send_at=datetime.now(UTC),last_sent_at=None,source='audit',created_at=datetime.now(UTC))
session=Session(row)
asyncio.run(email_drip.advance_drip(row.id,session))
record('D06',row.last_sent_at is not None,False)

row=SimpleNamespace(id=uuid4(),full_name='Synthetic',phone=None,email=None,lead_status=SimpleNamespace(value='new'),lead_source=None,ai_score=None,notes=None,follow_up_at=None,address=None,city=None,state=None,last_contacted_at=None,property_id=None,assigned_user_id=None,created_at=datetime.now(UTC),updated_at=datetime.now(UTC),deleted_at=datetime.now(UTC))
session=Session(row)
returned=asyncio.run(leads.get_lead(row.id,session))
record('D07',{'returned_deleted_lead':returned['id']==str(row.id),'soft_delete_predicate':'leads.deleted_at IS NULL' in session.statements[0]}, {'returned_deleted_lead':False,'soft_delete_predicate':True})

session=Session()
payload={'full_name':'Synthetic','phone':None,'email':None,'address':'Synthetic address','city':'Stockton','state':'CA','lead_source':'direct','source_record_id':'same-provider-record'}
asyncio.run(create_manual_lead(session,payload,'operator-one'))
asyncio.run(create_manual_lead(session,payload,'operator-two'))
record('D08',len({x.metadata_['manual_create_key'] for x in session.rows}),1)

row=SimpleNamespace(metadata_={'business_evidence':{'observed_at':datetime.now(UTC).isoformat(),'snapshot':{'valuation':{'point_cents':10000000}}}})
try:asyncio.run(read_business(Session(row),uuid4()));error=None
except Exception as exc:error=type(exc).__name__
record('D09',error,None)

fake=SimpleNamespace(__aenter__=None)
client=MagicMock();client.get=AsyncMock(return_value=SimpleNamespace(text='synthetic-private-service-data'))
client.__aenter__=AsyncMock(return_value=client);client.__aexit__=AsyncMock(return_value=False)
with patch.object(curator.httpx,'AsyncClient',return_value=client):
    value=asyncio.run(curator._fetch_url_content('http://127.0.0.1:9999/internal'))
    record('D10',{'private_url_requested':client.get.call_count,'returned_private_preview':bool(value)}, {'private_url_requested':0,'returned_private_preview':False})
with patch.dict(os.environ,{'ANTHROPIC_API_KEY':''}):
    variants=asyncio.run(curator._call_claude('Synthetic'))
    record('D11',any('we just closed' in item for item in variants),False)

async def refresh_race():
    from security.auth import create_refresh_token
    barrier=asyncio.Event()
    class Redis:
        def __init__(self):self.checks=0;self.used=set()
        async def exists(self,key):
            answer=key in self.used
            self.checks+=1
            if self.checks==2:barrier.set()
            await barrier.wait()
            return answer
        async def setex(self,key,ttl,value):self.used.add(key)
    redis=Redis()
    token=create_refresh_token(str(uuid4()))
    answers=await asyncio.gather(auth.refresh(auth.RefreshRequest(refresh_token=token),redis),auth.refresh(auth.RefreshRequest(refresh_token=token),redis))
    return len(answers)
record('D12',asyncio.run(refresh_race()),1)
from services.business_evidence import validate_snapshot
import hashlib
external='synthetic-external-lead'
snapshot={'schema_version':1,'property_id':'synthetic-property','valuation':{'lead_id':external,'status':'ready_advisory','method':'evidence_adjusted_sales_comparison','purpose':'after_repair','as_of':datetime.now(UTC).date().isoformat(),'comparable_count':3,'supported_low_cents':10000000,'point_cents':11000000,'supported_high_cents':12000000,'quote_authorized':False,'offer_authorized':False},'comparables':[{'sale_id':f'sale-{i}','source_ref':'synthetic-source','sale_price_cents':None,'adjusted_value_cents':None,'closed_on':None} for i in range(3)],'offers':[],'appointment':{'at':None,'status':None},'quote_authorized':False,'offer_authorized':False}
body={'lead_id':external,'snapshot':snapshot,'revision':hashlib.sha256(json.dumps(snapshot,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'occurred_at':datetime.now(UTC).isoformat()}
try:validate_snapshot(body);accepted=True
except Exception:accepted=False
record('D13',accepted,False)

from services.voice_ingest import resolve_lead
row=SimpleNamespace(id=uuid4(),deleted_at=None,phone=None,full_name='Unverified seller')
class Existing(Session):
    async def scalars(self,statement):return SimpleNamespace(all=lambda:[row])
asyncio.run(resolve_lead(Existing(),{'lead_id':'external','phone':'+12095550123','lead_name':'Synthetic Known Seller'}))
record('D14',{'phone':row.phone,'full_name':row.full_name},{'phone':'+12095550123','full_name':'Synthetic Known Seller'})

print(json.dumps({'suite':'Dashboard merged-source isolated defect probes','limits':'Synthetic auth, database and HTTP adapters; no provider actions or real SQL/concurrency certification','results':results},indent=2))
