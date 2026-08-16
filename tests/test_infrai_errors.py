import pytest

from infrai_errors import InfraiAPIError, InfraiErrors


class Response:
    def __init__(self, status_code, body, headers=None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)

    def json(self):
        return self._body


class Session:
    def __init__(self):
        self.calls = []
        self.responses = [
            Response(429, {}, {"Retry-After": "2"}),
            Response(
                200,
                {
                    "ok": True,
                    "data": {"event_id": "evt-1", "error_group_id": "grp-1"},
                    "error": None,
                    "metadata": {},
                },
            ),
        ]

    def request(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def test_capture_retries_with_same_idempotency_key():
    session = Session()
    delays = []
    client = InfraiErrors(api_key="test-key", session=session, sleep=delays.append)

    captured = client.capture({"exception": "ValueError: declined"}, idempotency_key="order:1")

    assert captured.error_group_id == "grp-1"
    assert delays == [2.0]
    assert [call["method"] for call in session.calls] == ["POST", "POST"]
    assert all(call["headers"]["Idempotency-Key"] == "order:1" for call in session.calls)


def test_capture_decodes_business_error_envelope_before_http_status():
    session = Session()
    session.responses = [
        Response(
            422,
            {
                "ok": False,
                "data": None,
                "error": {"message": "captcha required"},
            },
        )
    ]
    client = InfraiErrors(api_key="test-key", session=session)

    with pytest.raises(InfraiAPIError, match="captcha required"):
        client.capture({"exception": "ValueError: declined"}, idempotency_key="order:1")
