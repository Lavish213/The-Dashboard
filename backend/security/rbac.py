import enum

from models.enums import UserRole


class Permission(enum.StrEnum):
    # Lead permissions
    LEADS_READ = "leads:read"
    LEADS_WRITE = "leads:write"
    LEADS_DELETE = "leads:delete"
    # Property permissions
    PROPERTIES_READ = "properties:read"
    PROPERTIES_WRITE = "properties:write"
    # Workflow permissions
    WORKFLOWS_READ = "workflows:read"
    WORKFLOWS_WRITE = "workflows:write"
    WORKFLOWS_MANAGE = "workflows:manage"
    # Approval permissions
    APPROVALS_READ = "approvals:read"
    APPROVALS_RESOLVE = "approvals:resolve"
    # Transcript permissions
    TRANSCRIPTS_READ = "transcripts:read"
    # Call permissions
    CALLS_READ = "calls:read"
    CALLS_INITIATE = "calls:initiate"
    # AI permissions
    AI_READ = "ai:read"
    # Admin permissions
    USERS_READ = "users:read"
    USERS_MANAGE = "users:manage"
    AUDIT_READ = "audit:read"
    SETTINGS_MANAGE = "settings:manage"


ROLE_PERMISSIONS: dict[UserRole, frozenset[Permission]] = {
    UserRole.admin: frozenset(Permission),
    UserRole.operator: frozenset({
        Permission.LEADS_READ,
        Permission.LEADS_WRITE,
        Permission.PROPERTIES_READ,
        Permission.PROPERTIES_WRITE,
        Permission.WORKFLOWS_READ,
        Permission.WORKFLOWS_WRITE,
        Permission.APPROVALS_READ,
        Permission.TRANSCRIPTS_READ,
        Permission.CALLS_READ,
        Permission.CALLS_INITIATE,
        Permission.AI_READ,
    }),
    UserRole.reviewer: frozenset({
        Permission.LEADS_READ,
        Permission.PROPERTIES_READ,
        Permission.WORKFLOWS_READ,
        Permission.APPROVALS_READ,
        Permission.APPROVALS_RESOLVE,
        Permission.TRANSCRIPTS_READ,
        Permission.CALLS_READ,
        Permission.AI_READ,
        Permission.AUDIT_READ,
    }),
}


def has_permission(role: UserRole, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, frozenset())
