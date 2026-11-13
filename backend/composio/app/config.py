"""Application configuration module using Pydantic Settings.

Loads environment variables exclusively from the project root .env.local file
using a deterministic path relative to this backend module location.
"""

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    from pydantic import BaseModel as BaseSettings  # type: ignore
    SettingsConfigDict = None  # type: ignore

logger = logging.getLogger("composio.config")

# Deterministically resolve the project root directory relative to this file:
# backend/composio/app/config.py -> app (1) -> composio (2) -> backend (3) -> root (4)
ROOT_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent.parent
ROOT_ENV_LOCAL_PATH = ROOT_PROJECT_DIR / ".env.local"

# Pre-load root .env.local into os.environ if present, avoiding CWD dependencies
try:
    from dotenv import load_dotenv
    if ROOT_ENV_LOCAL_PATH.is_file():
        load_dotenv(dotenv_path=ROOT_ENV_LOCAL_PATH, override=False)
except ImportError:
    pass


class Settings(BaseSettings):
    """Application settings loaded strictly from the root .env.local file."""

    # Composio Credentials
    COMPOSIO_API_KEY: Optional[str] = None

    # Firebase Admin SDK Authentication (loaded from root .env.local)
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_SERVICE_ACCOUNT_JSON: Optional[str] = None
    # Allowed clock drift (seconds, 0-60) when verifying Firebase ID tokens
    FIREBASE_CLOCK_SKEW_SECONDS: int = 10

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # CORS and Service URLs
    FRONTEND_URL: str = "http://localhost:3000,http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"

    # OAuth Redirect Flow
    OAUTH_REDIRECT_URL: Optional[str] = "http://localhost:3000/auth/callback"

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=str(ROOT_ENV_LOCAL_PATH),
            env_file_encoding="utf-8",
            extra="ignore",
            case_sensitive=True,
        )

    @property
    def root_env_file(self) -> Path:
        """Return the resolved absolute path to the root .env.local file."""
        return ROOT_ENV_LOCAL_PATH

    @property
    def is_root_env_present(self) -> bool:
        """Return True if the root .env.local file exists on disk."""
        return ROOT_ENV_LOCAL_PATH.is_file()

    @property
    def cors_origins(self) -> List[str]:
        """Parse comma-separated FRONTEND_URL string into an origins list."""
        if not self.FRONTEND_URL:
            return ["http://localhost:3000", "http://localhost:5173"]
        origins = [origin.strip() for origin in self.FRONTEND_URL.split(",") if origin.strip()]
        return origins or ["*"]

    @property
    def is_composio_configured(self) -> bool:
        """Check if a valid Composio API key is provided."""
        if not self.COMPOSIO_API_KEY:
            return False
        key = self.COMPOSIO_API_KEY.strip()
        return bool(key and key != "your_composio_api_key_here" and len(key) > 5)

    @property
    def is_firebase_configured(self) -> bool:
        """Check if Firebase project ID and service account JSON are configured."""
        return bool(
            self.FIREBASE_PROJECT_ID
            and self.FIREBASE_PROJECT_ID.strip()
            and self.FIREBASE_SERVICE_ACCOUNT_JSON
            and self.FIREBASE_SERVICE_ACCOUNT_JSON.strip()
        )

    def parse_and_validate_service_account(self) -> Dict[str, Any]:
        """Parse and validate FIREBASE_SERVICE_ACCOUNT_JSON safely.

        Returns:
            Parsed service account dictionary.

        Raises:
            ValueError: If credentials are missing, malformed, or mismatched.
        """
        if not self.FIREBASE_PROJECT_ID or not self.FIREBASE_PROJECT_ID.strip():
            raise ValueError(
                "FIREBASE_PROJECT_ID is not configured in the root .env.local file. "
                "Ensure FIREBASE_PROJECT_ID is defined and matches the service account project ID."
            )

        if not self.FIREBASE_SERVICE_ACCOUNT_JSON or not self.FIREBASE_SERVICE_ACCOUNT_JSON.strip():
            raise ValueError(
                "FIREBASE_SERVICE_ACCOUNT_JSON is not configured in the root .env.local file. "
                "Please provide the complete service account JSON as a single-line string."
            )

        raw_json = self.FIREBASE_SERVICE_ACCOUNT_JSON.strip()
        try:
            parsed = json.loads(raw_json)
        except Exception:
            raise ValueError(
                "FIREBASE_SERVICE_ACCOUNT_JSON in root .env.local contains invalid or malformed JSON."
            )

        if not isinstance(parsed, dict):
            raise ValueError(
                "FIREBASE_SERVICE_ACCOUNT_JSON must be a valid JSON object dictionary."
            )

        required_fields = ["type", "project_id", "private_key", "client_email"]
        missing_fields = [f for f in required_fields if not parsed.get(f)]
        if missing_fields:
            raise ValueError(
                f"FIREBASE_SERVICE_ACCOUNT_JSON is missing required fields: {', '.join(missing_fields)}."
            )

        # Ensure standard Google OAuth2 endpoints are present for google-auth / firebase-admin Certificate
        if not parsed.get("token_uri"):
            parsed["token_uri"] = "https://oauth2.googleapis.com/token"
        if not parsed.get("auth_uri"):
            parsed["auth_uri"] = "https://accounts.google.com/o/oauth2/auth"

        sa_project_id = str(parsed.get("project_id", "")).strip()
        if sa_project_id != self.FIREBASE_PROJECT_ID.strip():
            raise ValueError(
                f"FIREBASE_PROJECT_ID ('{self.FIREBASE_PROJECT_ID.strip()}') does not match "
                f"the project_id in FIREBASE_SERVICE_ACCOUNT_JSON ('{sa_project_id}')."
            )

        return parsed

    def validate_composio_credentials(self) -> None:
        """Validate Composio API credentials without exposing any secret values."""
        if not self.is_composio_configured:
            raise ValueError(
                "COMPOSIO_API_KEY is not configured or contains placeholder value. "
                f"Please define a valid COMPOSIO_API_KEY in the root environment file: '{ROOT_ENV_LOCAL_PATH}'."
            )

    def validate_firebase_credentials(self) -> None:
        """Validate Firebase project credentials without exposing sensitive details."""
        self.parse_and_validate_service_account()


@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
