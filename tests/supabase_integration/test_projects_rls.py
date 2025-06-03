import uuid
from datetime import datetime, timezone

import httpx
import pytest

from tests.supabase_integration.utils import SUPABASE_URL, headers_template


@pytest.mark.asyncio
async def test_user_can_create_and_read_project(test_user, test_project):
    """
    Ensure a confirmed user can create a project and read it back using RLS policies.
    """
    project_id = test_project
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        # Read the project
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


async def create_project(client, token, user_id):
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    headers = headers_template(token)
    resp = await client.post(
        f"{SUPABASE_URL}/rest/v1/projects", headers=headers, json={"id": project_id, "owner_id": user_id, "query": "test", "created_at": now}
    )
    assert resp.status_code in (200, 201)
    return project_id


@pytest.mark.asyncio
async def test_project_sources_crud(test_user, supabase_admin):
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        source_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        # Create a project source
        insert_resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/project_sources",
            headers=headers,
            json={"id": source_id, "project_id": project_id, "backend_name": "test", "backend_query": "query"},
        )
        assert insert_resp.status_code in (200, 201)

        # Read the project source
        read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/project_sources?id=eq.{source_id}", headers=headers)
        assert read_resp.status_code == 200
        assert len(read_resp.json()) == 1

        # 🔴 Cleanup both project source and project
        supabase_admin.table("project_sources").delete().eq("id", source_id).execute()
        supabase_admin.table("projects").delete().eq("id", project_id).execute()
