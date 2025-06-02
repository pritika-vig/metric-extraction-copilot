# tests/supabase_integration/test_filters_table.py

import uuid
from datetime import datetime, timezone

import httpx
import pytest

from tests.supabase_integration.utils import SUPABASE_URL, create_project, headers_template, wait_until_deleted


@pytest.mark.asyncio
async def test_filter_and_result_crud(test_user):
    """Test basic creation and retrieval of filters and paper_filter_results."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        filter_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])
        now = datetime.now(timezone.utc).isoformat()

        # Paper
        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "Title", "abstract": "Text"},
        )

        # Filter
        await client.post(
            f"{SUPABASE_URL}/rest/v1/filters",
            headers=headers,
            json={"id": filter_id, "project_id": project_id, "timestamp": now, "filter_scope": "abstract"},
        )

        # Result
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/paper_filter_results",
            headers=headers,
            json={"id": result_id, "paper_id": paper_id, "filter_id": filter_id, "passed": True},
        )
        assert resp.status_code in (200, 201)

        # Read result
        read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/paper_filter_results?id=eq.{result_id}", headers=headers)
        assert read_resp.status_code == 200
        assert len(read_resp.json()) == 1


@pytest.mark.asyncio
async def test_deleting_project_cascades_filters(test_user):
    """When a project is deleted, its filters should also be deleted."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        filter_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])
        now = datetime.now(timezone.utc).isoformat()

        await client.post(
            f"{SUPABASE_URL}/rest/v1/filters",
            headers=headers,
            json={"id": filter_id, "project_id": project_id, "timestamp": now, "filter_scope": "abstract"},
        )

        del_resp = await client.delete(f"{SUPABASE_URL}/rest/v1/projects?id=eq.{project_id}", headers={**headers, "Prefer": "return=minimal"})
        assert del_resp.status_code == 204

        deleted = await wait_until_deleted(f"{SUPABASE_URL}/rest/v1/filters?id=eq.{filter_id}", headers)
        assert deleted, f"Filter {filter_id} still exists after project deletion"


@pytest.mark.asyncio
async def test_user_cannot_access_others_filters(test_user, supabase_admin):
    """Ensure a user cannot read another user's filters."""
    other_user = supabase_admin.auth.admin.create_user(
        {"email": f"owner_{uuid.uuid4().hex[:6]}@example.com", "password": "TestPass123", "email_confirm": True}
    ).user

    filter_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    supabase_admin.table("projects").insert({"id": project_id, "owner_id": other_user.id, "query": "secret", "created_at": now}).execute()

    supabase_admin.table("filters").insert({"id": filter_id, "project_id": project_id, "timestamp": now, "filter_scope": "abstract"}).execute()

    headers = headers_template(test_user["token"])
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/filters?id=eq.{filter_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_user_cannot_update_own_filter(test_user):
    """Users are not allowed to update filters, even their own (RLS block expected)."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        filter_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])
        now = datetime.now(timezone.utc).isoformat()

        # Create filter
        create_resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/filters",
            headers=headers,
            json={
                "id": filter_id,
                "project_id": project_id,
                "timestamp": now,
                "user_specified_text_filter": "initial",
                "filter_scope": "abstract",
            },
        )
        assert create_resp.status_code in (200, 201)

        # Try to update — should be forbidden
        update_resp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/filters?id=eq.{filter_id}", headers=headers, json={"user_specified_text_filter": "updated"}
        )
        update_resp.raise_for_status()  # Should raise an error if not 2xx

        read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/filters?id=eq.{filter_id}", headers=headers)
        assert read_resp.status_code == 200
        assert read_resp.json()[0]["user_specified_text_filter"] == "initial"


@pytest.mark.asyncio
async def test_deleting_filter_cascades_results(test_user):
    """Ensure deleting a filter deletes its associated paper_filter_results."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        filter_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])
        now = datetime.now(timezone.utc).isoformat()

        # Insert paper and filter
        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "Sample", "abstract": "Content"},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/filters",
            headers=headers,
            json={"id": filter_id, "project_id": project_id, "timestamp": now, "filter_scope": "abstract"},
        )

        # Insert result
        await client.post(
            f"{SUPABASE_URL}/rest/v1/paper_filter_results",
            headers=headers,
            json={"id": result_id, "paper_id": paper_id, "filter_id": filter_id, "passed": True},
        )

        # Delete the filter
        del_resp = await client.delete(f"{SUPABASE_URL}/rest/v1/filters?id=eq.{filter_id}", headers={**headers, "Prefer": "return=minimal"})
        assert del_resp.status_code == 204

        # Verify result is gone
        gone = await wait_until_deleted(f"{SUPABASE_URL}/rest/v1/paper_filter_results?id=eq.{result_id}", headers)
        assert gone, f"Result {result_id} still exists after deleting filter {filter_id}"
