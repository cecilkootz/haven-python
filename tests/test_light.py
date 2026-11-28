import pytest

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


def _on_payload(location_id=123, light_id=456, lighting_status_id=2, brightness=63):
    return {
        "locationId": location_id,
        "selectedLightIds": [light_id],
        "selectedZoneIds": [],
        "lightingStatusId": lighting_status_id,
        "lightBrightnessId": brightness,
        "lightColorId": 63,
        "patternSpeedId": 63,
    }


def test_turn_on_success(light):
    light._credentials.make_request.return_value = {"success": True}

    light.turn_on()

    assert light.is_on
    light._credentials.make_request.assert_called_once_with(
        "POST", "/v2/Light/CommandV1?locationId=123", json=_on_payload()
    )


def test_turn_on_with_brightness(light):
    light._credentials.make_request.return_value = {"success": True}

    light.turn_on(brightness=5)

    assert light.is_on
    assert light.brightness == 5
    light._credentials.make_request.assert_called_once_with(
        "POST",
        "/v2/Light/CommandV1?locationId=123",
        json=_on_payload(brightness=5),
    )


def test_turn_off_success(light):
    light._data.status = 2  # start "on"
    light._credentials.make_request.return_value = {"success": True}

    light.turn_off()

    assert not light.is_on
    light._credentials.make_request.assert_called_once_with(
        "POST",
        "/v2/Light/CommandV1?locationId=123",
        json=_on_payload(lighting_status_id=1),
    )


def test_set_brightness(light):
    light._credentials.make_request.return_value = {"success": True}

    light.set_brightness(7)

    assert light.brightness == 7
    light._credentials.make_request.assert_called_once_with(
        "POST",
        "/v2/Light/CommandV1?locationId=123",
        json=_on_payload(lighting_status_id=63, brightness=7),
    )


def test_set_brightness_rejects_out_of_range(light):
    with pytest.raises(ValueError):
        light.set_brightness(11)


def test_turn_on_command_failure_raises(light):
    light._credentials.make_request.return_value = {"success": False}

    with pytest.raises(ApiError):
        light.turn_on()

    assert not light.is_on
