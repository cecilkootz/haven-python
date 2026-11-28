import pytest

from havenlighting.config import COMMAND_API_BASE
from havenlighting.credentials import Credentials
from havenlighting.devices.light import Light
from havenlighting.exceptions import ApiError


@pytest.fixture
def light(mocker):
    credentials = mocker.Mock(spec=Credentials)
    return Light(
        credentials,
        location_id=123,
        light_id=456,
        data={
            "lightId": 456,
            "name": "Test Light",
            "lightingStatusId": 1,
            "lightBrightnessId": 10,
            "colorId": 11,
            "patternSpeed": 0,
        },
    )


def _on_payload(location_id=123, light_id=456, lighting_status_id=2, brightness=63,
                light_ids=None, zone_ids=None, color_id=63, pattern_speed=63):
    return {
        "locationId": location_id,
        "selectedLightIds": [light_id] if light_ids is None else light_ids,
        "selectedZoneIds": [] if zone_ids is None else zone_ids,
        "lightingStatusId": lighting_status_id,
        "lightBrightnessId": brightness,
        "lightColorId": color_id,
        "patternSpeedId": pattern_speed,
    }


def _assert_command(mock, payload):
    mock.assert_called_once_with(
        "POST",
        "/v2/Light/CommandV1?locationId=123",
        json=payload,
        base_url=COMMAND_API_BASE,
    )


def test_turn_on_success(light):
    light._credentials.make_request.return_value = {"success": True}

    light.turn_on()

    assert light.is_on
    _assert_command(light._credentials.make_request, _on_payload())


def test_turn_on_with_brightness(light):
    light._credentials.make_request.return_value = {"success": True}

    light.turn_on(brightness=5)

    assert light.is_on
    assert light.brightness == 5
    _assert_command(light._credentials.make_request, _on_payload(brightness=5))


def test_turn_off_success(light):
    light._data.status = 2  # start "on"
    light._credentials.make_request.return_value = {"success": True}

    light.turn_off()

    assert not light.is_on
    _assert_command(
        light._credentials.make_request, _on_payload(lighting_status_id=1)
    )


def test_set_brightness(light):
    light._credentials.make_request.return_value = {"success": True}

    light.set_brightness(7)

    assert light.brightness == 7
    _assert_command(
        light._credentials.make_request,
        _on_payload(lighting_status_id=63, brightness=7),
    )


def test_set_brightness_rejects_out_of_range(light):
    with pytest.raises(ValueError):
        light.set_brightness(11)


def test_turn_on_command_failure_raises(light):
    light._credentials.make_request.return_value = {"success": False}

    with pytest.raises(ApiError):
        light.turn_on()

    assert not light.is_on


def test_zone_command_uses_selected_zone_ids(mocker):
    credentials = mocker.Mock(spec=Credentials)
    zone = Light(
        credentials,
        location_id=123,
        light_id=49148,
        data={
            "id": 49148,
            "name": "Drive Way",
            "lightingStatusId": 2,
            "lightBrightnessId": 10,
            "colorId": 2,
            "patternSpeed": 16,
            "isZone": True,
        },
    )
    credentials.make_request.return_value = {"success": True}

    zone.turn_off()

    assert not zone.is_on
    _assert_command(
        credentials.make_request,
        _on_payload(
            light_id=49148,
            lighting_status_id=1,
            light_ids=[],
            zone_ids=[49148],
        ),
    )


def test_turn_on_with_color(light):
    light._credentials.make_request.return_value = {"success": True}

    light.turn_on(color_id=25)  # DEEP BLUE

    assert light._data.color == 25
    _assert_command(
        light._credentials.make_request, _on_payload(color_id=25)
    )


def test_turn_on_with_pattern(light):
    light._credentials.make_request.return_value = {"success": True}

    light.turn_on(color_id=80, pattern_speed=10)  # Sparkle pattern

    _assert_command(
        light._credentials.make_request,
        _on_payload(color_id=80, pattern_speed=10),
    )


def test_set_color(light):
    light._credentials.make_request.return_value = {"success": True}

    light.set_color(2)  # 3000K white

    assert light._data.color == 2
    _assert_command(
        light._credentials.make_request,
        _on_payload(lighting_status_id=63, color_id=2),
    )


def test_set_color_rejects_unknown_id(light):
    with pytest.raises(ValueError):
        light.set_color(999)


def test_set_pattern_speed(light):
    light._credentials.make_request.return_value = {"success": True}

    light.set_pattern_speed(16)

    assert light._data.pattern_speed == 16
    _assert_command(
        light._credentials.make_request,
        _on_payload(lighting_status_id=63, pattern_speed=16),
    )


def test_set_pattern_speed_rejects_out_of_range(light):
    with pytest.raises(ValueError):
        light.set_pattern_speed(0)


def test_rename(light):
    light._credentials.make_request.return_value = {}

    light.rename("New Name")

    assert light.name == "New Name"
    light._credentials.make_request.assert_called_once_with(
        "PUT",
        "/Light/UpdateName",
        json={"lightId": 456, "name": "New Name", "pinName": None},
    )
