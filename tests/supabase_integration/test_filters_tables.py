# tests/supabase_integration/test_filters_table.py

import uuid
from datetime import datetime, timezone

import httpx
import pytest

from tests.supabase_integration.utils import SUPABASE_URL, create_project, headers_template, wait_until_deleted


@pytest.mark.asyncio
async def test_filter_and_result_crud(test_user, test_project_with_cleanup, supabase_admin):
    async with httpx.AsyncClient() as client:
        project_id = test_project_with_cleanup
        headers = headers_template(test_user["token"])
        now = datetime.now(timezone.utc).isoformat()

        paper_id = str(uuid.uuid4())
        filter_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())

        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "Title", "abstract": "Text"},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/filters",
            headers=headers,
            json={"id": filter_id, "project_id": project_id, "timestamp": now, "filter_scope": "abstract"},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/paper_filter_results",
            headers=headers,
            json={"id": result_id, "paper_id": paper_id, "filter_id": filter_id, "passed": True},
        )

        resp = await client.get(f"{SUPABASE_URL}/rest/v1/paper_filter_results?id=eq.{result_id}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Cleanup
        supabase_admin.table("paper_filter_results").delete().eq("id", result_id).execute()
        supabase_admin.table("filters").delete().eq("id", filter_id).execute()
        supabase_admin.table("papers").delete().eq("id", paper_id).execute()


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
async def test_user_cannot_access_others_filters(test_user, other_user_filter):
    headers = headers_template(test_user["token"])
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/filters?id=eq.{other_user_filter}", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_user_cannot_update_own_filter(user_filter, test_user):
    headers = headers_template(test_user["token"])
    async with httpx.AsyncClient() as client:
        update_resp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/filters?id=eq.{user_filter}", headers=headers, json={"user_specified_text_filter": "updated"}
        )
        assert update_resp.status_code in (403, 401), f"Update response debug: {update_resp.status_code} {update_resp.text}"

        read_resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/filters?id=eq.{user_filter}",
            headers=headers,
        )
        assert read_resp.status_code == 200
        assert read_resp.json()[0]["user_specified_text_filter"] == "initial"


@pytest.mark.asyncio
async def test_deleting_filter_cascades_results(test_user, test_project_with_cleanup, supabase_admin):
    async with httpx.AsyncClient() as client:
        project_id = test_project_with_cleanup
        headers = headers_template(test_user["token"])
        now = datetime.now(timezone.utc).isoformat()

        paper_id = str(uuid.uuid4())
        filter_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())

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
        await client.post(
            f"{SUPABASE_URL}/rest/v1/paper_filter_results",
            headers=headers,
            json={"id": result_id, "paper_id": paper_id, "filter_id": filter_id, "passed": True},
        )

        await client.delete(f"{SUPABASE_URL}/rest/v1/filters?id=eq.{filter_id}", headers={**headers, "Prefer": "return=minimal"})

        gone = await wait_until_deleted(f"{SUPABASE_URL}/rest/v1/paper_filter_results?id=eq.{result_id}", headers)
        assert gone

        supabase_admin.table("papers").delete().eq("id", paper_id).execute()
