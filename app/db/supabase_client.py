# app/db/supabase_client.py
import os

from supabase import create_client


def get_supabase_client_for_user(jwt: str):
    url = os.getenv("SUPABASE_PROJECT_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")

    client = create_client(url, anon_key)

    # Manually inject the Authorization header for RLS
    client.postgrest.auth(jwt)

    return client
