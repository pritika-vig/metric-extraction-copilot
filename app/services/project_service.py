from uuid import UUID

from app.db.exceptions import DatabaseError
from app.db.projects_dal import ProjectDAL
from app.models.project_api_models import (
    CreateProjectRequest,
    CreateProjectResponse,
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
