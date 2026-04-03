"""
Password hashing using bcrypt.
Paper applied: arXiv OAuth Token Security 2025
- bcrypt chosen for adaptive cost factor (resistant to brute force)
- verify_password is constant-time to prevent timing attacks
"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
