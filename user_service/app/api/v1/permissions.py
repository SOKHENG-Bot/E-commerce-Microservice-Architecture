"""
Permission API endpoints for User Service
Provides endpoints for other services to check user permissions via API calls.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Path, status

from user_service.app.api.dependencies import get_current_user, get_permission_service
from user_service.app.core.access_permissions import PermissionEnum, RoleEnum
from user_service.app.models.user import User
from user_service.app.services.permission_service import PermissionService

router = APIRouter(prefix="/permissions")


@router.get("/{user_id}/permissions/{permission}")
async def check_user_permission(
    user_id: int = Path(..., description="User ID to check permissions for"),
    permission: str = Path(..., description="Permission to check"),
    permission_service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Check if a user has a specific permission.
    Used by other services to verify user permissions.
    """
    try:
        # Validate permission exists
        if permission not in [p.value for p in PermissionEnum]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid permission: {permission}",
            )

        has_permission = await permission_service.has_permission(user_id, permission)

        return {
            "user_id": user_id,
            "permission": permission,
            "has_permission": has_permission,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking permission: {str(e)}",
        )


@router.get("/{user_id}/permissions")
async def get_user_permissions(
    user_id: int = Path(..., description="User ID to get permissions for"),
    permission_service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get all permissions for a user.
    Used by other services to get complete permission list.
    """
    try:
        permissions = await permission_service.get_user_permissions(user_id)

        return {
            "user_id": user_id,
            "permissions": permissions,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting permissions: {str(e)}",
        )


@router.get("/{user_id}/roles")
async def get_user_roles(
    user_id: int = Path(..., description="User ID to get roles for"),
    permission_service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get all roles for a user.
    Used by other services to get user roles.
    """
    try:
        roles = await permission_service.get_user_roles(user_id)

        return {
            "user_id": user_id,
            "roles": roles,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting roles: {str(e)}",
        )


@router.get("/available")
async def get_available_permissions(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get all available permissions in the system.
    Useful for other services to know what permissions exist.
    """
    return {
        "permissions": [p.value for p in PermissionEnum],
        "roles": [r.value for r in RoleEnum],
    }
