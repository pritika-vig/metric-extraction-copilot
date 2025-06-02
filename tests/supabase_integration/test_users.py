"""
Supabase Integration Tests: RLS + Schema + Cascade Behavior

This test suite validates Supabase's core functionality including:
- Ownership and collaborator access control
- Foreign key constraints
- Cascade deletes
- RLS enforcement on each critical table

Assumes service role key is used for setup/cleanup, and anon key is used for user-scoped actions.
"""

import os
import uuid

import httpx
import pytest
from supabase import create_client


@pytest.fixture(scope="module")
def supabase_admin():
    url = os.environ["SUPABASE_PROJECT_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


@pytest.fixture
def test_user(supabase_admin):
    email = f"testuser_{uuid.uuid4().hex[:6]}@example.com"
    password = "TestPass123"
    user = supabase_admin.auth.admin.create_user({"email": email, "password": password, "email_confirm": True}).user
    yield {"email": email, "password": password, "id": user.id}
    supabase_admin.auth.admin.delete_user(user.id)


@pytest.fixture
async def access_token(supabase_url, supabase_anon_key, test_user):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{supabase_url}/auth/v1/token?grant_type=password",
            headers={"apikey": supabase_anon_key},
            json={"email": test_user["email"], "password": test_user["password"]},
        )
        return response.json()["access_token"]
