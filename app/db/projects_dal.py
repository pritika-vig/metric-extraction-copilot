# app/db/projects_dal.py
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from app.db.exceptions import DatabaseError


class ProjectDAL:
    # Data Access Control: Owner id for projects is set by supabase as the auth id.
    # It also validates permissions via auth id and RLS policies.
    def __init__(self, client):
        self.client = client

    # Retrieves a project by project id, if the user has access.
    def get_project_by_id(self, project_id: UUID) -> Optional[dict]:
        response = self.client.table("projects").select("*").eq("id", str(project_id)).single().execute()

        if response.error:
            raise DatabaseError(f"Error fetching project: {response.error}")
        return response.data

    # Creates a new project with the given description, owned by the creating user.
    def create_project(self, description: str) -> Optional[dict]:
        new_project = {"id": str(uuid4()), "description": description, "created_at": datetime.now(timezone.utc).isoformat()}
        response = self.client.table("projects").insert(new_project).execute()
        if response.error:
            raise Exception(response.error)
        return response.data[0] if response.data else None

    # Deletes a project by its id, if the user has access.
    def delete_project(self, project_id: UUID) -> bool:
        response = self.client.table("projects").delete().eq("id", str(project_id)).execute()

        if response.error and response.status_code != 404:
            raise DatabaseError(f"Error deleting project: {response.error}")

        # 204: No Content (successful delete), 200: OK (may include deleted data),
        # 404: Not Found (acceptable for idempotency)
        return response.status_code in (200, 204, 404)
