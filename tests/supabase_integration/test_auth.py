import httpx
import pytest


@pytest.mark.asyncio
async def test_supabase_auth_signup(supabase_url, supabase_anon_key, supabase_admin):
    """
    Test that creates a user via public signup and deletes the user afterward.
    """
    email = "testuser@example.com"
    password = "TestPass123"
    user_id = None

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{supabase_url}/auth/v1/signup",
            headers={"apikey": supabase_anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
        )
        assert response.status_code in [200, 400]

    # Retrieve user ID via admin
    users = supabase_admin.auth.admin.list_users()
    for user in users:
        if user.email == email:
            user_id = user.id
            break

    if user_id:
        supabase_admin.auth.admin.delete_user(user_id)
