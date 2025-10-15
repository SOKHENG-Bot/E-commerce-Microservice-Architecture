"""
Permission API endpoints for User Service
Provides endpoints for other services to check user permissions via API calls.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, status

from user_service.app.api.dependencies import get_current_user, get_permission_service
from user_service.app.core.access_permissions import PermissionEnum, RoleEnum
from user_service.app.models.user import User
from user_service.app.schemas.user import (
    AvailablePermissionsResponse,
    PermissionCheckResponse,
    UserPermissionsResponse,
    UserRolesResponse,
)
from user_service.app.services.permission_service import PermissionService

router = APIRouter(prefix="/permissions")


@router.get(
    "/{user_id}/permissions/{permission}", response_model=PermissionCheckResponse
)
async def check_user_permission(
    user_id: int = Path(..., description="User ID to check permissions for"),
    permission: str = Path(..., description="Permission to check"),
    permission_service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(get_current_user),
) -> PermissionCheckResponse:
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

        return PermissionCheckResponse(
            user_id=user_id,
            permission=permission,
            has_permission=has_permission,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking permission: {str(e)}",
        )


@router.get("/{user_id}/permissions", response_model=UserPermissionsResponse)
async def get_user_permissions(
    user_id: int = Path(..., description="User ID to get permissions for"),
    permission_service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(get_current_user),
) -> UserPermissionsResponse:
    """
    Get all permissions for a user.
    Used by other services to get complete permission list.
    """
    try:
        permissions = await permission_service.get_user_permissions(user_id)

        return UserPermissionsResponse(
            user_id=user_id,
            permissions=permissions,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting permissions: {str(e)}",
        )


@router.get("/{user_id}/roles", response_model=UserRolesResponse)
async def get_user_roles(
    user_id: int = Path(..., description="User ID to get roles for"),
    permission_service: PermissionService = Depends(get_permission_service),
    current_user: User = Depends(get_current_user),
) -> UserRolesResponse:
    """
    Get all roles for a user.
    Used by other services to get user roles.
    """
    try:
        roles = await permission_service.get_user_roles(user_id)

        return UserRolesResponse(
            user_id=user_id,
            roles=roles,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting roles: {str(e)}",
        )


@router.get("/available", response_model=AvailablePermissionsResponse)
async def get_available_permissions(
    current_user: User = Depends(get_current_user),
) -> AvailablePermissionsResponse:
    """
    Get all available permissions in the system.
    Useful for other services to know what permissions exist.
    """
    return AvailablePermissionsResponse(
        permissions=[p.value for p in PermissionEnum],
        roles=[r.value for r in RoleEnum],
    )
