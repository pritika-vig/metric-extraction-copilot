# tests/conftest.py

import os
import uuid

import httpx
import pytest
from dotenv import load_dotenv
from supabase import create_client

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
