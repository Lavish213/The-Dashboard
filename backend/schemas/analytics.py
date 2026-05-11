from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_leads: int
    active_workflows: int
    pending_approvals: int
    calls_today: int
    leads_by_status: dict[str, int]
    workflows_by_status: dict[str, int]
