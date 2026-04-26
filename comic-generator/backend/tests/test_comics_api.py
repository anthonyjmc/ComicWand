from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.v1 import comics
from app.core.database import get_db_session
from app.core.rate_limiter import check_rate_limit
from app.core.security import get_current_user
from app.main import app
from app.models.comic import ComicStatus


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


class ScalarsResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class ListResult:
    def __init__(self, items):
        self.items = items

    def scalars(self):
        return ScalarsResult(self.items)


@pytest.fixture
def api_client():
    return TestClient(app)


@pytest.fixture
def no_rate_limit_override():
    async def _no_rate_limit(*args, **kwargs):
        del args, kwargs
        return None

    app.dependency_overrides[check_rate_limit] = _no_rate_limit
    yield
    app.dependency_overrides.pop(check_rate_limit, None)


@pytest.fixture
def auth_override():
    async def _auth():
        return {"sub": "user_a", "email": "a@example.com", "tier": "free"}

    app.dependency_overrides[get_current_user] = _auth
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _override_db_session(session):
    async def _db_session_override():
        yield session

    app.dependency_overrides[get_db_session] = _db_session_override


def _clear_db_override():
    app.dependency_overrides.pop(get_db_session, None)


def test_create_comic_without_auth_returns_401(api_client, no_rate_limit_override):
    response = api_client.post(
        "/api/v1/comics/create",
        data={"story_prompt": "A valid story prompt", "pages": 4, "style": "manga", "title": "Valid Title"},
    )
    assert response.status_code == 401


def test_create_comic_invalid_data_returns_422(api_client, no_rate_limit_override, auth_override):
    response = api_client.post(
        "/api/v1/comics/create",
        data={"story_prompt": "short", "pages": 0, "style": "manga", "title": "bad"},
        headers={"Authorization": "Bearer test"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_accessing_another_users_comic_returns_403(api_client, no_rate_limit_override, auth_override, monkeypatch):
    own_user = SimpleNamespace(id=uuid4())
    another_user = uuid4()
    target_comic = SimpleNamespace(
        id=uuid4(),
        user_id=another_user,
        status=ComicStatus.completed,
        pdf_url="https://example.r2.dev/comics/out.pdf",
    )

    class SessionMock:
        async def execute(self, _statement):
            return ScalarResult(target_comic)

    _override_db_session(SessionMock())
    async def _get_user(**_kwargs):
        return own_user

    monkeypatch.setattr(comics, "_get_or_create_user", _get_user)

    response = api_client.get(f"/api/v1/comics/{target_comic.id}/status", headers={"Authorization": "Bearer test"})
    _clear_db_override()
    assert response.status_code == 403


def test_delete_processing_comic_cancels_task(api_client, no_rate_limit_override, auth_override, monkeypatch):
    user = SimpleNamespace(id=uuid4())
    comic_id = uuid4()
    processing_comic = SimpleNamespace(
        id=comic_id,
        user_id=user.id,
        status=ComicStatus.processing,
        reference_image_url=None,
        pdf_url=None,
    )

    class SessionMock:
        async def execute(self, _statement):
            return ScalarResult(processing_comic)

        async def delete(self, _obj):
            return None

        async def commit(self):
            return None

    _override_db_session(SessionMock())
    async def _get_user(**_kwargs):
        return user

    monkeypatch.setattr(comics, "_get_or_create_user", _get_user)
    monkeypatch.setattr(comics.storage_service, "delete_file", lambda *_args, **_kwargs: None)

    revoked = {"called": False}

    class ControlMock:
        def inspect(self):
            return self

        def active(self):
            return {"worker-1": [{"id": "task-123", "args": [str(comic_id), str(user.id)]}]}

        def revoke(self, task_id, terminate):
            revoked["called"] = task_id == "task-123" and terminate is True

    monkeypatch.setattr(comics, "celery_app", SimpleNamespace(control=ControlMock()))

    response = api_client.delete(f"/api/v1/comics/{comic_id}", headers={"Authorization": "Bearer test"})
    _clear_db_override()
    assert response.status_code == 204
    assert revoked["called"] is True


def test_list_comics_pagination(api_client, no_rate_limit_override, auth_override, monkeypatch):
    user = SimpleNamespace(id=uuid4())
    comic_items = [
        SimpleNamespace(
            id=uuid4(),
            title="Comic 1",
            status=ComicStatus.pending,
            pages_count=4,
            style="manga",
            created_at="2026-04-26T00:00:00Z",
            pdf_url=None,
        ),
        SimpleNamespace(
            id=uuid4(),
            title="Comic 2",
            status=ComicStatus.completed,
            pages_count=6,
            style="western",
            created_at="2026-04-26T01:00:00Z",
            pdf_url="https://example.r2.dev/comics/final.pdf",
        ),
    ]

    class SessionMock:
        call_index = 0

        async def execute(self, _statement):
            self.call_index += 1
            if self.call_index == 1:
                return ScalarResult(12)
            return ListResult(comic_items)

    _override_db_session(SessionMock())
    async def _get_user(**_kwargs):
        return user

    monkeypatch.setattr(comics, "_get_or_create_user", _get_user)
    monkeypatch.setattr(comics.storage_service, "get_signed_url", lambda *_args, **_kwargs: "https://signed-url")

    response = api_client.get("/api/v1/comics/?limit=2&offset=4", headers={"Authorization": "Bearer test"})
    _clear_db_override()
    assert response.status_code == 200
    payload = response.json()
    assert payload["limit"] == 2
    assert payload["offset"] == 4
    assert payload["total"] == 12
    assert len(payload["items"]) == 2
