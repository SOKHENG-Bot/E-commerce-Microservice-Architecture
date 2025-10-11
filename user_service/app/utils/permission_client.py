"""
API Client for User Service Permissions
Other services should use this instead of importing shared permission enums.
This creates proper service boundaries and reduces coupling.
"""

from typing import List

import httpx


class PermissionClient:
    """Client for checking user permissions via User Service API"""

    def __init__(self, user_service_url: str, timeout: int = 30):
        self.base_url = user_service_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def check_user_permission(
        self, user_id: int, permission: str, token: str
    ) -> bool:
        """Check if user has specific permission"""
        headers = {"Authorization": f"Bearer {token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v1/users/{user_id}/permissions/{permission}",
            headers=headers,
        )
        return response.status_code == 200 and response.json().get(
            "has_permission", False
        )

    async def get_user_permissions(self, user_id: int, token: str) -> List[str]:
        """Get all permissions for a user"""
        headers = {"Authorization": f"Bearer {token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v1/users/{user_id}/permissions", headers=headers
        )
        if response.status_code == 200:
            return response.json().get("permissions", [])
        return []

    async def get_user_roles(self, user_id: int, token: str) -> List[str]:
        """Get all roles for a user"""
        headers = {"Authorization": f"Bearer {token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v1/users/{user_id}/roles", headers=headers
        )
        if response.status_code == 200:
            return response.json().get("roles", [])
        return []

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


# Usage example for other services:
#
# from .user_permission_client import PermissionClient
#
# async def check_admin_access(user_id: int, token: str) -> bool:
#     client = PermissionClient("http://user-service:8001")
#     try:
#         return await client.check_user_permission(user_id, "manage_system", token)
#     finally:
#         await client.close()
