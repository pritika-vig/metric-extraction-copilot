import uuid
from datetime import datetime, timezone

import httpx
import pytest

from tests.supabase_integration.utils import SUPABASE_URL, create_project, headers_template, wait_until_deleted


@pytest.mark.asyncio
async def test_extraction_configs_crud(test_user):
    """Owners can create and read their own extraction_configs."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        config_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        insert_resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_configs",
            headers=headers,
            json={"id": config_id, "project_id": project_id, "created_at": datetime.now(timezone.utc).isoformat()},
        )
        assert insert_resp.status_code in (200, 201)

        read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/extraction_configs?id=eq.{config_id}", headers=headers)
        assert read_resp.status_code == 200
        assert len(read_resp.json()) == 1


@pytest.mark.asyncio
async def test_extraction_fields_crud(test_user):
    """Owners can create and read their own extraction_fields."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        config_id = str(uuid.uuid4())
        field_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        # Insert config first
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_configs",
            headers=headers,
            json={"id": config_id, "project_id": project_id, "created_at": datetime.now(timezone.utc).isoformat()},
        )

        # Then insert field
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_fields",
            headers=headers,
            json={"id": field_id, "config_id": config_id, "field_name": "Author", "description": "Extract Author"},
        )
        assert resp.status_code in (200, 201)

        read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/extraction_fields?id=eq.{field_id}", headers=headers)
        assert read_resp.status_code == 200
        assert len(read_resp.json()) == 1


@pytest.mark.asyncio
async def test_extracted_fields_crud(test_user):
    """Owners can insert and read extracted_fields related to their papers."""
    async with httpx.AsyncClient() as client:
        project_id = await create_project(client, test_user["token"], test_user["id"])
        config_id = str(uuid.uuid4())
        field_id = str(uuid.uuid4())
        paper_id = str(uuid.uuid4())
        extract_id = str(uuid.uuid4())
        headers = headers_template(test_user["token"])

        # Setup config
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_configs",
            headers=headers,
            json={"id": config_id, "project_id": project_id, "created_at": datetime.now(timezone.utc).isoformat()},
        )

        # Setup field
        await client.post(
            f"{SUPABASE_URL}/rest/v1/extraction_fields",
            headers=headers,
            json={"id": field_id, "config_id": config_id, "field_name": "Author", "description": "Extract Author"},
        )

        # Setup paper
        await client.post(
            f"{SUPABASE_URL}/rest/v1/papers",
            headers=headers,
            json={"id": paper_id, "project_id": project_id, "title": "Paper", "abstract": "Text"},
        )

        # Insert extracted field value
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/extracted_fields",
            headers=headers,
            json={"id": extract_id, "paper_id": paper_id, "extraction_field_id": field_id, "field_value": "Dr. Alice"},
        )
        assert resp.status_code in (200, 201)

        # Read back
        read_resp = await client.get(f"{SUPABASE_URL}/rest/v1/extracted_fields?id=eq.{extract_id}", headers=headers)
        assert read_resp.status_code == 200
        assert len(read_resp.json()) == 1


@pytest.mark.asyncio
async def test_user_cannot_access_others_extraction_configs(test_user, supabase_admin):
    """Enforces RLS: test_user should NOT access another user's extraction_configs."""
    other_user = supabase_admin.auth.admin.create_user(
        {"email": f"owner_{uuid.uuid4().hex[:6]}@example.com", "password": "TestPass123", "email_confirm": True}
    ).user

    project_id = str(uuid.uuid4())
    config_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    supabase_admin.table("projects").insert({"id": project_id, "owner_id": other_user.id, "query": "test", "created_at": now}).execute()

    supabase_admin.table("extraction_configs").insert({"id": config_id, "project_id": project_id, "created_at": now}).execute()

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/rest/v1/extraction_configs?id=eq.{config_id}", headers=headers_template(test_user["token"]))
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_user_cannot_access_others_extracted_fields(test_user, supabase_admin):
    """
    Ensure a user cannot access another user's extracted_fields data.
    """
    other_user = supabase_admin.auth.admin.create_user(
        {"email": f"owner_{uuid.uuid4().hex[:6]}@example.com", "password": "TestPass123", "email_confirm": True}
    ).user

    extract_id = str(uuid.uuid4())
    field_id = str(uuid.uuid4())
    paper_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())
    config_id = str(uuid.uuid4())

    now = datetime.now(timezone.utc).isoformat()

    supabase_admin.table("projects").insert({"id": project_id, "owner_id": other_user.id, "query": "test", "created_at": now}).execute()

    supabase_admin.table("extraction_configs").insert({"id": config_id, "project_id": project_id, "created_at": now}).execute()

    supabase_admin.table("extraction_fields").insert(
        {"id": field_id, "config_id": config_id, "field_name": "Author", "description": "Extract Author", "created_at": now}
    ).execute()

    supabase_admin.table("papers").insert(
        {"id": paper_id, "project_id": project_id, "title": "Hidden Paper", "abstract": "Confidential"}
    ).execute()

    supabase_admin.table("extracted_fields").insert(
        {"id": extract_id, "paper_id": paper_id, "extraction_field_id": field_id, "field_value": "Dr. X"}
    ).execute()

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
async def test_user_cannot_write_to_others_paper(test_user, supabase_admin):
    """
    Attempt to insert extracted_fields into a paper not owned by the user. Should fail silently (RLS blocked).
    """
    # Create other user's paper and field
    other_user = supabase_admin.auth.admin.create_user(
        {"email": f"other_{uuid.uuid4().hex[:6]}@example.com", "password": "TestPass123", "email_confirm": True}
    ).user
    now = datetime.now(timezone.utc).isoformat()
    project_id = str(uuid.uuid4())
    paper_id = str(uuid.uuid4())
    config_id = str(uuid.uuid4())
    field_id = str(uuid.uuid4())
    extract_id = str(uuid.uuid4())

    supabase_admin.table("projects").insert({"id": project_id, "owner_id": other_user.id, "query": "q", "created_at": now}).execute()
    supabase_admin.table("extraction_configs").insert({"id": config_id, "project_id": project_id, "created_at": now}).execute()
    supabase_admin.table("extraction_fields").insert(
        {"id": field_id, "config_id": config_id, "field_name": "Test", "description": "Desc", "created_at": now}
    ).execute()
    supabase_admin.table("papers").insert({"id": paper_id, "project_id": project_id, "title": "Hidden", "abstract": "Secret"}).execute()

    # Attempt to insert extracted field (should be blocked by RLS)
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/extracted_fields",
            headers=headers_template(test_user["token"]),
            json={"id": extract_id, "paper_id": paper_id, "extraction_field_id": field_id, "field_value": "X"},
        )
        assert resp.status_code == 403  # Rejected

        # We should not be able to read it
        read = await client.get(f"{SUPABASE_URL}/rest/v1/extracted_fields?id=eq.{extract_id}", headers=headers_template(test_user["token"]))
        assert read.status_code == 200
        assert read.json() == []


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
