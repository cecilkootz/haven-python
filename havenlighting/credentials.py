from typing import Any, Dict, Optional
from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException
import logging
from .exceptions import AuthenticationError, ApiError
from .config import API_BASE, API_TIMEOUT, APP_SOURCE, APP_VERSION

logger = logging.getLogger(__name__)

# 4xx statuses that mean "Haven could not process this request right now"
# rather than "these credentials are wrong": 403 is Azure Front Door's WAF
# block (see CLAUDE.md), 408 a timeout, 429 rate limiting.
_TRANSIENT_CLIENT_ERRORS = frozenset({403, 408, 429})


def is_credential_rejection(error: ApiError) -> bool:
    """Whether an auth-endpoint ApiError means Haven rejected the credentials.

    A 4xx answer (other than the transient ones above) is Haven saying the
    request itself is wrong, which for login/refresh means the credentials.
    Transport errors (no status) and 5xx mean they were never checked.
    """
    code = error.code
    return code is not None and 400 <= code < 500 and code not in _TRANSIENT_CLIENT_ERRORS


class Credentials:
    """Handles authentication and request credentials."""

    def __init__(self):
        self._token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._user_id: Optional[int] = None
        # impersonate="chrome": Haven's Azure Front Door WAF blocks the TLS
        # fingerprint of plain requests/urllib3 (403 "request is blocked",
        # verified against real headers/UA too) but passes curl and browser
        # fingerprints. A Session (vs. a fresh request each call) also avoids
        # re-negotiating that fingerprint/TLS handshake on every API call.
        self._session = requests.Session(impersonate="chrome")
        logger.debug("Initialized Credentials")

    @property
    def is_authenticated(self) -> bool:
        return bool(self._token and self._user_id)

    def authenticate(self, email: str, password: str) -> bool:
        """Authenticate with the Haven Lighting service.

        Returns False when Haven rejects the credentials. Raises ApiError
        when the credentials could not be checked at all (network error,
        timeout, 5xx, WAF block), so callers can retry instead of
        treating an outage as a wrong password.
        """
        logger.debug("Attempting authentication")
        payload = {
            "username": email,
            "password": password,
        }

        try:
            response = self._make_request_internal(
                "POST",
                "/Auth/authenticate",
                json=payload,
                auth_required=False
            )
        except AuthenticationError as e:
            logger.warning("Authentication rejected: %s", e)
            return False
        except ApiError as e:
            if is_credential_rejection(e):
                logger.warning("Authentication rejected: %s", e)
                return False
            logger.warning("Authentication request failed: %s", e)
            raise

        if not isinstance(response, dict) or not response.get("token"):
            logger.warning("Authentication failed: no token in response")
            return False
        self._update_credentials(response)
        logger.debug("Authentication successful")
        return True

    def refresh_token(self) -> bool:
        """Refresh the authentication token.

        Returns False when Haven rejects the refresh token (the session is
        over and a fresh login is needed). Raises ApiError when the refresh
        could not be attempted (network error, timeout, 5xx).
        """
        if not self._refresh_token or not self._user_id:
            logger.debug("Cannot refresh token - missing refresh token or user ID")
            return False

        try:
            logger.debug("Attempting token refresh for user ID: %s", self._user_id)
            response = self._make_request_internal(
                "POST",
                "/Auth/refresh",
                json={
                    "refreshToken": self._refresh_token,
                    "userId": self._user_id
                },
                auth_required=False
            )
        except AuthenticationError as e:
            logger.info("Token refresh rejected: %s", e)
            return False
        except ApiError as e:
            if is_credential_rejection(e):
                logger.info("Token refresh rejected: %s", e)
                return False
            logger.warning("Token refresh request failed: %s", e)
            raise

        try:
            self._update_credentials(response)
        except ApiError as e:
            logger.warning("Token refresh failed: %s", e)
            return False
        logger.debug("Token refresh successful")
        return True

    def _update_credentials(self, data: Dict[str, Any]) -> None:
        """Update stored credentials from API response."""
        if not isinstance(data, dict):
            raise ApiError(f"Auth response is not an object: {type(data).__name__}")
        try:
            self._token = data["token"]
            self._refresh_token = data["refreshToken"]
            self._user_id = data["id"]
        except KeyError as e:
            raise ApiError(f"Auth response missing expected field: {e}")

    def make_request(
        self,
        method: str,
        path: str,
        auth_required: bool = True,
        timeout: int = API_TIMEOUT,
        base_url: str = API_BASE,
        **kwargs: Any
    ) -> Any:
        """Make an authenticated API request with automatic token refresh.

        base_url defaults to the residential API; commands must pass
        COMMAND_API_BASE (the legacy host the app's default client uses).
        """
        try:
            return self._make_request_internal(
                method=method,
                path=path,
                auth_required=auth_required,
                timeout=timeout,
                base_url=base_url,
                **kwargs
            )
        except AuthenticationError:
            logger.debug("Authentication error, attempting token refresh")
            if self.refresh_token():
                logger.debug("Token refresh successful, retrying request")
                return self._make_request_internal(
                    method=method,
                    path=path,
                    auth_required=auth_required,
                    timeout=timeout,
                    base_url=base_url,
                    **kwargs
                )
            logger.info("Token refresh rejected, unable to retry request")
            raise AuthenticationError("Token refresh failed")

    def _make_request_internal(
        self,
        method: str,
        path: str,
        auth_required: bool = True,
        timeout: int = API_TIMEOUT,
        base_url: str = API_BASE,
        **kwargs: Any
    ) -> Any:
        """Internal method for making API requests."""
        if auth_required and not self.is_authenticated:
            raise AuthenticationError("Authentication required")

        url = f"{base_url}{path}"

        headers = kwargs.pop("headers", {})
        headers.setdefault("Accept", "application/json")
        headers["app-haven-source"] = APP_SOURCE
        headers["app-haven-version"] = APP_VERSION
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        kwargs["headers"] = headers

        try:
            response = self._session.request(method, url, timeout=timeout, **kwargs)
        except RequestException as e:
            logger.debug("Request failed: %s", e)
            raise ApiError(f"Request failed: {e}") from e

        if response.status_code == 401:
            raise AuthenticationError("Received 401 Unauthorized response")

        if not response.ok:
            # _extract_error_message can legitimately return "" (e.g. a 404
            # with an empty body); fall back to the status code so callers
            # and logs never see an empty error string.
            raise ApiError(
                self._extract_error_message(response) or f"HTTP {response.status_code}",
                code=response.status_code,
            )

        if not response.content:
            return {}

        return response.json()

    @staticmethod
    def _extract_error_message(response: Any) -> str:
        """Build an error message from an application/problem+json body, if present."""
        try:
            error_data = response.json()
        except ValueError:
            return response.text

        message = error_data.get("title") or error_data.get("message") or response.text

        # ASP.NET validation errors: {"errors": {"Field": ["reason", ...]}}
        errors = error_data.get("errors")
        if isinstance(errors, dict) and errors:
            detail = "; ".join(
                f"{field}: {', '.join(reasons)}" for field, reasons in errors.items()
            )
            message = f"{message}: {detail}" if message else detail

        return message
