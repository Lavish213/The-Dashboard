from models.enums import UserRole
from security.rbac import ROLE_PERMISSIONS, Permission, has_permission


def test_admin_has_all_permissions():
    for perm in Permission:
        assert has_permission(UserRole.admin, perm), f"admin missing {perm}"


def test_operator_permissions():
    assert has_permission(UserRole.operator, Permission.LEADS_READ)
    assert has_permission(UserRole.operator, Permission.LEADS_WRITE)
    assert has_permission(UserRole.operator, Permission.CALLS_INITIATE)
    # operator cannot manage users
    assert not has_permission(UserRole.operator, Permission.USERS_MANAGE)
    assert not has_permission(UserRole.operator, Permission.AUDIT_READ)
    assert not has_permission(UserRole.operator, Permission.SETTINGS_MANAGE)


def test_reviewer_permissions():
    assert has_permission(UserRole.reviewer, Permission.LEADS_READ)
    assert has_permission(UserRole.reviewer, Permission.APPROVALS_RESOLVE)
    assert has_permission(UserRole.reviewer, Permission.AUDIT_READ)
    # reviewer cannot write leads or initiate calls
    assert not has_permission(UserRole.reviewer, Permission.LEADS_WRITE)
    assert not has_permission(UserRole.reviewer, Permission.CALLS_INITIATE)
    assert not has_permission(UserRole.reviewer, Permission.USERS_MANAGE)


def test_all_roles_present():
    for role in UserRole:
        assert role in ROLE_PERMISSIONS, f"Role {role} missing from ROLE_PERMISSIONS"


def test_has_permission_unknown_role_returns_false():
    # Simulates a future role not in the matrix — should fail safe
    class FakeRole:
        pass
    result = has_permission(FakeRole(), Permission.LEADS_READ)
    assert result is False
