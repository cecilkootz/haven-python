from typing import Dict, Any, Optional
import logging
from ..models import LocationData
from .light import Light
from .scene import SCENE_TYPE_BOTH, Scene
from ..credentials import Credentials
from ..exceptions import ApiError

logger = logging.getLogger(__name__)

class Location:
    """
    Represents a Haven location with its associated lights.

    Attributes:
        credentials: Credentials object for API requests
        location_id: Unique identifier for the location
        name: Location name
    """

    def __init__(self, credentials: Credentials, location_id: int, data: Optional[Dict[str, Any]] = None) -> None:
        self._credentials = credentials
        self._location_id = location_id
        self._data = LocationData(
            location_id=location_id,
            name=data.get("name", "")
        ) if data else None
        self._lights: Dict[str, Light] = {}
        logger.debug("Initialized Location: %s (ID: %d)", self.name, location_id)

    @property
    def id(self) -> int:
        """Get location ID."""
        return self._location_id

    @property
    def name(self) -> str:
        """Get location name."""
        return self._data.name if self._data else ""

    @classmethod
    def discover(cls, credentials: Credentials) -> Dict[int, 'Location']:
        """
        Discover the authenticated user's default location.

        Only the account's default location is returned — `/user/GetUserInfo/`
        doesn't expose the other locations a multi-location account might
        have (the old pre-2025 API did, via a since-decommissioned endpoint).
        Revisit this if a verified capture ever turns up the 2025 equivalent.

        Args:
            credentials: Authenticated credentials object

        Returns:
            Dictionary of location_id to Location objects

        Raises:
            AuthenticationError: If not authenticated
            ApiError: If API request fails or the response is missing the
                expected default location
        """
        response = credentials.make_request("GET", "/user/GetUserInfo/")

        if "defaultLocationId" not in response:
            raise ApiError("GetUserInfo response is missing defaultLocationId")

        location_id = int(response["defaultLocationId"])
        owner_name = f"{response.get('firstName', '')} {response.get('lastName', '')}".strip()
        return {
            location_id: cls(credentials, location_id, {"name": owner_name})
        }

    def get_lights(self) -> Dict[str, Light]:
        """Get all lights and zones for this location, keyed by ``Light.key``.

        Lights and zones have separate id spaces (``lightId`` vs a zone's
        ``id``), so a zone and a light can share a number; keying by the
        raw id let one silently overwrite the other. Keys are
        ``"light_<id>"`` / ``"zone_<id>"`` (see ``Light.key``).

        Uses the same endpoint as the Haven Lighting Android app
        (v2.5.67 LocationsService.getLocationLightZones):
        GET LightAndZones/OrderedList/{location_id}, which answers with
        {"lights": [...], "zones": [...]} (app-side extractLights maps
        r0.lights and r0.zones). The older
        Location/InformationSummaryWithAllZonesGroup endpoint still resolves
        but no longer reports a usable "lights" array, which made
        discover_locations find a location with zero lights.
        """
        logger.debug("Fetching lights for location: %s (ID: %d)", self.name, self._location_id)

        try:
            response = self._credentials.make_request(
                "GET",
                f"/LightAndZones/OrderedList/{self._location_id}"
            )

            lights = self._extract_lights(response)

            if self._data and isinstance(response, dict) and response.get("name"):
                self._data.name = response["name"]

            self._lights = {}
            for light_data in lights:
                # Skip lights the user has hidden in the app; the app does
                # not show them in the light list either (isHidden field).
                if light_data.get("isHidden"):
                    continue
                light_id = int(
                    light_data["lightId"] if "lightId" in light_data else light_data["id"]
                )
                light = Light(
                    self._credentials,
                    self._location_id,
                    light_id,
                    light_data
                )
                self._lights[light.key] = light
            logger.debug("Found %d lights for location: %s", len(self._lights), self.name)
        except Exception as e:
            logger.debug("Failed to fetch lights for location %d: %s", self._location_id, e)
            raise

        return self._lights

    def _extract_lights(self, response: Any) -> list[dict[str, Any]]:
        """Pull the lights array out of the OrderedList response.

        The Android app (v2.5.67) reads response.data.lights directly, but
        the live API may wrap or flatten the payload. Accept the known
        shapes; for anything else, fail with a message that names the
        actual shape so the log pinpoints it in one attempt:

        - {"lights": [...]}                          the app's shape
        - {"data": {"lights": [...]}}                a wrapped envelope
        - [{lightId/isZone...}, ...]                 a flat ordered list
          (zone entries carry zoneId instead of lightId and are skipped)
        - {}                                         an empty body
        """
        if isinstance(response, dict):
            if isinstance(response.get("lights"), list):
                return response["lights"]
            if isinstance(response.get("data"), dict):
                inner = response["data"]
                if isinstance(inner.get("lights"), list):
                    return inner["lights"]
                raise ApiError(
                    "unexpected LightAndZones/OrderedList response: dict with keys "
                    f"{sorted(response.keys())}, data keys "
                    f"{sorted(inner.keys())}"
                )
            raise ApiError(
                "unexpected LightAndZones/OrderedList response: dict with keys "
                f"{sorted(response.keys())}"
            )
        if isinstance(response, list):
            # Live-verified shape: a flat ordered list whose entries carry
            # "id" (zones) or "lightId" (individual lights).
            return [
                item for item in response
                if isinstance(item, dict) and ("lightId" in item or "id" in item)
            ]
        raise ApiError(
            "unexpected LightAndZones/OrderedList response: "
            f"{type(response).__name__} ({response!r:.200})"
        )

    def get_scenes(self) -> Dict[int, "Scene"]:
        """List the location's saved scenes (static and playground).

        GET Scene/UserScenesByLocation/?locationId={id}&sceneType=BOTH on
        the residential API (app v2.5.67 ScenesService.getScenesByLocation
        + mapScene). The response body is a flat list of scene items.
        """
        response = self._credentials.make_request(
            "GET",
            f"/Scene/UserScenesByLocation/?locationId={self._location_id}"
            f"&sceneType={SCENE_TYPE_BOTH}",
        )
        if isinstance(response, dict):
            # tolerate a wrapped envelope; the app maps response.data
            # (the axios body) directly, so a bare list is the expected form
            items = response.get("scenes", response.get("data", response))
        else:
            items = response
        if not isinstance(items, list):
            raise ApiError(
                "unexpected Scene/UserScenesByLocation response: "
                f"{type(response).__name__}"
            )
        scenes: Dict[int, Scene] = {}
        for item in items:
            scene = Scene(self._credentials, self._location_id, item)
            scenes[scene.id] = scene
        logger.debug("Found %d scenes for location: %s", len(scenes), self.name)
        return scenes
