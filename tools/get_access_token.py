import os

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
response = client.auth.sign_in_with_password({"email": "test-user-pritikav@gmial.com", "password": "test-user-password"})
print("JWT:", response.session.access_token)
