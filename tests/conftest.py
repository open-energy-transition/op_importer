from dataclasses import dataclass
from typing import Any

import pytest
import requests


def elements(*items: dict) -> dict:
    return {"_embedded": {"elements": list(items)}}


@dataclass
class FakeResponse:
    status_code: int
    payload: dict

    def json(self) -> dict:
        return self.payload


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> dict[str, dict]:
    routes: dict[str, dict] = {
        "/users": elements(),
        "/roles": elements(),
        "/projects": elements({"id": 4, "name": "Project 4"}),
        "/work_packages": elements(),
        "/types": elements({"id": 3}),
        "/statuses": elements(),
        "/work_packages/form": {"_embedded": {"validationErrors": {}, "payload": {}}},
    }

    def respond(url: str, **kwargs: Any) -> FakeResponse:
        [route] = [route for route in routes if url.endswith(route)]
        return FakeResponse(200, routes[route])

    monkeypatch.setattr(requests, "get", respond)
    monkeypatch.setattr(requests, "post", respond)
    return routes
