from uuid import UUID

from app.db.projects_dal import ProjectDAL
from app.dependencies import get_client
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
    ProjectSourceRequest,
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
    result = await service.get_project(GetProjectRequest(project_id=UUID(project_id)))
    if isinstance(result, Success):
        return result.unwrap()
    error = result.failure()
    if isinstance(error, NotFoundError):
        raise HTTPException(status_code=404, detail=error.message())
    raise HTTPException(status_code=500, detail=error.message())


@router.delete("/{project_id}", response_model=DeleteProjectResponse)
async def delete_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    result = await service.delete_project(DeleteProjectRequest(project_id=UUID(project_id)))
    if isinstance(result, Success):
        return result.unwrap()
    error = result.failure()
    if isinstance(error, NotFoundError):
        raise HTTPException(status_code=404, detail=error.message())
    raise HTTPException(status_code=500, detail=error.message())


@router.post("/{project_id}/sources", response_model=CreateProjectSourcesResponse)
async def create_project_sources(
    project_id: str,
    sources: list[ProjectSourceRequest],
    service: ProjectService = Depends(get_project_service),
):
    req = CreateProjectSourcesRequest(project_id=UUID(project_id), sources=sources)
    result = await service.create_project_sources(req)
    if isinstance(result, Success):
        return result.unwrap()
    error = result.failure()
    raise HTTPException(status_code=500, detail=error.message())


# --- Extraction Config Endpoints ---


@router.post("/configs/", response_model=CreateExtractionConfigResponse)
async def create_extraction_config(
    request: CreateExtractionConfigRequest,
    service: ProjectService = Depends(get_project_service),
):
    result = await service.create_extraction_config(request)
    if isinstance(result, Success):
        return result.unwrap()
    raise HTTPException(status_code=500, detail=result.failure().message())


@router.post("/configs/{config_id}/fields", response_model=AddExtractionFieldsResponse)
async def add_extraction_fields(
    config_id: str,
    request: AddExtractionFieldsRequest,
    service: ProjectService = Depends(get_project_service),
):
    result = await service.add_extraction_fields(UUID(config_id), request)
    if isinstance(result, Success):
        return result.unwrap()
    raise HTTPException(status_code=500, detail=result.failure().message())


@router.delete("/configs/by-project/{project_id}", response_model=DeleteExtractionConfigResponse)
async def delete_extraction_config_by_project(
    project_id: str,
    service: ProjectService = Depends(get_project_service),
):
    request = DeleteExtractionConfigRequest(project_id=UUID(project_id))
    result = await service.delete_extraction_config(request)
    if isinstance(result, Success):
        return result.unwrap()
    raise HTTPException(status_code=500, detail=result.failure().message())


@router.delete("/configs/{config_id}/fields", response_model=DeleteExtractionFieldsResponse)
async def delete_extraction_fields(
    config_id: str,
    request: DeleteExtractionFieldsRequest,
    service: ProjectService = Depends(get_project_service),
):
    result = await service.delete_extraction_fields(request)
    if isinstance(result, Success):
        return result.unwrap()
    raise HTTPException(status_code=500, detail=result.failure().message())
