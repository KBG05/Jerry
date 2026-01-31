"""Encryption utilities for sensitive data."""

from cryptography.fernet import Fernet

from app.core.config import get_settings


def get_cipher() -> Fernet:
    """Get Fernet cipher instance."""
    settings = get_settings()
    return Fernet(settings.encryption_key.encode())


def encrypt_token(token: str) -> str:
    """
    Encrypt a token using Fernet encryption.
    
    Args:
        token: Plain text token to encrypt
        
    Returns:
        Encrypted token as string
    """
    cipher = get_cipher()
    encrypted_bytes = cipher.encrypt(token.encode())
    return encrypted_bytes.decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt an encrypted token.
    
    Args:
        encrypted_token: Encrypted token string
        
    Returns:
        Decrypted plain text token
    """
    cipher = get_cipher()
    decrypted_bytes = cipher.decrypt(encrypted_token.encode())
    return decrypted_bytes.decode()
