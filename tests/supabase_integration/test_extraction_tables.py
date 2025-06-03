import uuid
from datetime import datetime, timezone

import httpx
import pytest

from tests.supabase_integration.utils import SUPABASE_URL, create_project, headers_template, wait_until_deleted


@pytest.mark.asyncio
async def test_extraction_configs_crud(test_extraction_config, test_user):
    headers = headers_template(test_user["token"])
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/extraction_configs?id=eq.{test_extraction_config}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_extraction_fields_crud(test_extraction_field, test_user):
    headers = headers_template(test_user["token"])
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/extraction_fields?id=eq.{test_extraction_field}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_extracted_fields_crud(test_extracted_field, test_user):
    headers = headers_template(test_user["token"])
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/extracted_fields?id=eq.{test_extracted_field}", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_user_cannot_access_others_extraction_configs(test_user, other_user_with_extraction_data):
    """test_user should NOT access another user's extraction_configs."""
    config_id = other_user_with_extraction_data["config_id"]
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/extraction_configs?id=eq.{config_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_user_cannot_access_others_extracted_fields(test_user, other_user_with_extraction_data):
    """test_user should NOT access another user's extracted_fields."""
    extract_id = other_user_with_extraction_data["extract_id"]
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/extracted_fields?id=eq.{extract_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_deleting_project_cascades_extraction_configs(test_user):
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        config_id = str(uuid.uuid4())
        field_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        # Create config and field
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_configs",
            headers=headers,
            json={"id": config_id, "project_id": project_id, "created_at": datetime.now(timezone.utc).isoformat()},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_fields",
            headers=headers,
            json={"id": field_id, "config_id": config_id, "field_name": "Author", "description": "Extract Author"},
        )

        # Delete project
        del_resp = await client.delete(
            f"{SUPABASE_URL}/rest/v1/projects?id=eq.{project_id}", headers={**headers, "Prefer": "return=minimal"}  # Ensures 204 response
        )
        assert del_resp.status_code == 204
        # Use retry to wait until the child records are gone
        config_gone = await wait_until_deleted(f"{SUPABASE_URL}/rest/v1/extraction_configs?id=eq.{config_id}", headers)
        field_gone = await wait_until_deleted(f"{SUPABASE_URL}/rest/v1/extraction_fields?id=eq.{field_id}", headers)
        assert config_gone, f"Extraction config {config_id} still exists after project {project_id} deletion, {test_user['id']}"
        assert field_gone, f"Extraction field {field_id} still exists after project {project_id} deletion"


@pytest.mark.asyncio
async def test_user_cannot_write_to_others_paper(test_user, other_user_with_extraction_data):
    """test_user should be blocked from writing to another user's paper via extracted_fields insert."""
    extract_id = str(uuid.uuid4())
    paper_id = other_user_with_extraction_data["paper_id"]
    field_id = other_user_with_extraction_data["field_id"]
    headers = headers_template(test_user["token"])

    async with httpx.AsyncClient() as client:
        insert_resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/extracted_fields",
            headers=headers,
            json={"id": extract_id, "paper_id": paper_id, "extraction_field_id": field_id, "field_value": "X"},
        )
        assert insert_resp.status_code == 403

        read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/extracted_fields?id=eq.{extract_id}", headers=headers)
        assert read_resp.status_code == 200
        assert read_resp.json() == []


@pytest.mark.asyncio
async def test_deleting_config_cascades_fields_and_extracted(test_user):
    """Deleting an extraction_config deletes its extraction_fields and downstream extracted_fields."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        config_id = str(uuid.uuid4())
        field_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        extract_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        now = datetime.now(timezone.utc).isoformat()

        # Create config
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_configs", headers=headers, json={"id": config_id, "project_id": project_id, "created_at": now}
        )

        # Create field
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_fields",
            headers=headers,
            json={"id": field_id, "config_id": config_id, "field_name": "X", "description": "Y", "created_at": now},
        )

        # Create paper
        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "Test", "abstract": "..."},
        )

        # Create extracted field
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extracted_fields",
            headers=headers,
            json={"id": extract_id, "paper_id": paper_id, "extraction_field_id": field_id, "field_value": "Z"},
        )

        # Delete config
        del_resp = await client.delete(
            f"{SUPABASE_URL}/rest/v1/extraction_configs?id=eq.{config_id}", headers={**headers, "Prefer": "return=minimal"}
        )
        assert del_resp.status_code == 204

        # Check cascades
        field_gone = await wait_until_deleted(f"{SUPABASE_URL}/rest/v1/extraction_fields?id=eq.{field_id}", headers)
        extract_gone = await wait_until_deleted(f"{SUPABASE_URL}/rest/v1/extracted_fields?id=eq.{extract_id}", headers)
        assert field_gone, f"Extraction field {field_id} not deleted after config {config_id}"
        assert extract_gone, f"Extracted field {extract_id} not deleted after config {config_id}"


@pytest.mark.asyncio
async def test_deleting_field_cascades_extracted(test_user):
    """Deleting an extraction_field deletes associated extracted_fields."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        config_id = str(uuid.uuid4())
        field_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        extract_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        now = datetime.now(timezone.utc).isoformat()

        # Setup config and field
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_configs", headers=headers, json={"id": config_id, "project_id": project_id, "created_at": now}
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_fields",
            headers=headers,
            json={"id": field_id, "config_id": config_id, "field_name": "F", "description": "Desc", "created_at": now},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "Paper", "abstract": "Abstract"},
        )
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extracted_fields",
            headers=headers,
            json={"id": extract_id, "paper_id": paper_id, "extraction_field_id": field_id, "field_value": "Data"},
        )

        # Delete field
        del_resp = await client.delete(
            f"{SUPABASE_URL}/rest/v1/extraction_fields?id=eq.{field_id}", headers={**headers, "Prefer": "return=minimal"}
        )
        assert del_resp.status_code == 204

        extract_gone = await wait_until_deleted(f"{SUPABASE_URL}/rest/v1/extracted_fields?id=eq.{extract_id}", headers)
        assert extract_gone, f"Extracted field {extract_id} still exists after deleting field {field_id}"


@pytest.mark.asyncio
async def test_user_cannot_update_extraction_field(test_extraction_field, test_user):
    headers = headers_template(test_user["token"])
    async with httpx.AsyncClient() as client:
        update_resp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/extraction_fields?id=eq.{test_extraction_field}", headers=headers, json={"field_name": "Hacked"}
        )
        assert update_resp.status_code == 403  # Forbidden due to RLS

        read_resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/extraction_fields?id=eq.{test_extraction_field}",
            headers=headers,
        )
        assert read_resp.status_code == 200
        data = read_resp.json()
        assert len(data) == 1
        assert data[0]["field_name"] == "Author"
