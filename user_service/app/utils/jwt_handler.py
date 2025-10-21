from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from pydantic import BaseModel


class TokenData(BaseModel):
    """Data model for decoded JWT token information."""

    user_id: str
    email: str
    username: str
    roles: list[str] = []
    permissions: list[str] = []
    expires_at: datetime


class JWTHandler:
    """Utility class for handling JWT encoding and decoding."""

    def __init__(self, secret_key: str, algorithm: str):
        self.secret_key = secret_key
        self.algorithm = algorithm

    def encode_token(
        self, payload: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """Encode a JWT token with the given payload and expiration."""

        to_encode = payload.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=30)
        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc).timestamp(),
                "type": "access",
            }
        )
        token = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return token

    def decode_token(self, token: str) -> TokenData:
        """Decode and validate a JWT token, returning the token data."""

        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id = payload.get("user_id")
            exp = payload.get("exp")
            if not user_id or not exp:
                raise ValueError("Invalid token payload")

            return TokenData(
                user_id=str(user_id),
                email=payload.get("email") or "",
                username=payload.get("username") or "",
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                expires_at=datetime.fromtimestamp(exp),
            )
        except ExpiredSignatureError:
            raise ValueError("Token has expired")
        except JWTError as e:
            raise ValueError(f"Token validation failed: {e}")
