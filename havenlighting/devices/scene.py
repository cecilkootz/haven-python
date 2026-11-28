"""Haven scene device."""
from typing import Any, Dict

import logging

from ..credentials import Credentials
from ..exceptions import ApiError

logger = logging.getLogger(__name__)

# The app's SceneType enum (both static scenes and playground light shows)
SCENE_TYPE_BOTH = "BOTH"


class Scene:
    """A saved Haven scene (a stored light/zone state snapshot).

    Listing and execution were reverse-engineered from the Haven Lighting
    Android app v2.5.67 (ScenesService): scenes are listed via
    GET Scene/UserScenesByLocation/?locationId={id}&sceneType=BOTH and
    executed via POST Commands/Scene/Execute/?sceneId={id}; both on the
    residential API. Item shape from the app's mapScene: {id|sceneId,
    name, photoUrl, preferedScene, isPlayGroundScene}.
    """

    def __init__(self, credentials: Credentials, location_id: int, data: Dict[str, Any]) -> None:
        self._credentials = credentials
        self.location_id = location_id
        self.id = int(data["id"]) if "id" in data else int(data["sceneId"])
        self.name = data["name"]
        self.photo_url = data.get("photoUrl")
        self.is_playground = bool(data.get("isPlayGroundScene", False))
        logger.debug("Initialized Scene: %s (ID: %d)", self.name, self.id)

    def activate(self) -> None:
        """Apply the scene (the app's executeScenById).

        The API answers {"success": true} (the app's validateResponseAPI
        check), which is the only success signal.
        """
        response = self._credentials.make_request(
            "POST",
            f"/Commands/Scene/Execute/?sceneId={self.id}",
            json={},
        )
        if not (isinstance(response, dict) and response.get("success")):
            raise ApiError(f"Executing scene {self.id} ({self.name}) failed: {response!r}")
        logger.info("Scene activated: %s (ID: %d)", self.name, self.id)
