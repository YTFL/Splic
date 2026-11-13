"""Firebase Admin SDK authentication and token verification module.

Ensures singleton Firebase Admin initialization, secure Bearer token verification,
revocation checking, and offline mock support for unit tests.
"""

import logging
import os
from typing import Any, Callable, Dict, Optional
from fastapi import HTTPException, status
from app.config import Settings, get_settings

logger = logging.getLogger("composio.auth.firebase")

# Global singleton instance
_firebase_auth_manager: Optional["FirebaseAuthManager"] = None


class FirebaseAuthManager:
    """Manages Firebase Admin SDK lifecycle and ID token verification."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._app: Optional[Any] = None
        self._mock_verifier: Optional[Callable[[str, bool], Dict[str, Any]]] = None
        self._is_initialized = False

    def initialize(self, raise_on_error: bool = False) -> None:
        """Initialize Firebase Admin SDK once using credentials parsed from root .env.local.

        Args:
            raise_on_error: If True, re-raises any credential parsing or initialization errors.
                           If False, logs the error safely without leaking secrets.
        """
        if self._is_initialized:
            return

        try:
            import firebase_admin
            from firebase_admin import credentials

            # Check if an existing Firebase app is already initialized
            try:
                self._app = firebase_admin.get_app()
                self._is_initialized = True
                logger.info("Reusing existing Firebase Admin app initialization.")
                return
            except ValueError:
                # No default app exists, proceed to initialize
                pass

            # Parse and validate the service account JSON directly from environment
            parsed_sa = self.settings.parse_and_validate_service_account()
            project_id = self.settings.FIREBASE_PROJECT_ID

            # Initialize Firebase Admin using credentials.Certificate(parsed_service_account)
            cred = credentials.Certificate(parsed_sa)
            self._app = firebase_admin.initialize_app(cred, options={"projectId": project_id})
            self._is_initialized = True
            logger.info(f"Firebase Admin initialized successfully for project '{project_id}'.")

        except ImportError:
            logger.warning(
                "firebase-admin library not installed. Live token verification will fail "
                "unless mock verifier is configured."
            )
            if raise_on_error:
                raise
        except Exception as exc:
            logger.error(f"Failed to initialize Firebase Admin SDK: {exc}")
            if raise_on_error:
                raise

    def verify_token(self, token: str, check_revoked: bool = True) -> Dict[str, Any]:
        """Verify a Firebase ID token.
        
        Args:
            token: Raw Bearer JWT token string.
            check_revoked: Whether to check if the token has been revoked by Firebase.
            
        Returns:
            Decoded token claims dictionary containing 'uid', 'email', etc.
            
        Raises:
            HTTPException: 401 Unauthorized for expired, revoked, or invalid tokens.
        """
        if not token or not token.strip():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Empty or missing Firebase authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 1. Use test mock verifier if injected (used for offline regression and auth tests)
        if self._mock_verifier is not None:
            return self._mock_verifier(token, check_revoked)

        # 2. Ensure Firebase Admin is initialized
        if not self._is_initialized:
            try:
                self.initialize(raise_on_error=True)
            except Exception as init_exc:
                logger.error(f"Cannot verify token: Firebase Admin initialization failed: {init_exc}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Firebase authentication service is not properly configured: {init_exc}",
                ) from init_exc

        # 3. Verify via official Firebase Admin SDK
        try:
            from firebase_admin import auth
            from firebase_admin.exceptions import FirebaseError

            decoded_claims = auth.verify_id_token(token, check_revoked=check_revoked)
            return decoded_claims

        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Firebase Admin SDK is not available on this server.",
            )
        except Exception as exc:
            # Inspect exact Firebase error types dynamically to avoid hard dependency at import time
            exc_name = type(exc).__name__
            exc_str = str(exc)

            if "RevokedIdTokenError" in exc_name or "revoked" in exc_str.lower():
                logger.warning(f"Firebase token revoked: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Firebase ID token has been revoked. Please sign in again.",
                    headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Token revoked\""},
                )
            elif "ExpiredIdTokenError" in exc_name or "expired" in exc_str.lower():
                logger.warning(f"Firebase token expired: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Firebase ID token has expired. Please refresh your token.",
                    headers={"WWW-Authenticate": "Bearer error=\"invalid_token\", error_description=\"Token expired\""},
                )
            elif "InvalidIdTokenError" in exc_name or "invalid" in exc_str.lower():
                logger.warning(f"Invalid Firebase token: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid Firebase ID token.",
                    headers={"WWW-Authenticate": "Bearer error=\"invalid_token\""},
                )
            elif "CertificateFetchError" in exc_name:
                logger.error(f"Certificate fetch error from Google auth servers: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to verify token: failed to reach Google authentication servers.",
                )
            elif isinstance(exc, ValueError):
                logger.warning(f"Malformed Firebase token: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Malformed Firebase ID token: {exc_str}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                logger.error(f"Unexpected error during Firebase token verification: {exc}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Could not validate credentials.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    def set_mock_verifier(self, verifier_func: Callable[[str, bool], Dict[str, Any]]) -> None:
        """Inject a mock verifier callable for testing."""
        self._mock_verifier = verifier_func

    def reset_mock_verifier(self) -> None:
        """Reset mock verifier to use live Firebase Admin SDK."""
        self._mock_verifier = None


def get_firebase_auth_manager() -> FirebaseAuthManager:
    """Retrieve or create the global FirebaseAuthManager singleton."""
    global _firebase_auth_manager
    if _firebase_auth_manager is None:
        _firebase_auth_manager = FirebaseAuthManager()
    return _firebase_auth_manager


def initialize_firebase_admin() -> None:
    """Convenience helper to initialize Firebase Admin SDK."""
    get_firebase_auth_manager().initialize()


def verify_firebase_id_token(token: str, check_revoked: bool = True) -> Dict[str, Any]:
    """Convenience helper to verify a Firebase ID token."""
    return get_firebase_auth_manager().verify_token(token, check_revoked=check_revoked)

