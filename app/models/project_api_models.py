from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.models.shared import ResponseStatus
from pydantic import BaseModel, Field


# Create Project endpoint
# Returns a project id, description, created_at timestamp and status.
class CreateProjectRequest(BaseModel):
    description: str = Field(..., example="Exploring machine learning applications in healthcare")


class CreateProjectResponse(BaseModel):
    project_id: Optional[UUID] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    status: ResponseStatus = ResponseStatus.SUCCESS


# Get Project endpoint
# Returns project, if found and permission to read.
# If not found, or no permission returns status NOT_FOUND.
class GetProjectRequest(BaseModel):
    project_id: UUID


class GetProjectResponse(BaseModel):
    project_id: Optional[UUID] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    status: ResponseStatus = ResponseStatus.SUCCESS


# Delete Project endpoint
# Returns a response status, SUCCESS if deleted,
# NOT_FOUND if project does not exist or no permission to delete.
# Else may return a different error status if deletion fails.
class DeleteProjectRequest(BaseModel):
    project_id: UUID


class DeleteProjectResponse(BaseModel):
    status: ResponseStatus = ResponseStatus.SUCCESS


# Create Project Sources
# Project Sources endpoint
# Accepts a list of source configs for a given project and returns confirmation of insertion.
class ProjectSourceRequest(BaseModel):
    backend_name: str
    backend_query: str


class CreateProjectSourcesRequest(BaseModel):
    project_id: Optional[UUID] = None
    sources: List[ProjectSourceRequest]


class CreateProjectSourcesResponse(BaseModel):
    project_id: Optional[UUID] = None
    status: ResponseStatus = ResponseStatus.SUCCESS


# Request + Response for extraction creating config with fields
class ExtractionFieldRequest(BaseModel):
    field_name: str
    description: Optional[str] = None


class CreateExtractionConfigRequest(BaseModel):
    project_id: UUID
    fields: list[ExtractionFieldRequest]


class CreateExtractionConfigResponse(BaseModel):
    config_id: UUID
    field_count: int
    status: ResponseStatus


# Delete endpoint -- delete by project id
class DeleteExtractionConfigRequest(BaseModel):
    project_id: UUID


class DeleteExtractionConfigResponse(BaseModel):
    status: ResponseStatus = ResponseStatus.SUCCESS


# For adding to existing config
class AddExtractionFieldsRequest(BaseModel):
    fields: list[ExtractionFieldRequest]


class AddExtractionFieldsResponse(BaseModel):
    status: ResponseStatus


# For Deleting fields from existing config


class DeleteExtractionFieldsRequest(BaseModel):
    field_ids: list[UUID]


class DeleteExtractionFieldsResponse(BaseModel):
    status: ResponseStatus
