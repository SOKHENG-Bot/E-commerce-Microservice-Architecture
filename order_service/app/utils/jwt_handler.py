"""
JWT Handler for Order Service

Provides JWT token encoding/decoding functionality for authentication.
Follows the same patterns as other microservices for consistency.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from pydantic import BaseModel


class TokenData(BaseModel):
    """Token data model for decoded JWT tokens"""

    user_id: str
    email: str
    username: str
    roles: list[str] = []
    permissions: list[str] = []
    expires_at: datetime


class JWTHandler:
    """
    JWT token handler for encoding and decoding tokens.

    Provides secure token creation and validation with configurable
    secret key and algorithm.
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize JWT handler with secret key and algorithm.

        Args:
            secret_key: Secret key for token signing
            algorithm: JWT algorithm (default: HS256)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm

    def encode_token(
        self, payload: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Encode payload into JWT token.

        Args:
            payload: Token payload data
            expires_delta: Token expiration time (default: 30 minutes)

        Returns:
            Encoded JWT token string
        """
        to_encode = payload.copy()

        # Set expiration time
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=30)

        # Add standard claims
        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc).timestamp(),
                "type": "access",
            }
        )

        # Encode and return token
        token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str) -> TokenData:
        """
        Decode and validate JWT token.

        Args:
            token: JWT token string

        Returns:
            TokenData object with decoded payload

        Raises:
            ValueError: If token is invalid, expired, or malformed
        """
        try:
            # Decode token
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Extract required fields
            user_id = payload.get("user_id")
            exp = payload.get("exp")

            if not user_id or not exp:
                raise ValueError("Invalid token payload: missing user_id or exp")

            # Return token data
            return TokenData(
                user_id=str(user_id),
                email=payload.get("email", ""),
                username=payload.get("username", ""),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                expires_at=datetime.fromtimestamp(exp, tz=timezone.utc),
            )

        except ExpiredSignatureError:
            raise ValueError("Token has expired")
        except JWTError as e:
            raise ValueError(f"Token validation failed: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error during token decoding: {e}")
