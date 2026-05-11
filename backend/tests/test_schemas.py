
import pytest

from models.enums import (
    LeadStatus,
    UserRole,
    WorkflowType,
)
from schemas.lead import LeadCreate, LeadUpdate
from schemas.property import PropertyCreate
from schemas.user import UserCreate
from schemas.workflow import WorkflowCreate


def test_user_create_valid():
    u = UserCreate(email="test@example.com", password="secret")
    assert u.email == "test@example.com"
    assert u.role == UserRole.operator


def test_user_create_invalid_email():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="secret")


def test_lead_create_minimal():
    lead = LeadCreate(full_name="John Doe")
    assert lead.full_name == "John Doe"
    assert lead.phone is None


def test_lead_update_partial():
    update = LeadUpdate(lead_status=LeadStatus.qualified)
    assert update.lead_status == LeadStatus.qualified
    assert update.full_name is None


def test_property_create():
    p = PropertyCreate(address="123 Main St", city="Austin", state="TX")
    assert p.state == "TX"


def test_workflow_create():
    w = WorkflowCreate(workflow_type=WorkflowType.outreach)
    assert w.workflow_type == WorkflowType.outreach
    assert w.lead_id is None
