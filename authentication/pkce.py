# apps/authentication/pkce.py
import os
import hashlib
import base64
from django.core.cache import cache

def generate_code_verifier() -> str:
    """Cryptographically random verifier, URL-safe, 64 chars."""
    return base64.urlsafe_b64encode(os.urandom(48)).rstrip(b"=").decode()

def generate_code_challenge(verifier: str) -> str:
    """S256 challenge: BASE64URL(SHA256(verifier))."""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

# Store verifier server-side keyed by `state` (CSRF protection too)
PKCE_TTL = 300  # 5 minutes — must complete flow within this window

def store_pkce_state(state: str, verifier: str):
    cache.set(f"pkce:{state}", verifier, timeout=PKCE_TTL)

def pop_pkce_state(state: str) -> str | None:
    """Retrieve and immediately delete — single use."""
    verifier = cache.get(f"pkce:{state}")
    if verifier:
        cache.delete(f"pkce:{state}")
    return verifier