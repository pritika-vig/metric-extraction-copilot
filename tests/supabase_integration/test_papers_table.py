# tests/supabase/test_papers.py

import asyncio
import uuid

import httpx
import pytest

from tests.supabase_integration.utils import SUPABASE_URL, headers_template


@pytest.mark.asyncio
async def test_papers_crud(test_user, test_paper):
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{test_paper}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_user_cannot_access_others_papers(test_user, other_user_paper):
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{other_user_paper}", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_deleting_project_cascades_papers(test_user, test_project):
    async with httpx.AsyncClient() as client:
        paper_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": test_project, "title": "Cascade", "abstract": "Test"},
        )

        await client.delete(f"{SUPABASE_URL}/rest/v1/projects?id=eq.{test_project}", headers={**headers, "Prefer": "return=minimal"})

        for _ in range(5):
            resp = await client.get(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{paper_id}", headers=headers)
            if resp.status_code == 200 and resp.json() == []:
                break
            await asyncio.sleep(0.5)
        else:
            assert False, f"Paper {paper_id} still exists after project {test_project} was deleted"


@pytest.mark.asyncio
async def test_user_cannot_insert_paper_to_others_project(test_user, other_user_with_project):
    _, project_id = other_user_with_project
    headers = headers_template(test_user["token"])
    paper_id = str(uuid.uuid4())

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "Bad Write", "abstract": "Blocked"},
        )
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_deleting_paper_cascades_extracted_and_filter_results(test_user, test_project, paper_dependencies_for_cascade):
    ids = paper_dependencies_for_cascade
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": ids["paper"], "project_id": test_project, "title": "To Delete", "abstract": "..."},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extracted_fields",
            headers=headers,
            json={"id": ids["extract"], "paper_id": ids["paper"], "extraction_field_id": ids["field"], "field_value": "Alice"},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/paper_filter_results",
            headers=headers,
            json={"id": ids["result"], "paper_id": ids["paper"], "filter_id": ids["filter"], "passed": True},
        )

        await client.delete(f"{SUPABASE_URL}/rest/v1/papers?id=eq.{ids['paper']}", headers={**headers, "Prefer": "return=minimal"})

        async def is_deleted(endpoint):
            for _ in range(5):
                resp = await client.get(endpoint, headers=headers)
                if resp.status_code == 200 and resp.json() == []:
                    return True
                await asyncio.sleep(0.5)
            return False

        assert await is_deleted(f"{SUPABASE_URL}/rest/v1/extracted_fields?id=eq.{ids['extract']}")
        assert await is_deleted(f"{SUPABASE_URL}/rest/v1/paper_filter_results?id=eq.{ids['result']}")
