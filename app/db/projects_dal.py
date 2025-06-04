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
        try:
            response = self.client.table("projects").select("*").eq("id", str(project_id)).limit(1).execute()
            if not response.data:
                return None
            return response.data[0]
        except Exception as e:
            raise DatabaseError(f"Error fetching project: {e}")

    # Creates a new project with the given description, owned by the creating user.
    def create_project(self, description: str) -> Optional[dict]:
        new_project = {"id": str(uuid4()), "description": description, "created_at": datetime.now(timezone.utc).isoformat()}

        try:
            response = self.client.table("projects").insert(new_project).execute()
            if not response.data:
                raise DatabaseError("Insert returned empty data")
            return response.data[0]
        except Exception as e:
            raise DatabaseError(f"Error inserting project: {e}")

    # Deletes a project by its id, if the user has access.
    def delete_project(self, project_id: UUID) -> bool:
        try:
            response = self.client.table("projects").delete().eq("id", str(project_id)).execute()
            return bool(response.data)
        except Exception as e:
            raise DatabaseError(f"Error deleting project: {e}")
