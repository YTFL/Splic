"""Authentication package for Firebase integration."""

from .firebase import (
    initialize_firebase_admin,
    verify_firebase_id_token,
    get_firebase_auth_manager,
    FirebaseAuthManager,
)

__all__ = [
    "initialize_firebase_admin",
    "verify_firebase_id_token",
    "get_firebase_auth_manager",
    "FirebaseAuthManager",
]
