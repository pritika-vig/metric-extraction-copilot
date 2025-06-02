# tests/supabase/test_auth.py

import httpx
import pytest


@pytest.mark.asyncio
async def test_supabase_auth_signup(supabase_url, supabase_anon_key):
    """
    This test checks that a user can sign up using the Supabase public auth endpoint.
    - 200: New user successfully created
    - 400: User already exists (acceptable for reruns)
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{supabase_url}/auth/v1/signup",
            headers={"apikey": supabase_anon_key, "Content-Type": "application/json"},
            json={"email": "testuser@example.com", "password": "TestPass123"},
        )
        assert response.status_code in [200, 400]  # 400 = already signed up
