import pytest

from havenlighting.credentials import Credentials
from havenlighting.devices.location import Location
from havenlighting.devices.scene import Scene
from havenlighting.exceptions import ApiError


@pytest.fixture
def location(mocker):
    credentials = mocker.Mock(spec=Credentials)
    return Location(credentials, location_id=123, data={"name": "Test Location"})


def _scene_data(scene_id=777, **overrides):
    data = {
        "id": scene_id,
        "name": f"Scene {scene_id}",
        "photoUrl": None,
        "preferedScene": False,
        "isPlayGroundScene": False,
    }
    data.update(overrides)
    return data


def test_get_scenes_uses_both_scene_type(location):
    location._credentials.make_request.return_value = [_scene_data()]

    scenes = location.get_scenes()

    location._credentials.make_request.assert_called_once_with(
        "GET", "/Scene/UserScenesByLocation/?locationId=123&sceneType=BOTH"
    )
    assert list(scenes.keys()) == [777]
    assert scenes[777].name == "Scene 777"


def test_get_scenes_accepts_scene_id_key(location):
    location._credentials.make_request.return_value = [
        {"sceneId": 888, "name": "App Scene"}
    ]

    scenes = location.get_scenes()

    assert scenes[888].name == "App Scene"


def test_get_scenes_wrapped_envelope(location):
    location._credentials.make_request.return_value = {
        "scenes": [_scene_data()]
    }

    scenes = location.get_scenes()

    assert list(scenes.keys()) == [777]


def test_scene_activate(location):
    location._credentials.make_request.return_value = [_scene_data()]
    scene = location.get_scenes()[777]
    location._credentials.make_request.reset_mock()
    location._credentials.make_request.return_value = {"success": True}

    scene.activate()

    location._credentials.make_request.assert_called_once_with(
        "POST", "/Commands/Scene/Execute/?sceneId=777", json={}
    )


def test_scene_activate_failure_raises(location):
    location._credentials.make_request.return_value = [_scene_data()]
    scene = location.get_scenes()[777]
    location._credentials.make_request.return_value = {"success": False}

    with pytest.raises(ApiError):
        scene.activate()
