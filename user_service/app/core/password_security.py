from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityUtils:
    """Password hashing and verification utilities using bcrypt"""

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Hash a plain text password using bcrypt"""
        return pwd_context.hash(plain_password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
