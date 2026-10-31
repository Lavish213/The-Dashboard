import csv
import io
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from security.permissions import require_permission
from security.rbac import Permission
from services.source_commands import destination

router = APIRouter(dependencies=[Depends(require_permission(Permission.LEADS_READ))])


@router.get('/connections')
async def connections(session: AsyncSession = Depends(get_session)):
    from services.connection_status import connection_status
    return await connection_status(session, source_request)


async def source_request(method, path, body=None):
    url, secret, _ = destination()
    try:
        async with httpx.AsyncClient(timeout=300 if path == '/api/operations/rentcast/price' else 10 if path.startswith('/api/operations/integration?') else 5, follow_redirects=False) as client:
            response = await client.request(
                method,
                url + path,
                json=body,
                headers={"X-Source-Command-Secret": secret},
            )
        if not response.is_success:
            raise HTTPException(
                409 if response.status_code in {409, 422} else 503,
                "Source review unavailable or rejected",
            )
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid source response")
        return data
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(503, "Source review unavailable") from error


@router.get("/candidates")
async def candidates(page: int = Query(1, ge=1, le=100000)):
    return await source_request("GET", "/api/operations/candidates?page=" + str(page))


class CandidateReview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(dismissed|linked_to_reviewed_lead)$")
    reason: str = Field(min_length=10, max_length=1000)
    fingerprint: str = Field(min_length=64, max_length=64)
    lead_id: UUID | None = None


@router.post("/candidates/{identity}/review")
async def review(
    identity: UUID,
    body: CandidateReview,
    actor=Depends(require_permission(Permission.LEADS_WRITE)),
):
    return await source_request(
        "POST",
        "/api/operations/candidates/" + str(identity) + "/review",
        {**body.model_dump(mode="json"), "actor_id": str(actor.id)},
    )


DATA_QUALITY_FIELDS = (
    'schema_version', 'generated_at', 'properties', 'properties_with_comp_arv', 'properties_needing_comps',
    'assessed_based_arv', 'comps_rows', 'leads', 'leads_with_phone', 'leads_with_bob_brief', 'by_distress_type',
)
RENTCAST_HARD_CAP = 50


def rentcast_budget(value):
    if not isinstance(value, dict):
        return None
    used = value.get('used')
    if isinstance(used, bool) or not isinstance(used, int) or used < 0:
        return None
    return {'used': used, 'hard_cap': RENTCAST_HARD_CAP, 'window_days': 31}


@router.get('/data-quality')
async def data_quality():
    report = await source_request('GET', '/api/health/data-quality')
    if report.get('schema_version') != 1:
        raise HTTPException(503, 'Unsupported data quality report')
    return {**{field: report.get(field) for field in DATA_QUALITY_FIELDS}, 'rentcast': rentcast_budget(report.get('rentcast'))}


@router.get('/rentcast/usage')
async def rentcast_usage():
    usage = await source_request('GET', '/api/operations/rentcast/usage')
    budget = rentcast_budget(usage)
    if budget is None:
        raise HTTPException(503, 'RentCast usage unavailable')
    cap = usage.get('configured_cap')
    configured = cap if isinstance(cap, int) and not isinstance(cap, bool) and 0 <= cap <= RENTCAST_HARD_CAP else 0
    return {**budget, 'enabled': usage.get('enabled') is True, 'configured_cap': configured, 'remaining': max(0, min(configured, RENTCAST_HARD_CAP) - budget['used'])}


