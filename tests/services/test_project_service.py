from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from app.db.exceptions import DatabaseError
from app.models.project_api_models import CreateProjectRequest, DeleteProjectRequest, GetProjectRequest
from app.models.shared import ResponseStatus
from app.services.errors import InternalServiceError
from app.services.project_service import ProjectService
from returns.result import Failure, Success


class MockDAL:
    def __init__(self):
        self.store = {}

    def create_project(self, description):
        project_id = uuid4()
        now = datetime.now(timezone.utc)
        self.store[str(project_id)] = {
            "id": str(project_id),
            "description": description,
            "created_at": now,
        }
        return self.store[str(project_id)]

    def get_project_by_id(self, project_id):
        return self.store.get(str(project_id), None)

    def delete_project(self, project_id):
        return self.store.pop(str(project_id), None) is not None


@pytest.fixture
def service():
    return ProjectService(dal=MockDAL())


@pytest.mark.asyncio
async def test_create_project_success(service):
    req = CreateProjectRequest(description="Testing Project")
    result = await service.create_project(req)
    assert isinstance(result, Success)
    response = result.unwrap()
    assert response.description == "Testing Project"
    assert isinstance(UUID(str(response.project_id)), UUID)
    assert isinstance(response.created_at, datetime)
    assert response.status == ResponseStatus.SUCCESS


@pytest.mark.asyncio
async def test_create_project_degraded(service):
    class DegradedDAL(MockDAL):
        def create_project(self, description):
            return None

    degraded_service = ProjectService(dal=DegradedDAL())
    req = CreateProjectRequest(description="Should degrade")
    result = await degraded_service.create_project(req)
    assert isinstance(result, Success)
    response = result.unwrap()
    assert response.status == ResponseStatus.DEGRADED


@pytest.mark.asyncio
async def test_create_project_failure():
    class FailingDAL:
        def create_project(self, description):
            raise DatabaseError("Insert failed")

    service = ProjectService(dal=FailingDAL())
    req = CreateProjectRequest(description="Will fail")
    result = await service.create_project(req)
    assert isinstance(result, Failure)
    error = result.failure()
    assert isinstance(error, InternalServiceError)


@pytest.mark.asyncio
async def test_get_project_success(service):
    created = service.dal.create_project("Saved project")
    req = GetProjectRequest(project_id=UUID(created["id"]))
    result = await service.get_project(req)
    assert isinstance(result, Success)
    response = result.unwrap()
    assert response.project_id == UUID(created["id"])
    assert response.description == "Saved project"
    assert response.status == ResponseStatus.SUCCESS


@pytest.mark.asyncio
async def test_get_project_not_found(service):
    req = GetProjectRequest(project_id=uuid4())
    result = await service.get_project(req)
    assert isinstance(result, Success)
    response = result.unwrap()
    assert response.status == ResponseStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_get_project_failure():
    class FailingDAL:
        def get_project_by_id(self, project_id):
            raise DatabaseError("Fetch error")

    service = ProjectService(dal=FailingDAL())
    req = GetProjectRequest(project_id=uuid4())
    result = await service.get_project(req)
    assert isinstance(result, Failure)
    error = result.failure()
    assert isinstance(error, InternalServiceError)


@pytest.mark.asyncio
async def test_delete_project_success(service):
    created = service.dal.create_project("Project to delete")
    req = DeleteProjectRequest(project_id=UUID(created["id"]))
    result = await service.delete_project(req)
    assert isinstance(result, Success)
    response = result.unwrap()
    assert response.status == ResponseStatus.SUCCESS


@pytest.mark.asyncio
async def test_delete_project_not_found(service):
    req = DeleteProjectRequest(project_id=uuid4())
    result = await service.delete_project(req)
    assert isinstance(result, Success)
    response = result.unwrap()
    assert response.status == ResponseStatus.NOT_FOUND


@pytest.mark.asyncio
async def test_delete_project_failure():
    class FailingDAL:
        def delete_project(self, project_id):
            raise DatabaseError("Delete failed")

    service = ProjectService(dal=FailingDAL())
    req = DeleteProjectRequest(project_id=uuid4())
    result = await service.delete_project(req)
    assert isinstance(result, Failure)
    error = result.failure()
    assert isinstance(error, InternalServiceError)
