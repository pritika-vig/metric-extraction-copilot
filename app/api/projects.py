from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class ProjectCreateRequest(BaseModel):
    query: str
    sources: list[str]

@router.post("/projects")
def create_project(req: ProjectCreateRequest):
    return {"project_id": "abc123", "status": "fetched"}