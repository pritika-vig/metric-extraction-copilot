import asyncio
import os
import uuid
from datetime import datetime, timezone

import httpx

SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")


def headers_template(token):
    return {
        "Authorization": f"Bearer {token}",
        "apikey": SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


async def create_project(client, token, user_id):
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    headers = headers_template(token)
    resp = await client.post(
        f"{SUPABASE_URL}/rest/v1/projects",
        headers=headers,
        json={"id": project_id, "description": "test", "created_at": now},
    )
    assert resp.status_code in (200, 201)
    return project_id


async def wait_until_deleted(url, headers, max_attempts=6, delay=0.5):
    """
    Poll the given URL until it returns an empty list, indicating deletion.
    Returns True if deleted, False otherwise after retries.
    """
    async with httpx.AsyncClient() as client:
        for attempt in range(max_attempts):
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200 and resp.json() == []:
                return True
            await asyncio.sleep(delay)
            delay *= 1.5  # exponential backoff
        # Optional: Log response body for easier debugging
        print(f"⚠️  Not deleted after {max_attempts} tries: {url} => {resp.json()}")
        return False
