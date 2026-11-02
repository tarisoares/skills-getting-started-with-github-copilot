from copy import deepcopy

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.app import activities, app


@pytest_asyncio.fixture
async def client():
    original_activities = deepcopy(activities)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as test_client:
        yield test_client

    activities.clear()
    activities.update(original_activities)


async def test_root_redirects_to_static_index(client):
    response = await client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


async def test_get_activities_returns_seeded_data(client):
    response = await client.get("/activities")

    assert response.status_code == 200
    data = response.json()
    assert "Chess Club" in data
    assert data["Chess Club"]["participants"] == [
        "michael@mergington.edu",
        "daniel@mergington.edu",
    ]


async def test_signup_adds_new_participant(client):
    email = "new.student@mergington.edu"

    response = await client.post(
        "/activities/Art Club/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for Art Club"}
    assert email in activities["Art Club"]["participants"]


async def test_signup_rejects_unknown_activity(client):
    response = await client.post(
        "/activities/Unknown Club/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


async def test_signup_rejects_duplicate_participant(client):
    response = await client.post(
        "/activities/Chess Club/signup",
        params={"email": "michael@mergington.edu"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Student is already signed up for this activity"


async def test_delete_removes_existing_participant(client):
    email = "remove.student@mergington.edu"
    activities["Art Club"]["participants"].append(email)

    response = await client.delete(
        "/activities/Art Club/signup",
        params={"email": email},
    )

    assert response.status_code == 200
    assert response.json() == {"message": f"Removed {email} from Art Club"}
    assert email not in activities["Art Club"]["participants"]


async def test_delete_rejects_unknown_activity(client):
    response = await client.delete(
        "/activities/Unknown Club/signup",
        params={"email": "student@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


async def test_delete_rejects_unregistered_participant(client):
    response = await client.delete(
        "/activities/Art Club/signup",
        params={"email": "not.registered@mergington.edu"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"
