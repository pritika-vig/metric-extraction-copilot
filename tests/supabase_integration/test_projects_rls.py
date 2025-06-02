import uuid
from datetime import datetime, timezone

import httpx
import pytest

from tests.supabase_integration.utils import SUPABASE_URL, headers_template


@pytest.mark.asyncio
async def test_user_can_create_and_read_project(test_user):
    """
    Ensure a confirmed user can create a project and read it back using RLS policies.
    """
    project_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        # Create project
        create_resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/projects",
            headers=headers,
            json={"id": project_id, "query": "Test query from RLS test", "created_at": created_at, "owner_id": test_user["id"]},
        )
        assert create_resp.status_code in (200, 201), create_resp.text

        # Read project
        read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/projects?id=eq.{project_id}", headers=headers)
        assert read_resp.status_code == 200
        data = read_resp.json()
        assert len(data) == 1
        assert data[0]["id"] == project_id


@pytest.mark.asyncio
async def test_user_cannot_read_others_project(test_user, supabase_admin):
    """
    Ensure that a user cannot access a project owned by another user.
    """
    # Create another user (owner)
    other_email = f"owner_{uuid.uuid4().hex[:6]}@example.com"
    other_password = "TestPass123"
    other_user = supabase_admin.auth.admin.create_user({"email": other_email, "password": other_password, "email_confirm": True}).user

    project_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    # Create a project owned by the other user
    supabase_admin.table("projects").insert(
        {"id": project_id, "query": "Private project", "owner_id": other_user.id, "created_at": created_at}
    ).execute()

    # Try to access that project with test_user
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/projects?id=eq.{project_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    # Clean up the created project and other user
    supabase_admin.table("projects").delete().eq("id", project_id).execute()
    supabase_admin.auth.admin.delete_user(other_user.id)
