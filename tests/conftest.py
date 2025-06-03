# tests/conftest.py

import os
import uuid
from datetime import datetime, timezone

import httpx
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from supabase import create_client

from tests.supabase_integration.utils import headers_template

# Load .env variables like SUPABASE keys
load_dotenv()

# Global Supabase config
SUPABASE_URL = os.environ["SUPABASE_PROJECT_URL"]
SUPABASE_ANON_KEY = os.environ["SUPABASE_ANON_KEY"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

# ------------- Global Fixtures ------------------


@pytest.fixture(scope="module")
def supabase_admin():
    """
    Supabase admin client using the service role key.
    Use this for setup/cleanup that bypasses RLS.
    """
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


@pytest.fixture
def test_user(supabase_admin):
    """
    Creates a confirmed user via Admin API and returns their token, ID, and email.
    Automatically cleaned up after test.
    """
    email = f"testuser_{uuid.uuid4().hex[:6]}@example.com"
    password = "TestPass123"

    # Create confirmed user
    user = supabase_admin.auth.admin.create_user({"email": email, "password": password, "email_confirm": True}).user

    # Log in via password grant to get access token
    resp = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]

    yield {"email": email, "password": password, "id": user.id, "token": token}

    # Cleanup: delete user and related data
    supabase_admin.table("projects").delete().eq("owner_id", user.id).execute()
    supabase_admin.auth.admin.delete_user(user.id)


@pytest.fixture
async def http_client():
    """
    Shared async HTTPX client for REST requests.
    """
    async with httpx.AsyncClient() as client:
        yield client


@pytest.fixture(scope="module")
def supabase_url():
    """Fixture for the Supabase project URL."""
    return SUPABASE_URL


@pytest.fixture(scope="module")
def supabase_anon_key():
    """Fixture for the Supabase anon public key."""
    return SUPABASE_ANON_KEY


@pytest_asyncio.fixture
async def test_project(test_user, supabase_admin):
    # Setup: create a project
    project_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/projects",
            headers=headers,
            json={"id": project_id, "description": "Test desc from RLS test", "created_at": created_at, "owner_id": test_user["id"]},
        )
        assert resp.status_code in (200, 201), resp.text

    # Yield the ID for use in the test
    yield project_id

    # Teardown: delete the project
    supabase_admin.table("projects").delete().eq("id", project_id).execute()


@pytest_asyncio.fixture
async def test_paper(test_project, test_user, supabase_admin):
    paper_id = str(uuid.uuid4())
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": test_project, "title": "My Paper", "abstract": "My abstract"},
        )
        assert resp.status_code in (200, 201)

    yield paper_id

    supabase_admin.table("papers").delete().eq("id", paper_id).execute()


@pytest_asyncio.fixture
def other_user_with_project(supabase_admin):
    user_email = f"other_{uuid.uuid4().hex[:6]}@example.com"
    password = "TestPass123"
    now = datetime.now(timezone.utc).isoformat()
    user = supabase_admin.auth.admin.create_user({"email": user_email, "password": password, "email_confirm": True}).user

    project_id = str(uuid.uuid4())
    supabase_admin.table("projects").insert({"id": project_id, "owner_id": user.id, "description": "other project", "created_at": now}).execute()

    yield user, project_id

    supabase_admin.table("projects").delete().eq("id", project_id).execute()
    supabase_admin.auth.admin.delete_user(user.id)


@pytest_asyncio.fixture
async def test_project_with_cleanup(test_user, supabase_admin):
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/projects",
            headers=headers,
            json={"id": project_id, "owner_id": test_user["id"], "description": "filter test", "created_at": now},
        )
        assert resp.status_code in (200, 201)

    yield project_id

    supabase_admin.table("projects").delete().eq("id", project_id).execute()


@pytest_asyncio.fixture
def other_user_with_filter_project(supabase_admin):
    user = supabase_admin.auth.admin.create_user(
        {"email": f"owner_{uuid.uuid4().hex[:6]}@example.com", "password": "TestPass123", "email_confirm": True}
    ).user

    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    supabase_admin.table("projects").insert(
        {"id": project_id, "owner_id": user.id, "description": "other user's project", "created_at": now}
    ).execute()

    yield user, project_id

    supabase_admin.table("projects").delete().eq("id", project_id).execute()
    supabase_admin.auth.admin.delete_user(user.id)


@pytest_asyncio.fixture
async def test_extraction_config(test_project, test_user, supabase_admin):
    config_id = str(uuid.uuid4())
    headers = headers_template(test_user["token"])
    now = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_configs", headers=headers, json={"id": config_id, "project_id": test_project, "created_at": now}
        )
        assert resp.status_code in (200, 201)

    yield config_id

    supabase_admin.table("extraction_configs").delete().eq("id", config_id).execute()


@pytest_asyncio.fixture
async def test_extraction_field(test_extraction_config, test_user, supabase_admin):
    field_id = str(uuid.uuid4())
    headers = headers_template(test_user["token"])
    now = datetime.now(timezone.utc).isoformat()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_fields",
            headers=headers,
            json={
                "id": field_id,
                "config_id": test_extraction_config,
                "field_name": "Author",
                "description": "Extract Author",
                "created_at": now,
            },
        )
        assert resp.status_code in (200, 201)

    yield field_id

    supabase_admin.table("extraction_fields").delete().eq("id", field_id).execute()


