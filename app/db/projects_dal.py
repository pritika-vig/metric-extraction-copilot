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

    # Deletes all project_sources entries for a given project
    def delete_project_sources(self, project_id: UUID) -> None:
        try:
            self.client.table("project_sources").delete().eq("project_id", str(project_id)).execute()
        except Exception as e:
            raise DatabaseError(f"Error deleting project sources: {e}")

    # Inserts multiple project_sources entries
    def insert_project_sources(self, source_rows: list[dict]) -> None:
        try:
            if not source_rows:
                return
            self.client.table("project_sources").insert(source_rows).execute()
        except Exception as e:
            raise DatabaseError(f"Error inserting project sources: {e}")

    # Creates a new extraction config for a project
    def create_extraction_config(self, project_id: UUID) -> dict:
        new_config = {"id": str(uuid4()), "project_id": str(project_id), "created_at": datetime.now(timezone.utc).isoformat()}
        try:
            response = self.client.table("extraction_configs").insert(new_config).execute()
            return response.data[0]
        except Exception as e:
            raise DatabaseError(f"Error creating extraction config: {e}")

    # Inserts an extraction field.
    def insert_extraction_fields(self, config_id: UUID, fields: list[dict]) -> None:
        try:
            for field in fields:
                field["id"] = str(uuid4())
                field["config_id"] = str(config_id)
                field["created_at"] = datetime.now(timezone.utc).isoformat()
            self.client.table("extraction_fields").insert(fields).execute()
        except Exception as e:
            raise DatabaseError(f"Error inserting extraction fields: {e}")

    # Deletes an extraction config.
    def delete_extraction_config(self, config_id: UUID) -> None:
        try:
            self.client.table("extraction_fields").delete().eq("config_id", str(config_id)).execute()
            self.client.table("extraction_configs").delete().eq("id", str(config_id)).execute()
        except Exception as e:
            raise DatabaseError(f"Error deleting extraction config: {e}")

    # Deletes a field.
    def delete_extraction_fields(self, field_ids: list[UUID]) -> None:
        try:
            str_ids = [str(fid) for fid in field_ids]
            self.client.table("extraction_fields").delete().in_("id", str_ids).execute()
        except Exception as e:
            raise DatabaseError(f"Error deleting extraction fields: {e}")
