"""Connection management module for Composio OAuth flows and connected accounts."""

import logging
import uuid
from typing import Any, Dict, List, Optional
from app.config import get_settings
from .client import ComposioClientManager, get_composio_client_manager
from .sessions import SessionManager
from app.schemas.account import ConnectedAccountSummary, AccountDetailResponse
from app.schemas.connection import ConnectionInitiationResponse, ConnectionStatusResponse

logger = logging.getLogger("composio.connections")


class ConnectionManager:
    """Manages initiating OAuth links, checking status, and managing accounts."""

    def __init__(
        self,
        client_manager: Optional[ComposioClientManager] = None,
        session_manager: Optional[SessionManager] = None
    ):
        self.client_manager = client_manager or get_composio_client_manager()
        self.session_manager = session_manager or SessionManager(self.client_manager)
        self.settings = get_settings()

    def initiate_connection(
        self,
        toolkit: str,
        user_id: str,
        redirect_url: Optional[str] = None,
        additional_params: Optional[Dict[str, Any]] = None
    ) -> ConnectionInitiationResponse:
        """Initiate OAuth authentication link for a user and toolkit (Instagram or YouTube).
        
        Args:
            toolkit: Target toolkit name (e.g. 'instagram', 'youtube')
            user_id: User identifier
            redirect_url: Frontend callback URL to redirect to after OAuth consent
            additional_params: Optional extra parameters (e.g. scopes)
        """
        effective_redirect_url = redirect_url or self.settings.OAUTH_REDIRECT_URL
        client = self.client_manager.get_client()

        # If mock client is injected with initiate_connection, prioritize it for test determinism
        if hasattr(client, "initiate_connection") and getattr(self.client_manager, "_is_mock", False):
            res = client.initiate_connection(toolkit=toolkit, user_id=user_id, redirect_url=effective_redirect_url)
            return ConnectionInitiationResponse(
                connection_request_id=getattr(res, "connection_request_id", f"req_{uuid.uuid4().hex[:12]}"),
                toolkit=toolkit,
                redirect_url=getattr(res, "redirect_url", "https://mock.composio.dev/auth"),
                status="INITIATED",
                user_id=user_id,
            )

        # Composio v3 SDK: Use connected_accounts.link() or toolkits.authorize()
        try:
            if hasattr(client, "connected_accounts") and hasattr(client.connected_accounts, "link"):
                auth_config_id = toolkit
                if hasattr(client, "auth_configs") and hasattr(client.auth_configs, "list"):
                    try:
                        auth_configs = client.auth_configs.list()
                        items = getattr(auth_configs, "items", [])
                        for item in items:
                            item_toolkit = getattr(item, "toolkit", None)
                            slug = getattr(item_toolkit, "slug", "") if item_toolkit else ""
                            if slug == toolkit or getattr(item, "name", "").lower().startswith(toolkit):
                                auth_config_id = item.id
                                break
                        else:
                            if hasattr(client.auth_configs, "create"):
                                new_ac = client.auth_configs.create(
                                    toolkit=toolkit,
                                    options={
                                        "type": "use_composio_managed_auth",
                                        "name": f"{toolkit.capitalize()} Managed Auth",
                                    }
                                )
                                auth_config_id = new_ac.id
                    except Exception as ac_err:
                        logger.debug(f"Auth config lookup/creation fallback: {ac_err}")
                elif hasattr(client, "toolkits") and hasattr(client.toolkits, "_get_auth_config_id"):
                    try:
                        auth_config_id = client.toolkits._get_auth_config_id(toolkit=toolkit)
                    except Exception:
                        pass

                req = client.connected_accounts.link(
                    user_id=user_id,
                    auth_config_id=auth_config_id,
                    callback_url=effective_redirect_url,
                )
                req_id = getattr(req, "id", f"req_{uuid.uuid4().hex[:12]}")
                auth_url = getattr(req, "redirect_url", getattr(req, "url", ""))
                return ConnectionInitiationResponse(
                    connection_request_id=str(req_id),
                    toolkit=toolkit,
                    redirect_url=str(auth_url),
                    status="INITIATED",
                    user_id=user_id,
                )
        except Exception as exc:
            logger.debug(f"Direct connected_accounts.link failed: {exc}")
            exc_str = str(exc)
            if "AuthenticationError" in type(exc).__name__ or "401" in exc_str:
                raise RuntimeError(f"Composio API authentication failed: {exc_str}") from exc

        # Fallback to toolkits.authorize()
        try:
            if hasattr(client, "toolkits") and hasattr(client.toolkits, "authorize"):
                req = client.toolkits.authorize(user_id=user_id, toolkit=toolkit)
                req_id = getattr(req, "id", f"req_{uuid.uuid4().hex[:12]}")
                auth_url = getattr(req, "redirect_url", getattr(req, "url", ""))
                return ConnectionInitiationResponse(
                    connection_request_id=str(req_id),
                    toolkit=toolkit,
                    redirect_url=str(auth_url),
                    status="INITIATED",
                    user_id=user_id,
                )
        except Exception as exc:
            logger.debug(f"toolkits.authorize failed: {exc}")
            exc_str = str(exc)
            if "AuthenticationError" in type(exc).__name__ or "401" in exc_str:
                raise RuntimeError(f"Composio API authentication failed: {exc_str}") from exc

        # Fallback to session.authorize()
        try:
            session = self.session_manager.get_or_create_session(user_id=user_id, toolkits=[toolkit])
            if hasattr(session, "authorize"):
                auth_kwargs: Dict[str, Any] = {}
                if effective_redirect_url:
                    auth_kwargs["redirect_url"] = effective_redirect_url
                req = session.authorize(toolkit, **auth_kwargs)
                req_id = getattr(req, "id", f"req_{uuid.uuid4().hex[:12]}")
                auth_url = getattr(req, "redirect_url", getattr(req, "url", ""))
                return ConnectionInitiationResponse(
                    connection_request_id=req_id,
                    toolkit=toolkit,
                    redirect_url=auth_url,
                    status="INITIATED",
                    user_id=user_id,
                )
        except Exception as exc:
            logger.debug(f"session.authorize failed: {exc}")

        # Legacy composio-core: entity.initiate_connection()
        try:
            if hasattr(client, "get_entity"):
                entity = client.get_entity(id=user_id)
                req = entity.initiate_connection(app_name=toolkit, redirect_url=effective_redirect_url)
                req_id = getattr(req, "connection_id", getattr(req, "id", f"req_{uuid.uuid4().hex[:12]}"))
                auth_url = getattr(req, "redirect_url", getattr(req, "redirectUrl", ""))
                return ConnectionInitiationResponse(
                    connection_request_id=str(req_id),
                    toolkit=toolkit,
                    redirect_url=str(auth_url),
                    status="INITIATED",
                    user_id=user_id,
                )
        except Exception as exc:
            logger.error(f"Legacy entity.initiate_connection failed: {exc}")
            raise RuntimeError(f"Failed to initiate connection for toolkit '{toolkit}': {exc}") from exc

        # If mock client is injected with initiate_connection
        if hasattr(client, "initiate_connection"):
            res = client.initiate_connection(toolkit=toolkit, user_id=user_id, redirect_url=effective_redirect_url)
            return ConnectionInitiationResponse(
                connection_request_id=getattr(res, "connection_request_id", f"req_{uuid.uuid4().hex[:12]}"),
                toolkit=toolkit,
                redirect_url=getattr(res, "redirect_url", "https://mock.composio.dev/auth"),
                status="INITIATED",
                user_id=user_id,
            )

        raise RuntimeError(f"Unable to initiate OAuth connection for {toolkit}: No supported method found on client.")

    def list_connected_accounts(
        self,
        user_id: str,
        toolkit: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[ConnectedAccountSummary]:
        """List connected accounts belonging to a user, with optional toolkit/status filters."""
        client = self.client_manager.get_client()
        raw_accounts: List[Any] = []

        try:
            if hasattr(client, "connected_accounts") and hasattr(client.connected_accounts, "list"):
                filter_kwargs: Dict[str, Any] = {"user_ids": [user_id]}
                if status:
                    filter_kwargs["statuses"] = [status]
                res = client.connected_accounts.list(**filter_kwargs)
                if hasattr(res, "items") and not isinstance(res, (list, tuple, dict)):
                    raw_accounts = res.items
                elif isinstance(res, list):
                    raw_accounts = res
                else:
                    raw_accounts = getattr(res, "items", [])
            elif hasattr(client, "get_entity"):
                entity = client.get_entity(id=user_id)
                raw_accounts = entity.get_connections()
            elif hasattr(client, "get_connected_accounts"):
                raw_accounts = client.get_connected_accounts(user_id=user_id)
            elif hasattr(client, "list_accounts"):
                raw_accounts = client.list_accounts(user_id=user_id, toolkit=toolkit)
        except Exception as exc:
            logger.error(f"Failed to query connected accounts from Composio: {exc}")
            raise RuntimeError(f"Error fetching connected accounts: {exc}") from exc

        results: List[ConnectedAccountSummary] = []
        for item in raw_accounts:
            acc = self._sanitize_account(item, user_id=user_id)
            if acc:
                if toolkit and acc.toolkit.lower() != toolkit.lower():
                    continue
                results.append(acc)

        return results

    def get_account_detail(self, account_id: str, user_id: str) -> AccountDetailResponse:
        """Fetch details of a single connected account and verify ownership."""
        client = self.client_manager.get_client()
        raw_account: Any = None

        try:
            if hasattr(client, "connected_accounts") and hasattr(client.connected_accounts, "get"):
                raw_account = client.connected_accounts.get(account_id)
            elif hasattr(client, "get_connection"):
                raw_account = client.get_connection(account_id)
            elif hasattr(client, "get_account"):
                raw_account = client.get_account(account_id=account_id)
        except Exception as exc:
            logger.error(f"Failed to fetch account {account_id}: {exc}")
            raise KeyError(f"Connected account '{account_id}' not found.") from exc

        if not raw_account:
            raise KeyError(f"Connected account '{account_id}' not found.")

        # Check ownership
        owner_id = self._extract_attr(raw_account, ["user_id", "userId", "entity_id"], default="")
        if owner_id and owner_id != user_id:
            logger.warning(f"Forbidden access: User '{user_id}' requested account '{account_id}' owned by '{owner_id}'.")
            raise PermissionError(f"Account '{account_id}' does not belong to user '{user_id}'.")

        summary = self._sanitize_account(raw_account, user_id=user_id)
        if not summary:
            raise ValueError(f"Failed to parse account data for '{account_id}'.")

        # Extract safe public metadata (excluding tokens/secrets)
        safe_meta = self._extract_safe_metadata(raw_account)

        return AccountDetailResponse(
            id=summary.id,
            toolkit=summary.toolkit,
            status=summary.status,
            user_id=user_id,
            account_name=summary.account_name,
            account_handle=summary.account_handle,
            is_active=summary.is_active,
            created_at=summary.created_at,
            metadata=safe_meta,
        )

    def disconnect_account(self, account_id: str, user_id: str) -> bool:
        """Disconnect and revoke a connected account, verifying user ownership first."""
        # Check ownership first
        self.get_account_detail(account_id=account_id, user_id=user_id)

        client = self.client_manager.get_client()
        try:
            if hasattr(client, "connected_accounts") and hasattr(client.connected_accounts, "delete"):
                client.connected_accounts.delete(account_id)
                return True
            elif hasattr(client, "connected_accounts") and hasattr(client.connected_accounts, "disconnect"):
                client.connected_accounts.disconnect(account_id)
                return True
            elif hasattr(client, "disconnect"):
                client.disconnect(account_id)
                return True
            elif hasattr(client, "delete_account"):
                client.delete_account(account_id)
                return True
        except Exception as exc:
            logger.error(f"Failed to disconnect account {account_id}: {exc}")
            raise RuntimeError(f"Failed to disconnect account '{account_id}': {exc}") from exc

        return True

    def check_connection_status(self, toolkit: str, user_id: str) -> ConnectionStatusResponse:
        """Check if an active connection exists for the specified toolkit and user."""
        accounts = self.list_connected_accounts(user_id=user_id, toolkit=toolkit)
        active_accounts = [acc for acc in accounts if acc.is_active and acc.status.upper() in ["ACTIVE", "CONNECTED"]]

        if active_accounts:
            target = active_accounts[0]
            return ConnectionStatusResponse(
                connection_id=target.id,
                toolkit=toolkit,
                status=target.status,
                user_id=user_id,
                is_active=True,
                message=f"Active connection exists for {toolkit}."
            )

        return ConnectionStatusResponse(
            connection_id=None,
            toolkit=toolkit,
            status="NOT_CONNECTED",
            user_id=user_id,
            is_active=False,
            message=f"No active connection found for {toolkit}."
        )

    def _sanitize_account(self, raw_item: Any, user_id: str) -> Optional[ConnectedAccountSummary]:
        """Convert raw Composio SDK account object or dict into a safe ConnectedAccountSummary."""
        if raw_item is None:
            return None

        account_id = self._extract_attr(raw_item, ["id", "connection_id", "connectionId", "uuid"], default="")
        if not account_id:
            return None

        # Extract toolkit slug
        toolkit_raw = self._extract_attr(raw_item, ["toolkit", "appName", "app", "app_name"], default="unknown")
        if hasattr(toolkit_raw, "slug"):
            toolkit = toolkit_raw.slug
        elif isinstance(toolkit_raw, str):
            toolkit = toolkit_raw
        else:
            toolkit = str(toolkit_raw)

        raw_status = self._extract_attr(raw_item, ["status", "state"], default="UNKNOWN").upper()
        is_active = raw_status in ["ACTIVE", "CONNECTED", "READY"]

        account_name = self._extract_attr(raw_item, ["name", "account_name", "accountName", "displayName"])
        account_handle = self._extract_attr(raw_item, ["handle", "account_handle", "username", "channelTitle"])
        created_at = self._extract_attr(raw_item, ["created_at", "createdAt", "timestamp"])

        return ConnectedAccountSummary(
            id=str(account_id),
            toolkit=toolkit.lower(),
            status=raw_status,
            user_id=user_id,
            account_name=str(account_name) if account_name else None,
            account_handle=str(account_handle) if account_handle else None,
            created_at=str(created_at) if created_at else None,
            is_active=is_active,
        )

    def _extract_safe_metadata(self, raw_item: Any) -> Dict[str, Any]:
        """Extract public metadata while filtering out secret keys and tokens."""
        raw_meta = self._extract_attr(raw_item, ["metadata", "profile", "params"], default={})
        if not isinstance(raw_meta, dict):
            return {}

        sensitive_keywords = ["token", "secret", "password", "key", "auth", "credential", "bearer"]
        safe_dict = {}
        for k, v in raw_meta.items():
            if any(sens in k.lower() for sens in sensitive_keywords):
                continue
            safe_dict[k] = v
        return safe_dict

    def _extract_attr(self, obj: Any, candidates: List[str], default: Any = None) -> Any:
        """Utility to safely extract an attribute from an object or dictionary."""
        if isinstance(obj, dict):
            for candidate in candidates:
                if candidate in obj and obj[candidate] is not None:
                    return obj[candidate]
            return default

        for candidate in candidates:
            if hasattr(obj, candidate):
                val = getattr(obj, candidate)
                if val is not None:
                    return val
        return default

