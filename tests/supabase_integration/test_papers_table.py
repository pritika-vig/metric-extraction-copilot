# tests/supabase/test_papers.py

import asyncio
import uuid
from datetime import datetime, timezone

import httpx
import pytest

from tests.supabase_integration.utils import SUPABASE_URL, create_project, headers_template


@pytest.mark.asyncio
async def test_papers_crud(test_user):
    """
    A user can create and read papers associated with their own project.
    """
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        paper_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        # Insert a paper
        insert_resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "My Paper", "abstract": "My abstract"},
        )
        assert insert_resp.status_code in (200, 201), insert_resp.text

        # Read the paper back
        read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{paper_id}", headers=headers)
        assert read_resp.status_code == 200
        papers = read_resp.json()
        assert len(papers) == 1
        assert papers[0]["id"] == paper_id


@pytest.mark.asyncio
async def test_user_cannot_access_others_papers(test_user, supabase_admin):
    """
    Ensure a user cannot access another user's papers due to RLS policy.
    """
    other_user = supabase_admin.auth.admin.create_user(
        {"email": f"other_{uuid.uuid4().hex[:6]}@example.com", "password": "TestPass123", "email_confirm": True}
    ).user

    paper_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Insert project and paper for other user
    supabase_admin.table("projects").insert({"id": project_id, "owner_id": other_user.id, "query": "test", "created_at": now}).execute()

    supabase_admin.table("papers").insert({"id": paper_id, "project_id": project_id, "title": "Other's Paper", "abstract": "Hidden"}).execute()

    # Attempt to read as test_user
    headers = headers_template(test_user["token"])
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{paper_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_deleting_project_cascades_papers(test_user):
    """
    When a project is deleted, all associated papers should be automatically deleted.
    """
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        paper_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        # Insert paper
        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "Cascade", "abstract": "Test"},
        )

        # Delete project
        del_resp = await client.delete(
            f"{SUPABASE_URL}/rest/v1/projects?id=eq.{project_id}", headers={**headers, "Prefer": "return=minimal"}  # <-- makes response 204
        )
        assert del_resp.status_code == 204

        # Retry loop: check up to 5 times with 0.5s delay
        for _ in range(5):
            read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{paper_id}", headers=headers)
            assert read_resp.status_code == 200
            if read_resp.json() == []:
                break  # ✅ success
            await asyncio.sleep(0.5)
        else:
            assert False, f"Paper {paper_id} still exists after project {project_id} deletion for user {test_user['id']}"


@pytest.mark.asyncio
async def test_user_cannot_insert_paper_to_others_project(test_user, supabase_admin):
    """
    Users should not be able to insert papers into a project they don't own (RLS write enforcement).
    """
    # Create another user with a project
    other_user = supabase_admin.auth.admin.create_user(
        {"email": f"other_{uuid.uuid4().hex[:6]}@example.com", "password": "TestPass123", "email_confirm": True}
    ).user

    project_id = str(uuid.uuid4())

    supabase_admin.table("projects").insert(
        {"id": project_id, "owner_id": other_user.id, "query": "other project", "created_at": datetime.now(timezone.utc).isoformat()}
    ).execute()

    # Attempt to insert a paper into that project as the test user
    headers = headers_template(test_user["token"])
    paper_id = str(uuid.uuid4())

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "Bad Write", "abstract": "Blocked"},
        )
        assert resp.status_code == 403  # RLS should forbid this


@pytest.mark.asyncio
async def test_deleting_paper_cascades_extracted_and_filter_results(test_user):
    """Deleting a paper deletes its extracted_fields and paper_filter_results."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        paper_id = str(uuid.uuid4())
        config_id = str(uuid.uuid4())
        field_id = str(uuid.uuid4())
        extract_id = str(uuid.uuid4())
        filter_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])
        now = datetime.now(timezone.utc).isoformat()

        # Create required entities
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_configs", headers=headers, json={"id": config_id, "project_id": project_id, "created_at": now}
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_fields",
            headers=headers,
            json={"id": field_id, "config_id": config_id, "field_name": "Field", "description": "Desc", "created_at": now},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "To Delete", "abstract": "..."},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extracted_fields",
            headers=headers,
            json={"id": extract_id, "paper_id": paper_id, "extraction_field_id": field_id, "field_value": "Alice"},
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

        # Delete the paper
        del_resp = await client.delete(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{paper_id}", headers={**headers, "Prefer": "return=minimal"})
        assert del_resp.status_code == 204

        # Confirm extracted field and filter result are deleted
        async def is_deleted(endpoint):
            for _ in range(5):
                resp = await client.get(endpoint, headers=headers)
                if resp.status_code == 200 and resp.json() == []:
                    return True
                await asyncio.sleep(0.5)
            return False

        assert await is_deleted(f"{SUPABASE_URL}/rest/v1/extracted_fields?id=eq.{extract_id}"), f"extracted_field {extract_id} not deleted"
        assert await is_deleted(f"{SUPABASE_URL}/rest/v1/paper_filter_results?id=eq.{result_id}"), f"paper_filter_result {result_id} not deleted"
