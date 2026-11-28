"""Auth error classification, Light.is_zone, and library logging hygiene."""
import logging

import pytest

from havenlighting import HavenClient
from havenlighting.credentials import Credentials
from havenlighting.devices.light import Light
from havenlighting.exceptions import ApiError, AuthenticationError

AUTH_OK = {"id": 123, "token": "t", "refreshToken": "r"}


def _client_with(mocker, side_effect):
    client = HavenClient()
    credentials = Credentials()
    mock = mocker.patch.object(credentials, "_make_request_internal")
    mock.side_effect = side_effect
    client._credentials = credentials
    return client, mock


@pytest.mark.parametrize("code", [400, 401, 404, 422])
def test_rejected_credentials_return_false(mocker, code):
    client, _ = _client_with(mocker, ApiError("Invalid username or password", code=code))
    assert client.authenticate("a@example.com", "wrong") is False


def test_401_authentication_error_returns_false(mocker):
    client, _ = _client_with(mocker, AuthenticationError("Received 401 Unauthorized response"))
    assert client.authenticate("a@example.com", "wrong") is False


@pytest.mark.parametrize(
    "error",
    [
        ApiError("Request failed: Could not resolve host"),  # transport, no status
        ApiError("Service Unavailable", code=503),
        ApiError("The request is blocked.", code=403),  # Front Door WAF
        ApiError("Too Many Requests", code=429),
    ],
)
def test_unreachable_haven_raises_instead_of_false(mocker, error):
    """An outage must not look like a wrong password."""
    client, _ = _client_with(mocker, error)
    with pytest.raises(ApiError):
        client.authenticate("a@example.com", "right")
    assert not client._credentials.is_authenticated


def test_response_without_token_returns_false(mocker):
    client, _ = _client_with(mocker, [{"message": "nope"}])
    assert client.authenticate("a@example.com", "pw") is False


def _authenticated_credentials(mocker, after_auth):
    credentials = Credentials()
    mock = mocker.patch.object(credentials, "_make_request_internal")
    mock.side_effect = [AUTH_OK, *after_auth]
    assert credentials.authenticate("a@example.com", "pw")
    return credentials, mock


def test_rejected_refresh_raises_authentication_error(mocker):
    credentials, _ = _authenticated_credentials(
        mocker, [AuthenticationError("401"), ApiError("invalid refresh token", code=400)]
    )
    with pytest.raises(AuthenticationError):
        credentials.make_request("GET", "/x")


def test_unreachable_refresh_raises_api_error(mocker):
    """A network failure during refresh is transient, not an auth failure."""
    credentials, _ = _authenticated_credentials(
        mocker, [AuthenticationError("401"), ApiError("Request failed: timeout")]
    )
    with pytest.raises(ApiError) as excinfo:
        credentials.make_request("GET", "/x")
    assert not isinstance(excinfo.value, AuthenticationError)


def test_light_is_zone_property():
    zone = Light(None, 1, 7, {"id": 7, "name": "Pool", "isZone": True})
    light = Light(None, 1, 8, {"lightId": 8, "name": "Palm"})
    assert zone.is_zone is True
    assert light.is_zone is False


@pytest.fixture
def clean_logger():
    logger = logging.getLogger("havenlighting")
    saved = (list(logger.handlers), logger.level)
    yield logger
    logger.handlers[:] = saved[0]
    logger.setLevel(saved[1])


def test_default_client_leaves_logging_alone(clean_logger):
    """Applications (e.g. Home Assistant) own handlers and levels."""
    handlers_before = list(clean_logger.handlers)
    clean_logger.setLevel(logging.WARNING)
    for _ in range(3):
        HavenClient()
    assert clean_logger.handlers == handlers_before
    assert clean_logger.level == logging.WARNING


def test_opt_in_logging_does_not_stack_handlers(clean_logger):
    for _ in range(3):
        HavenClient(log_level=logging.DEBUG)
    stream_handlers = [
        h for h in clean_logger.handlers if getattr(h, "_havenlighting_handler", False)
    ]
    assert len(stream_handlers) == 1
    assert clean_logger.level == logging.DEBUG


def test_email_is_not_logged(mocker, caplog, clean_logger):
    caplog.set_level(logging.DEBUG, logger="havenlighting")
    client, _ = _client_with(mocker, [AUTH_OK])
    client.authenticate("secret.person@example.com", "pw")
    client2, _ = _client_with(mocker, ApiError("bad", code=400))
    client2.authenticate("secret.person@example.com", "pw")
    assert "secret.person" not in caplog.text
