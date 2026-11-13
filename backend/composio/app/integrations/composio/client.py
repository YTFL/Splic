"""Composio SDK Client Manager.

Handles client lifecycle, environment validation, and safe error handling.
"""

import logging
from typing import Any, Dict, Optional
from app.config import Settings, get_settings

logger = logging.getLogger("composio.client")


class ComposioClientManager:
    """Manages the Composio SDK client lifecycle and health checks."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self._client: Optional[Any] = None
        self._is_mock: bool = False
        self._init_error: Optional[str] = None

    def get_client(self) -> Any:
        """Retrieve the initialized Composio client or raise a descriptive error."""
        if self._client is not None:
            return self._client

        if not self.settings.is_composio_configured:
            self._init_error = (
                "COMPOSIO_API_KEY is missing or invalid. "
                f"Please configure COMPOSIO_API_KEY in the root environment file: '{self.settings.root_env_file}'."
            )
            logger.warning(self._init_error)
            raise ValueError(self._init_error)

        try:
            # Attempt to import official Composio SDK (v3)
            from composio import Composio
            self._client = Composio(api_key=self.settings.COMPOSIO_API_KEY)
            self._init_error = None
            logger.info("Composio SDK client initialized successfully.")
            return self._client
        except ImportError:
            try:
                # Fallback check for legacy composio_core
                from composio_core import ComposioToolSet
                self._client = ComposioToolSet(api_key=self.settings.COMPOSIO_API_KEY)
                self._init_error = None
                logger.info("Composio legacy ToolSet initialized successfully.")
                return self._client
            except ImportError as exc:
                self._init_error = (
                    "Composio SDK is not installed in the current environment. "
                    "Install via: pip install composio or pip install composio-core."
                )
                logger.error(f"{self._init_error} (error: {exc})")
                raise RuntimeError(self._init_error) from exc
        except Exception as exc:
            self._init_error = f"Failed to initialize Composio client: {str(exc)}"
            logger.error(self._init_error)
            raise RuntimeError(self._init_error) from exc

    def set_mock_client(self, mock_client: Any) -> None:
        """Inject a mock client for automated testing."""
        self._client = mock_client
        self._is_mock = True
        self._init_error = None
        logger.debug("Injected mock Composio client for testing.")

    def reset(self) -> None:
        """Reset internal client state."""
        self._client = None
        self._is_mock = False
        self._init_error = None

    def get_health_status(self) -> Dict[str, Any]:
        """Return diagnostic health information about the Composio SDK integration."""
        is_configured = self.settings.is_composio_configured
        status = "HEALTHY" if (is_configured and not self._init_error) else "UNCONFIGURED"

        sdk_available = False
        try:
            import composio  # noqa: F401
            sdk_available = True
        except ImportError:
            sdk_available = False

        return {
            "status": "MOCK" if self._is_mock else status,
            "is_configured": is_configured,
            "sdk_installed": sdk_available,
            "is_mock": self._is_mock,
            "error": self._init_error,
        }


# Global singleton instance
_client_manager: Optional[ComposioClientManager] = None


def get_composio_client_manager() -> ComposioClientManager:
    """Retrieve the global client manager singleton."""
    global _client_manager
    if _client_manager is None:
        _client_manager = ComposioClientManager()
    return _client_manager


def get_composio_client() -> Any:
    """Convenience getter to obtain the active Composio client instance."""
    return get_composio_client_manager().get_client()

