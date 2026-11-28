import logging
from typing import Dict, Any, Optional
from .credentials import Credentials
from .devices.light import Light
from .devices.location import Location
from .exceptions import AuthenticationError, ApiError
from .logging import setup_logging

logger = logging.getLogger(__name__)

class HavenClient:
    """Main client for interacting with Haven Lighting devices."""
    
    def __init__(self, log_level: Optional[int] = None, log_file: Optional[str] = None) -> None:
        """
        Initialize the Haven Lighting client.

        Logging is left to the application unless asked for: pass
        ``log_level`` (and optionally ``log_file``) to have the client
        install its own console/file handlers, as a standalone script would.

        Args:
            log_level: Logging level to configure, or None (the default) to
                leave logging configuration to the application
            log_file: Optional file path for logging output
        """
        if log_level is not None or log_file is not None:
            setup_logging(logging.INFO if log_level is None else log_level, log_file)
        self._credentials = Credentials()
        self._locations: Dict[int, Location] = {}
        self._lights: Dict[int, Light] = {}
        logger.debug("Initialized HavenClient")

    def authenticate(self, email: str, password: str) -> bool:
        """
        Authenticate with the Haven Lighting service.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            bool: True if authentication successful, False if Haven rejected
                the credentials

        Raises:
            ApiError: If Haven could not be reached or failed (network
                error, timeout, 5xx, WAF block) — the credentials were not
                checked, so the caller should retry rather than re-prompt
        """
        try:
            authenticated = self._credentials.authenticate(email, password)
        except ApiError as e:
            logger.warning("Could not reach Haven to authenticate: %s", e)
            raise
        if not authenticated:
            logger.warning("Haven rejected the account credentials")
        return authenticated

    def discover_locations(self) -> Dict[int, Location]:
        """Discover all available locations."""
        if not self._credentials:
            raise AuthenticationError("Not authenticated")
            
        locations = Location.discover(self._credentials)
        self._locations.update(locations)
        return self._locations 