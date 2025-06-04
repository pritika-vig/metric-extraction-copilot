# app/api/projects.py

from app.db.projects_dal import ProjectDAL
from app.dependencies import get_client
from app.models.project_api_models import (
    CreateProjectRequest,
    CreateProjectResponse,
    DeleteProjectRequest,
    DeleteProjectResponse,
    GetProjectRequest,
    GetProjectResponse,
)
from app.services.errors import NotFoundError
from app.services.project_service import ProjectService
from fastapi import APIRouter, Depends, HTTPException
from returns.result import Success

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_project_service(client=Depends(get_client)) -> ProjectService:
    return ProjectService(dal=ProjectDAL(client))


@router.post("/", response_model=CreateProjectResponse)
async def create_project(request: CreateProjectRequest, service: ProjectService = Depends(get_project_service)):
    result = await service.create_project(request)
    if isinstance(result, Success):
        return result.unwrap()
    error = result.failure()
    raise HTTPException(status_code=500, detail=error.message())


@router.get("/{project_id}", response_model=GetProjectResponse)
async def get_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    result = await service.get_project(GetProjectRequest(project_id=project_id))
    if isinstance(result, Success):
        return result.unwrap()
    error = result.failure()
    if isinstance(error, NotFoundError):
        raise HTTPException(status_code=404, detail=error.message())
    raise HTTPException(status_code=500, detail=error.message())


@router.delete("/{project_id}", response_model=DeleteProjectResponse)
async def delete_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    result = await service.delete_project(DeleteProjectRequest(project_id=project_id))
    if isinstance(result, Success):
        return result.unwrap()
    error = result.failure()
    if isinstance(error, NotFoundError):
        raise HTTPException(status_code=404, detail=error.message())
    raise HTTPException(status_code=500, detail=error.message())
