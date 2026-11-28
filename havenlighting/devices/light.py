from typing import Dict, Any
import logging
from ..models import LightData
from ..config import COMMAND_API_BASE, LIGHT_COMMAND, LIGHT_PARAMS, LIGHT_STATE
from ..credentials import Credentials
from ..exceptions import ApiError

logger = logging.getLogger(__name__)

class Light:
    """Represents a Haven light device."""

    def __init__(self, credentials: Credentials, location_id: int, light_id: int, data: Dict[str, Any]) -> None:
        self._credentials = credentials
        self.location_id = location_id
        # The LightAndZones/OrderedList endpoint reports pattern speed as
        # "patternSpeed" (no "Id" suffix), identifies each entry by "id"
        # (not "lightId"), and can return zone entries (isZone). Unlike the
        # older Location/InformationSummaryWithAllZonesGroup payload.
        self._data = LightData(
            light_id=int(data["lightId"]) if "lightId" in data else int(data["id"]),
            name=data["name"],
            status=data.get("lightingStatusId", LIGHT_STATE["OFF"]),
            brightness=data.get("lightBrightnessId", LIGHT_PARAMS["BRIGHTNESS"]),
            color=data.get("colorId", LIGHT_PARAMS["COLOR"]),
            pattern_speed=data.get(
                "patternSpeed", data.get("patternSpeedId", LIGHT_PARAMS["PATTERN_SPEED"])
            ),
            is_zone=bool(data.get("isZone", False)),
        )
        logger.debug("Initialized %s: %s (ID: %d)",
                     "Zone" if self._data.is_zone else "Light", self.name, self.id)

    @property
    def id(self) -> int:
        return self._data.light_id

    @property
    def name(self) -> str:
        return self._data.name

    @property
    def is_on(self) -> bool:
        return self._data.status == LIGHT_STATE["ON"]

    @property
    def brightness(self) -> int:
        """Brightness on Haven's 0-10 scale."""
        return self._data.brightness

    def turn_on(self, brightness: int | None = None) -> None:
        """Turn the light on, optionally setting brightness (0-10 scale).

        The v2/Light/CommandV1 endpoint carries the requested state in the
        payload itself: lightingStatusId 2 = on, lightBrightnessId 1-10 = the
        new level, 63 = keep the current one.
        """
        logger.debug("Turning on light: %s (ID: %d)", self.name, self.id)
        self._send_command(LIGHT_STATE["ON"], brightness)
        self._data.status = LIGHT_STATE["ON"]
        if brightness is not None:
            self._data.brightness = brightness
        logger.info("Light turned on successfully: %s", self.name)

    def turn_off(self) -> None:
        """Turn the light off."""
        logger.debug("Turning off light: %s (ID: %d)", self.name, self.id)
        self._send_command(LIGHT_STATE["OFF"])
        self._data.status = LIGHT_STATE["OFF"]
        logger.info("Light turned off successfully: %s", self.name)

    def set_brightness(self, brightness: int) -> None:
        """Set brightness (0-10 scale) without changing on/off state."""
        if not 0 <= brightness <= 10:
            raise ValueError(f"Brightness must be 0-10 on Haven's scale, got {brightness}")
        logger.debug("Setting brightness of light %s (ID: %d) to %d", self.name, self.id, brightness)
        self._send_command(LIGHT_COMMAND["KEEP_SAME"], brightness)
        self._data.brightness = brightness
        logger.info("Brightness of light %s set to %d", self.name, brightness)

    def _send_command(self, lighting_status_id: int, brightness: int | None = None) -> None:
        """Send a state command via the v2/Light/CommandV1 endpoint.

        Endpoint and payload shape reverse-engineered from the Haven
        Lighting Android app v2.5.67 (LightsService.sendLightCommand +
        LightCommandBuilder/LightCommand): POST to
        v2/Light/CommandV1?locationId={locationId} with locationId,
        selectedLightIds, selectedZoneIds, lightingStatusId,
        lightBrightnessId, lightColorId and patternSpeedId, where 63 means
        "keep the current value". The API answers with {"success": true}.
        """
        payload = {
            "locationId": self.location_id,
            "selectedLightIds": [] if self._data.is_zone else [self.id],
            "selectedZoneIds": [self.id] if self._data.is_zone else [],
            "lightingStatusId": lighting_status_id,
            "lightBrightnessId": (
                LIGHT_COMMAND["KEEP_SAME"] if brightness is None else brightness
            ),
            "lightColorId": LIGHT_COMMAND["KEEP_SAME"],
            "patternSpeedId": LIGHT_COMMAND["KEEP_SAME"],
        }
        response = self._credentials.make_request(
            "POST",
            f"/v2/Light/CommandV1?locationId={self.location_id}",
            json=payload,
            base_url=COMMAND_API_BASE,
        )
        if not (isinstance(response, dict) and response.get("success")):
            raise ApiError(f"Command for light {self.id} failed: {response!r}")
