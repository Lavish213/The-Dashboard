from fastapi import APIRouter, Depends, HTTPException, Query

from api.routes.source_review import source_request
from security.permissions import require_permission
from security.rbac import Permission

router = APIRouter(dependencies=[Depends(require_permission(Permission.LEADS_READ))])

OVERVIEW_FIELDS = (
    'schema_version', 'generated_at', 'graded_leads', 'contactable_leads', 'briefed_leads',
    'valuation_ready_leads', 'newest_grade_at', 'newest_grade_age_seconds', 'oldest_grade_age_seconds',
    'blocked_leads', 'economics_unknown_leads',
    'by_readiness', 'by_grade', 'by_evidence_confidence', 'by_lockout_class', 'by_valuation_verification',
)
DEAL_FIELDS = (
    'lead_id', 'address', 'city', 'distress_score', 'grade', 'readiness', 'evidence_confidence',
    'economics_state', 'limit_method', 'profit_at_asking_cents', 'arv_point_cents', 'asking_price_cents', 'purchase_limit_cents',
    'headroom_cents', 'headroom_bps', 'valuation_status', 'valuation_verification', 'comparable_count', 'blocked_count',
    'lockout_class', 'next_action', 'graded_at',
)
READINESS = ('HOT_BUY', 'WATCH_LIST', 'ARCHIVED', 'UNGRADED')


def _deal(value):
    if not isinstance(value, dict):
        return None
    readiness = value.get('readiness')
    if readiness not in READINESS or not isinstance(value.get('lead_id'), str):
        return None
    return {field: value.get(field) for field in DEAL_FIELDS}


@router.get('/insights')
async def insights(limit: int = Query(default=25, ge=1, le=100)):
    report = await source_request('GET', '/api/bob/insights?limit=' + str(limit))
    if report.get('schema_version') != 1:
        raise HTTPException(503, 'Unsupported Bob opportunity report')
    authority = report.get('authority')
    if not isinstance(authority, dict) or authority.get('quote_authorized') is not False or authority.get('offer_authorized') is not False:
        raise HTTPException(503, 'Bob opportunity report withheld: unexpected offer authority')
    deals = report.get('deals')
    if not isinstance(deals, list):
        raise HTTPException(503, 'Bob opportunity report withheld: malformed deal list')
    return {
        **{field: report.get(field) for field in OVERVIEW_FIELDS},
        'deals': [deal for deal in (_deal(row) for row in deals) if deal is not None],
        'grading_basis': authority.get('grading_basis'),
        'quote_authorized': False,
        'offer_authorized': False,
    }