class RentcastPricing(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    limit: int = Field(ge=1, le=RENTCAST_HARD_CAP)


RENTCAST_RESULT_FIELDS = ('requested', 'priced', 'no_data', 'errors', 'comps_saved', 'stopped')


@router.post('/rentcast/price')
async def rentcast_price(body: RentcastPricing, actor=Depends(require_permission(Permission.SETTINGS_MANAGE))):
    result = await source_request('POST', '/api/operations/rentcast/price', {'limit': body.limit})
    return {**{field: result.get(field) for field in RENTCAST_RESULT_FIELDS}, 'usage': rentcast_budget(result.get('usage'))}


@router.get('/workflow-review')
async def workflows():
    health = await source_request('GET', '/api/health/workflow-recovery')
    queue = await source_request('GET', '/api/health/workflow-recovery/review')
    return {**health, **queue}


class Reconciliation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    decision: str = Field(pattern='^skipped$')
    reason: str = Field(min_length=10, max_length=1000)


@router.post('/workflow-review/{identity}/reconcile')
async def reconcile(identity: UUID, body: Reconciliation, actor=Depends(require_permission(Permission.LEADS_WRITE))):
    return await source_request('POST', '/api/health/workflow-recovery/' + str(identity) + '/reconcile', {**body.model_dump(), 'actor_id': str(actor.id)})


@router.get('/price-reviews', dependencies=[Depends(require_permission(Permission.APPROVALS_READ))])
async def price_reviews(page: int = Query(1, ge=1, le=100000)):
    return await source_request('GET', '/api/operations/price-reviews?page=' + str(page))


class PriceReviewDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: str = Field(pattern='^(approved|rejected)$')
    reason: str = Field(min_length=10, max_length=1000)
    fingerprint: str = Field(pattern='^[0-9a-f]{64}$')
    offer_low_cents: int | None = Field(default=None, strict=True, ge=100, le=10**14, multiple_of=100)
    offer_high_cents: int | None = Field(default=None, strict=True, ge=100, le=10**14, multiple_of=100)


@router.post('/price-reviews/{identity}/resolve')
async def resolve_price(identity: str, body: PriceReviewDecision, actor=Depends(require_permission(Permission.APPROVALS_RESOLVE))):
    if not 1 <= len(identity) <= 100 or any(character not in '0123456789abcdefABCDEF-' for character in identity):
        raise HTTPException(422, 'Valid source approval identity required')
    low, high = body.offer_low_cents, body.offer_high_cents
    if (body.status == 'approved' and (low is None or high is None or high < low)) or (body.status == 'rejected' and (low is not None or high is not None)) or len(body.reason.strip()) < 10:
        raise HTTPException(422, 'Explicit valid range and review reason required')
    result = await source_request('POST', '/api/operations/price-reviews/' + identity + '/resolve', {**body.model_dump(), 'actor_id': str(actor.id)})
    if type(result.get('schema_version')) is not int or result.get('schema_version') != 1 or result.get('persisted') is not True or result.get('approval_id') != identity or result.get('status') != body.status or result.get('action') != 'resolve_price_review':
        raise HTTPException(503, 'Source decision receipt not confirmed; refresh before retrying')
    return result


@router.get('/email-holds')
async def email_holds(page: int = Query(1, ge=1, le=100000)):
    return await source_request('GET', '/api/operations/email-holds?page=' + str(page))


class EmailResumption(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_id: UUID
    fingerprint: str = Field(pattern='^[0-9a-f]{64}$')
    reason: str = Field(min_length=10, max_length=1000)


@router.post('/email-holds/{lead_id}/resume', status_code=202)
async def resume_email(lead_id: UUID, body: EmailResumption, actor=Depends(require_permission(Permission.LEADS_WRITE))):
    if len(body.reason.strip()) < 10:
        raise HTTPException(422, 'Explicit reviewed reason required')
    result = await source_request('POST', '/api/operations/email-holds/' + str(lead_id) + '/resume', {**body.model_dump(mode='json'), 'actor_id': str(actor.id)})
    if type(result.get('schema_version')) is not int or result.get('schema_version') != 1 or result.get('persisted') is not True or result.get('request_id') != str(body.request_id) or result.get('lead_id') != str(lead_id) or result.get('state') not in {'pending','applied','requires_review'}:
        raise HTTPException(503, 'Resumption receipt not confirmed; refresh source review')
    return result


@router.get('/delivery')
async def delivery_receipts():
    data = await source_request('GET', '/api/operations/delivery')
    from services.delivery_evidence import validate_delivery_overview
    try:
        return validate_delivery_overview(data)
    except (ValueError, TypeError, KeyError) as error:
        raise HTTPException(503, 'Provider delivery evidence unavailable') from error


MAIL_COLUMNS = (
    'owner_name', 'mailing_address', 'mailing_city', 'mailing_state', 'mailing_zip',
    'property_address', 'property_city', 'property_zip', 'value', 'mao', 'value_source', 'distress_type', 'distress_score',
)
IMPORT_LIMIT = 10 * 1024 * 1024


def mail_cell(value):
    if value is None:
        return ''
    text = str(value).replace('\r', ' ').replace('\n', ' ')
    return "'" + text if text[:1] in ('=', '+', '-', '@', '\t') else text


def dollars(value):
    return value // 100 if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


@router.get('/mail-list.csv')
async def mail_list_csv(priced_only: bool = True, actor=Depends(require_permission(Permission.SETTINGS_MANAGE))):
    data = await source_request('GET', '/api/operations/mail-list?priced_only=' + ('true' if priced_only else 'false'))
    rows = data.get('rows')
    if data.get('schema_version') != 1 or not isinstance(rows, list):
        raise HTTPException(503, 'Mail list unavailable')
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(MAIL_COLUMNS)
    for row in rows:
        if not isinstance(row, dict):
            continue
        values = {**row, 'value': dollars(row.get('value_cents')), 'mao': dollars(row.get('mao_cents'))}
        writer.writerow([mail_cell(values.get(column)) for column in MAIL_COLUMNS])
    name = 'mail-list-priced.csv' if priced_only else 'mail-list-all.csv'
    return Response(buffer.getvalue(), media_type='text/csv; charset=utf-8', headers={'Content-Disposition': f'attachment; filename="{name}"', 'Cache-Control': 'no-store'})


@router.post('/import-csv')
async def import_csv(request: Request, actor=Depends(require_permission(Permission.SETTINGS_MANAGE))):
    body = await request.body()
    if not body or len(body) > IMPORT_LIMIT:
        raise HTTPException(400, 'CSV must be between 1 byte and 10MB')
    url, secret, _ = destination()
    try:
        async with httpx.AsyncClient(timeout=600, follow_redirects=False) as client:
            response = await client.post(url + '/api/operations/import-csv', files={'file': ('import.csv', body, 'text/csv')}, headers={'X-Source-Command-Secret': secret})
        if response.status_code == 400:
            raise HTTPException(400, 'CSV rejected')
        if not response.is_success:
            raise HTTPException(503, 'Import unavailable')
        data = response.json()
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(503, 'Import unavailable') from error
    fields = ('parsed', 'upserted', 'scored', 'leads_created', 'skipped_score', 'errors')
    if not isinstance(data, dict) or not all(isinstance(data.get(field), int) for field in fields):
        raise HTTPException(503, 'Import unavailable')
    return {field: data[field] for field in fields}
