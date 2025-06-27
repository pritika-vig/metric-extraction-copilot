from uuid import UUID, uuid4

from app.db.exceptions import DatabaseError
from app.db.projects_dal import ProjectDAL
from app.models.project_api_models import (
    AddExtractionFieldsRequest,
    AddExtractionFieldsResponse,
    CreateExtractionConfigRequest,
    CreateExtractionConfigResponse,
    CreateProjectRequest,
    CreateProjectResponse,
    CreateProjectSourcesRequest,
    CreateProjectSourcesResponse,
    DeleteExtractionConfigRequest,
    DeleteExtractionConfigResponse,
    DeleteExtractionFieldsRequest,
    DeleteExtractionFieldsResponse,
    DeleteProjectRequest,
    DeleteProjectResponse,
    GetProjectRequest,
    GetProjectResponse,
)
from app.models.shared import ResponseStatus
from app.services.errors import InternalServiceError, ProjectServiceError
from returns.result import Failure, Result, Success


class ProjectService:
    def __init__(self, dal: ProjectDAL):
        self.dal = dal

    async def create_project(self, request: CreateProjectRequest) -> Result[CreateProjectResponse, ProjectServiceError]:
        try:
            result = self.dal.create_project(description=request.description)

            if not result:
                return Success(
                    CreateProjectResponse(
                        project_id=UUID(int=0), description=request.description, created_at=None, status=ResponseStatus.DEGRADED
                    )
                )

            return Success(
                CreateProjectResponse(
                    project_id=result["id"], description=result["description"], created_at=result["created_at"], status=ResponseStatus.SUCCESS
                )
            )

        except DatabaseError as e:
            return Failure(InternalServiceError(f"Database error during creation: {e}"))

        except Exception as e:
            return Failure(InternalServiceError(f"Unhandled error during creation: {e}"))

    async def get_project(self, request: GetProjectRequest) -> Result[GetProjectResponse, ProjectServiceError]:
        try:
            result = self.dal.get_project_by_id(project_id=request.project_id)

            if result is None:
                return Success(
                    GetProjectResponse(project_id=request.project_id, description="", created_at=None, status=ResponseStatus.NOT_FOUND)
                )

            return Success(
                GetProjectResponse(
                    project_id=result["id"], description=result["description"], created_at=result["created_at"], status=ResponseStatus.SUCCESS
                )
            )

        except DatabaseError as e:
            return Failure(InternalServiceError(f"Database error during fetch: {e}"))

        except Exception as e:
            return Failure(InternalServiceError(f"Unhandled error during fetch: {e}"))

    async def delete_project(self, request: DeleteProjectRequest) -> Result[DeleteProjectResponse, ProjectServiceError]:
        try:
            success = self.dal.delete_project(project_id=request.project_id)

            if success:
                return Success(DeleteProjectResponse(status=ResponseStatus.SUCCESS))
            else:
                return Success(DeleteProjectResponse(status=ResponseStatus.NOT_FOUND))

        except DatabaseError as e:
            return Failure(InternalServiceError(f"Database error during deletion: {e}"))

        except Exception as e:
            return Failure(InternalServiceError(f"Unhandled error during deletion: {e}"))

    async def create_project_sources(self, request: CreateProjectSourcesRequest) -> Result[CreateProjectSourcesResponse, ProjectServiceError]:
        try:
            # Step 1: Verify project exists
            project = self.dal.get_project_by_id(project_id=request.project_id)
            if project is None:
                return Success(CreateProjectSourcesResponse(project_id=request.project_id, source_count=0, status=ResponseStatus.NOT_FOUND))

            # Step 2: Delete existing sources
            self.dal.delete_project_sources(project_id=request.project_id)

            # Step 3: Insert new sources
            sources_payload = [
                {
                    "id": str(uuid4()),
                    "project_id": str(request.project_id),
                    "backend_name": source.backend_name,
                    "backend_query": source.backend_query,
                }
                for source in request.sources
            ]

            self.dal.insert_project_sources(sources_payload)

            return Success(
                CreateProjectSourcesResponse(project_id=request.project_id, source_count=len(sources_payload), status=ResponseStatus.SUCCESS)
            )

        except DatabaseError as e:
            return Failure(InternalServiceError(f"Database error during source update: {e}"))

        except Exception as e:
            return Failure(InternalServiceError(f"Unhandled error during source update: {e}"))

    async def create_extraction_config(
        self, request: CreateExtractionConfigRequest
    ) -> Result[CreateExtractionConfigResponse, ProjectServiceError]:
        try:
            # Check if config already exists (optional if enforced in DB)
            existing = self.dal.client.table("extraction_configs").select("*").eq("project_id", str(request.project_id)).limit(1).execute()
            if existing.data:
                return Failure(ProjectServiceError("Extraction config already exists for this project."))

            config = self.dal.create_extraction_config(project_id=request.project_id)

            field_dicts = [{"field_name": f.field_name, "description": f.description} for f in request.fields]

            self.dal.insert_extraction_fields(config_id=UUID(config["id"]), fields=field_dicts)

            return Success(
                CreateExtractionConfigResponse(config_id=UUID(config["id"]), field_count=len(field_dicts), status=ResponseStatus.SUCCESS)
            )

        except Exception as e:
            return Failure(InternalServiceError(f"Error creating extraction config: {e}"))

    async def add_extraction_fields(
        self, config_id: UUID, request: AddExtractionFieldsRequest
    ) -> Result[AddExtractionFieldsResponse, ProjectServiceError]:
        try:
            field_dicts = [{"field_name": f.field_name, "description": f.description} for f in request.fields]

            self.dal.insert_extraction_fields(config_id=config_id, fields=field_dicts)

            return Success(AddExtractionFieldsResponse(status=ResponseStatus.SUCCESS))

        except Exception as e:
            return Failure(InternalServiceError(f"Error adding extraction fields: {e}"))

    async def delete_extraction_config(
        self, request: DeleteExtractionConfigRequest
    ) -> Result[DeleteExtractionConfigResponse, ProjectServiceError]:
        try:
            # Get config ID by project_id
            response = self.dal.client.table("extraction_configs").select("id").eq("project_id", str(request.project_id)).limit(1).execute()
            if not response.data:
                return Success(DeleteExtractionConfigResponse(status=ResponseStatus.NOT_FOUND))

            config_id = UUID(response.data[0]["id"])
            self.dal.delete_extraction_config(config_id=config_id)

            return Success(DeleteExtractionConfigResponse(status=ResponseStatus.SUCCESS))

        except Exception as e:
            return Failure(InternalServiceError(f"Error deleting extraction config: {e}"))

    async def delete_extraction_fields(
        self, request: DeleteExtractionFieldsRequest
    ) -> Result[DeleteExtractionFieldsRequest, ProjectServiceError]:
        try:
            self.dal.delete_extraction_fields(field_ids=request.field_ids)
            return Success(DeleteExtractionFieldsResponse(status=ResponseStatus.SUCCESS))
        except Exception as e:
            return Failure(InternalServiceError(f"Error deleting extraction fields: {e}"))