@pytest_asyncio.fixture
async def test_extracted_field(test_extraction_field, test_paper, test_user, supabase_admin):
    extract_id = str(uuid.uuid4())
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/extracted_fields",
            headers=headers,
            json={"id": extract_id, "paper_id": test_paper, "extraction_field_id": test_extraction_field, "field_value": "Dr. Alice"},
        )
        assert resp.status_code in (200, 201)

    yield extract_id

    supabase_admin.table("extracted_fields").delete().eq("id", extract_id).execute()


@pytest_asyncio.fixture
def other_user_with_extraction_data(supabase_admin):
    """
    Creates a second user with a full extraction data chain:
    project → config → field → paper → extracted_field
    Returns a dict of all IDs and the user.
    Cleans up everything after test.
    """
    now = datetime.now(timezone.utc).isoformat()
    user_email = f"other_{uuid.uuid4().hex[:6]}@example.com"
    password = "TestPass123"

    user = supabase_admin.auth.admin.create_user(
        {
            "email": user_email,
            "password": password,
            "email_confirm": True,
        }
    ).user

    project_id = str(uuid.uuid4())
    config_id = str(uuid.uuid4())
    field_id = str(uuid.uuid4())
    paper_id = str(uuid.uuid4())
    extract_id = str(uuid.uuid4())

    supabase_admin.table("projects").insert({"id": project_id, "owner_id": user.id, "description": "other", "created_at": now}).execute()

    supabase_admin.table("extraction_configs").insert({"id": config_id, "project_id": project_id, "created_at": now}).execute()

    supabase_admin.table("extraction_fields").insert(
        {"id": field_id, "config_id": config_id, "field_name": "Test", "description": "Desc", "created_at": now}
    ).execute()

    supabase_admin.table("papers").insert({"id": paper_id, "project_id": project_id, "title": "Hidden", "abstract": "Secret"}).execute()

    supabase_admin.table("extracted_fields").insert(
        {"id": extract_id, "paper_id": paper_id, "extraction_field_id": field_id, "field_value": "X"}
    ).execute()

    yield {
        "user": user,
        "project_id": project_id,
        "config_id": config_id,
        "field_id": field_id,
        "paper_id": paper_id,
        "extract_id": extract_id,
    }

    # Teardown (delete in reverse order)
    supabase_admin.table("extracted_fields").delete().eq("id", extract_id).execute()
    supabase_admin.table("papers").delete().eq("id", paper_id).execute()
    supabase_admin.table("extraction_fields").delete().eq("id", field_id).execute()
    supabase_admin.table("extraction_configs").delete().eq("id", config_id).execute()
    supabase_admin.table("projects").delete().eq("id", project_id).execute()
    supabase_admin.auth.admin.delete_user(user.id)


@pytest_asyncio.fixture
async def user_filter(test_project_with_cleanup, test_user, supabase_admin):
    """Creates a filter for the current test_user, cleans up after test."""
    filter_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/filters",
            headers=headers,
            json={
                "id": filter_id,
                "project_id": test_project_with_cleanup,
                "timestamp": now,
                "user_specified_text_filter": "initial",
                "filter_scope": "abstract",
            },
        )
        assert resp.status_code in (200, 201)

    yield filter_id

    supabase_admin.table("filters").delete().eq("id", filter_id).execute()


@pytest_asyncio.fixture
def other_user_filter(supabase_admin, other_user_with_filter_project):
    """Creates a filter for another user and cleans up after test."""
    other_user, project_id = other_user_with_filter_project
    filter_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    supabase_admin.table("filters").insert(
        {
            "id": filter_id,
            "project_id": project_id,
            "timestamp": now,
            "filter_scope": "abstract",
        }
    ).execute()

    yield filter_id

    supabase_admin.table("filters").delete().eq("id", filter_id).execute()


@pytest_asyncio.fixture
def other_user_paper(supabase_admin, other_user_with_project):
    user, project_id = other_user_with_project
    paper_id = str(uuid.uuid4())

    supabase_admin.table("papers").insert({"id": paper_id, "project_id": project_id, "title": "Hidden", "abstract": "Classified"}).execute()

    yield paper_id

    supabase_admin.table("papers").delete().eq("id", paper_id).execute()


@pytest_asyncio.fixture
def paper_dependencies_for_cascade(test_project, test_user, supabase_admin):
    ids = {k: str(uuid.uuid4()) for k in ["config", "field", "paper", "extract", "filter", "result"]}
    now = datetime.now(timezone.utc).isoformat()

    supabase_admin.table("extraction_configs").insert({"id": ids["config"], "project_id": test_project, "created_at": now}).execute()
    supabase_admin.table("extraction_fields").insert(
        {"id": ids["field"], "config_id": ids["config"], "field_name": "Field", "description": "Desc", "created_at": now}
    ).execute()
    supabase_admin.table("filters").insert(
        {"id": ids["filter"], "project_id": test_project, "timestamp": now, "filter_scope": "abstract"}
    ).execute()

    yield ids

    supabase_admin.table("extraction_fields").delete().eq("id", ids["field"]).execute()
    supabase_admin.table("filters").delete().eq("id", ids["filter"]).execute()
    supabase_admin.table("extraction_configs").delete().eq("id", ids["config"]).execute()
