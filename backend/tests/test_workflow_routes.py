"""
HTTP-level tests for workflow route error handling.

Verifies TransitionError and NotFoundError are mapped to correct HTTP status codes.
All runtime calls are mocked — no DB required.
"""

import uuid
from unittest.mock import AsyncMock, patch

from models.enums import WorkflowStatus
from workflows.transitions import TransitionError

_WF_ID = uuid.uuid4()
_ERR = TransitionError(_WF_ID, WorkflowStatus.completed, WorkflowStatus.paused, "terminal")


def _mock_runtime(method: str, side_effect: Exception):
    """Patch WorkflowRuntime in the routes module."""
    return patch(
        "api.routes.workflows.WorkflowRuntime",
        **{f"return_value.{method}": AsyncMock(side_effect=side_effect)},
    )


def _mock_recovery(side_effect: Exception):
    return patch(
        "api.routes.workflows.WorkflowRecovery",
        **{"return_value.resume_failed": AsyncMock(side_effect=side_effect)},
    )


class TestTransitionError409:
    def test_pause_invalid_transition_returns_409(self, client):
        with _mock_runtime("pause", _ERR):
            resp = client.post(f"/api/v1/workflows/{_WF_ID}/pause")
        assert resp.status_code == 409

    def test_resume_invalid_transition_returns_409(self, client):
        with _mock_runtime("resume", _ERR):
            resp = client.post(f"/api/v1/workflows/{_WF_ID}/resume")
        assert resp.status_code == 409

    def test_complete_invalid_transition_returns_409(self, client):
        with _mock_runtime("complete", _ERR):
            resp = client.post(f"/api/v1/workflows/{_WF_ID}/complete")
        assert resp.status_code == 409

    def test_cancel_invalid_transition_returns_409(self, client):
        with _mock_runtime("cancel", _ERR):
            resp = client.post(f"/api/v1/workflows/{_WF_ID}/cancel")
        assert resp.status_code == 409

    def test_recover_invalid_transition_returns_409(self, client):
        with _mock_recovery(_ERR):
            resp = client.post(f"/api/v1/workflows/{_WF_ID}/recover")
        assert resp.status_code == 409

    def test_409_body_contains_detail(self, client):
        with _mock_runtime("pause", _ERR):
            resp = client.post(f"/api/v1/workflows/{_WF_ID}/pause")
        assert resp.status_code == 409
        assert "detail" in resp.json()
