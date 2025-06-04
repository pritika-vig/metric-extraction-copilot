from datetime import datetime
from typing import Optional
from uuid import UUID

from app.models.shared import ResponseStatus
from pydantic import BaseModel, Field


# Create Project endpoint
class CreateProjectRequest(BaseModel):
    description: str = Field(..., example="Exploring machine learning applications in healthcare")


class CreateProjectResponse(BaseModel):
    project_id: Optional[UUID] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    status: ResponseStatus = ResponseStatus.SUCCESS


# Get Project endpoint
class GetProjectRequest(BaseModel):
    project_id: UUID


class GetProjectResponse(BaseModel):
    project_id: Optional[UUID] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    status: ResponseStatus = ResponseStatus.SUCCESS


# Delete Project endpoint
class DeleteProjectRequest(BaseModel):
    project_id: UUID


class DeleteProjectResponse(BaseModel):
    status: ResponseStatus = ResponseStatus.SUCCESS
