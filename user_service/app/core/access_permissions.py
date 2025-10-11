"""
User Service Permission and Role Enums
Other services should access permissions via API endpoints, not direct imports.
"""

from enum import Enum


class RoleEnum(str, Enum):
    """User role enumeration - owned by user service"""

    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


class PermissionEnum(str, Enum):
    """User permission enumeration - owned by user service"""

    # User management permissions
    CREATE_USER = "create_user"
    READ_USER = "read_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"

    # Profile management permissions
    CREATE_PROFILE = "create_profile"
    READ_PROFILE = "read_profile"
    UPDATE_PROFILE = "update_profile"
    DELETE_PROFILE = "delete_profile"

    # Administrative permissions
    MANAGE_ROLES = "manage_roles"
    MANAGE_PERMISSIONS = "manage_permissions"
    BULK_OPERATIONS = "bulk_operations"

    # System permissions
    READ_SYSTEM_INFO = "read_system_info"
    MANAGE_SYSTEM = "manage_system"
