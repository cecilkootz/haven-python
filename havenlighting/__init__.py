import logging as _logging

from .client import HavenClient
from .devices.light import Light
from .devices.location import Location
from .exceptions import ApiError, AuthenticationError, DeviceError, HavenException

# Libraries leave logging configuration to the application.
_logging.getLogger(__name__).addHandler(_logging.NullHandler())

__version__ = "0.4.0"
__all__ = [
    "HavenClient",
    "Light",
    "Location",
    "HavenException",
    "ApiError",
    "AuthenticationError",
    "DeviceError",
] 