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
    assert list(lights.keys()) == ["light_456"]
    assert lights["light_456"].name == "Light 456"


def test_get_lights_skips_hidden_lights(location):
    location._credentials.make_request.return_value = _ordered_list_response(
        [_light_data(456), _light_data(789, isHidden=True)]
    )

    lights = location.get_lights()

    assert list(lights.keys()) == ["light_456"]


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

    assert lights["light_456"].brightness == 5
    assert not lights["light_456"].is_on


def test_get_lights_accepts_wrapped_envelope(location):
    location._credentials.make_request.return_value = {
        "data": {
            "lights": [_light_data()],
            "zones": [],
        }
    }

    lights = location.get_lights()

    assert list(lights.keys()) == ["light_456"]


def test_get_lights_accepts_flat_list(location):
    location._credentials.make_request.return_value = [
        _light_data(),
        {"zoneId": 99, "name": "A Zone", "isZone": True},
    ]

    lights = location.get_lights()

    # zone entries (zoneId, no lightId) are skipped
    assert list(lights.keys()) == ["light_456"]


def test_get_lights_unexpected_shape_names_the_keys(location):
    location._credentials.make_request.return_value = {"zones": [], "result": None}

    with pytest.raises(ApiError, match=r"keys \['result', 'zones'\]"):
        location.get_lights()


def test_get_lights_envelope_without_lights_names_both_key_sets(location):
    location._credentials.make_request.return_value = {"data": {"zones": []}}

    with pytest.raises(ApiError, match=r"data keys \['zones'\]"):
        location.get_lights()


def test_get_lights_flat_list_with_zone_entries(location):
    # Live-verified shape (2026-11-27): the OrderedList endpoint returns a
    # flat list whose entries are zones identified by "id", not "lightId".
    location._credentials.make_request.return_value = [
        {"id": 39288, "name": "Far Left Palm", "isZone": True,
         "lightingStatusId": 2, "lightBrightnessId": 10, "colorId": 11,
         "patternSpeed": 16, "isHidden": False},
        {"id": 49148, "name": "Drive Way", "isZone": True,
         "lightingStatusId": 2, "lightBrightnessId": 10, "colorId": 2,
         "patternSpeed": 16, "isHidden": False},
        "not-a-light",
    ]

    lights = location.get_lights()

    assert sorted(lights.keys()) == ["zone_39288", "zone_49148"]
    drive_way = lights["zone_49148"]
    assert drive_way.name == "Drive Way"
    assert drive_way.is_on
    assert drive_way.brightness == 10


def test_get_lights_keeps_zone_and_light_with_the_same_id(location):
    """Lights and zones are numbered independently; neither may be dropped."""
    location._credentials.make_request.return_value = [
        {"lightId": 7, "name": "Palm", "lightingStatusId": 2},
        {"id": 7, "name": "Pool Zone", "isZone": True, "lightingStatusId": 1},
    ]
    lights = location.get_lights()
    assert set(lights) == {"light_7", "zone_7"}
    assert lights["light_7"].name == "Palm" and not lights["light_7"].is_zone
    assert lights["zone_7"].name == "Pool Zone" and lights["zone_7"].is_zone
