import pytest

from havenlighting.credentials import Credentials
from havenlighting.devices.location import Location
from havenlighting.exceptions import ApiError


def _ordered_list_response(lights, zones=None):
    """Shape returned by GET LightAndZones/OrderedList/{locationId}."""
    return {
        "locationId": 123,
        "name": "Test Location",
        "lights": lights,
        "zones": zones or [],
    }


def _light_data(light_id=456, **overrides):
    data = {
        "lightId": light_id,
        "name": f"Light {light_id}",
        "lightingStatusId": 1,
        "lightBrightnessId": 10,
        "colorId": 11,
        "patternSpeed": 0,
        "isHidden": False,
        "orderNumber": 1,
    }
    data.update(overrides)
    return data


@pytest.fixture
def location(mocker):
    credentials = mocker.Mock(spec=Credentials)
    return Location(credentials, location_id=123, data={"name": "Test Location"})


def test_get_lights_uses_ordered_list_endpoint(location):
    location._credentials.make_request.return_value = _ordered_list_response(
        [_light_data()]
    )

    lights = location.get_lights()

    location._credentials.make_request.assert_called_once_with(
        "GET", "/LightAndZones/OrderedList/123"
    )
    assert list(lights.keys()) == [456]
    assert lights[456].name == "Light 456"


def test_get_lights_skips_hidden_lights(location):
    location._credentials.make_request.return_value = _ordered_list_response(
        [_light_data(456), _light_data(789, isHidden=True)]
    )

    lights = location.get_lights()

    assert list(lights.keys()) == [456]


def test_get_lights_missing_lights_array_raises(location):
    location._credentials.make_request.return_value = {"zones": []}

    with pytest.raises(ApiError):
        location.get_lights()


def test_get_lights_updates_location_name(location):
    location._credentials.make_request.return_value = _ordered_list_response(
        [_light_data()], zones=[]
    ) | {"name": "Renamed Location"}

    location.get_lights()

    assert location.name == "Renamed Location"


def test_get_lights_parses_brightness_and_pattern_speed(location):
    location._credentials.make_request.return_value = _ordered_list_response(
        [_light_data(lightBrightnessId=5, patternSpeed=2)]
    )

    lights = location.get_lights()

    assert lights[456].brightness == 5
    assert not lights[456].is_on
