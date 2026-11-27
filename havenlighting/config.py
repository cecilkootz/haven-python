"""Configuration constants for Haven Lighting API."""

from typing import Final

# API Configuration
API_TIMEOUT: Final[int] = 30

# Light States
LIGHT_STATE: Final[dict] = {
    "OFF": 1,
    "ON": 2
}

# Default Light Parameters (brightness is 0-10 on Haven's scale)
LIGHT_PARAMS: Final[dict] = {
    "BRIGHTNESS": 10,
    "COLOR": 63,
    "PATTERN_SPEED": 63
}

# Command payload values (reverse-engineered from the Haven Lighting Android
# app v2.5.67, LightCommandBuilder/LightCommand: keepSame=63, lightOn=2,
# lightOff=1). Unchanged command aspects are sent as 63 ("keep same").
LIGHT_COMMAND: Final[dict] = {
    "KEEP_SAME": 63,
}

# API Configuration
API_BASE: Final[str] = "https://stg-api.havenlighting.com/api"
APP_SOURCE: Final[str] = "REACT_NATIVE"
APP_VERSION: Final[str] = "1.6" 