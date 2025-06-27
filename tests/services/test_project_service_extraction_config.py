from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from app.db.exceptions import DatabaseError
from app.models.project_api_models import (
    AddExtractionFieldsRequest,
    CreateExtractionConfigRequest,
    DeleteExtractionConfigRequest,
    DeleteExtractionFieldsRequest,
    ExtractionFieldRequest,
)
from app.models.shared import ResponseStatus
from app.services.errors import InternalServiceError, ProjectServiceError
from app.services.project_service import ProjectService
from returns.result import Failure, Success


# --- Mock DAL for service-level testing ---
class MockDAL:
    def __init__(self):
        self.configs = {}
        self.fields = {}

    def create_extraction_config(self, project_id):
        if str(project_id) in self.configs:
            raise DatabaseError("duplicate key value violates unique constraint")
        config_id = str(uuid4())
        config = {"id": config_id, "project_id": str(project_id), "created_at": datetime.now(timezone.utc).isoformat()}
        self.configs[str(project_id)] = config
        return config

    def insert_extraction_fields(self, config_id, fields):
        if not fields:
            return
        if str(config_id) not in self.fields:
            self.fields[str(config_id)] = []
        self.fields[str(config_id)].extend(fields)

    def delete_extraction_config(self, config_id):
        self.fields.pop(str(config_id), None)
        for pid, config in list(self.configs.items()):
            if config["id"] == str(config_id):
                del self.configs[pid]

    def delete_extraction_fields(self, field_ids):
        found = False
        for field_list in self.fields.values():
            before = len(field_list)
            field_list[:] = [f for f in field_list if f.get("id") not in [str(fid) for fid in field_ids]]
            after = len(field_list)
            if before != after:
                found = True
        if not found:
            raise DatabaseError("No matching field IDs")

    @property
    def client(self):
        class DummyClient:
            def table(inner_self, name):
                class Table:
                    def __init__(self):
                        self.filter_value = None  # renamed to avoid underscore clash

                    def select(self, *args):
                        return self

                    def eq(self, field, value):
                        self.filter_value = value
                        return self

                    def limit(self, value):
                        return self

                    def execute(inner_self2):
                        # Use outer self (`self` of MockDAL)
                        for cfg in self.configs.values():
                            if cfg["project_id"] == inner_self2.filter_value:
                                return type("R", (), {"data": [cfg]})
                        return type("R", (), {"data": []})

                return Table()

        return DummyClient()


@pytest.fixture
def service():
    return ProjectService(dal=MockDAL())


# Test creating a new extraction config with fields
@pytest.mark.asyncio
async def test_create_extraction_config_success(service):
    project_id = uuid4()
    req = CreateExtractionConfigRequest(
        project_id=project_id,
        fields=[
            ExtractionFieldRequest(field_name="title", description="The title field"),
            ExtractionFieldRequest(field_name="authors"),
        ],
    )
    result = await service.create_extraction_config(req)
    assert isinstance(result, Success)
    response = result.unwrap()
    assert response.config_id
    assert response.field_count == 2
    assert response.status == ResponseStatus.SUCCESS


# Test trying to create an extraction config for a project that already has one (unique constraint error)
@pytest.mark.asyncio
async def test_create_extraction_config_duplicate(service):
    project_id = uuid4()
    await service.create_extraction_config(CreateExtractionConfigRequest(project_id=project_id, fields=[]))
    req = CreateExtractionConfigRequest(project_id=project_id, fields=[])
    result = await service.create_extraction_config(req)
    assert isinstance(result, Failure)
    assert isinstance(result.failure(), ProjectServiceError)


# Test adding extraction fields to an existing config
@pytest.mark.asyncio
async def test_add_extraction_fields_success(service):
    project_id = uuid4()
    creation = await service.create_extraction_config(CreateExtractionConfigRequest(project_id=project_id, fields=[]))
    config_id = creation.unwrap().config_id

    req = AddExtractionFieldsRequest(fields=[ExtractionFieldRequest(field_name="abstract")])

    result = await service.add_extraction_fields(config_id=config_id, request=req)
    assert isinstance(result, Success)
    assert result.unwrap().status == ResponseStatus.SUCCESS


# Test handling failure when adding extraction fields
@pytest.mark.asyncio
async def test_add_extraction_fields_failure():
    class FailingInsertDAL(MockDAL):
        def insert_extraction_fields(self, config_id, fields):
            raise DatabaseError("Insert failed")

    service = ProjectService(dal=FailingInsertDAL())
    req = AddExtractionFieldsRequest(fields=[ExtractionFieldRequest(field_name="fail")])
    result = await service.add_extraction_fields(uuid4(), req)
    assert isinstance(result, Failure)
    assert isinstance(result.failure(), InternalServiceError)


# Test deleting specific extraction fields by their IDs
@pytest.mark.asyncio
async def test_delete_extraction_fields_success(service):
    project_id = uuid4()
    creation = await service.create_extraction_config(CreateExtractionConfigRequest(project_id=project_id, fields=[]))
    config_id = creation.unwrap().config_id

    # Add field manually to mock DAL
    field_id = str(uuid4())
    service.dal.fields[str(config_id)] = [{"id": field_id, "field_name": "title"}]

    req = DeleteExtractionFieldsRequest(field_ids=[UUID(field_id)])
    result = await service.delete_extraction_fields(req)
    assert isinstance(result, Success)
    assert result.unwrap().status == ResponseStatus.SUCCESS


# Test failure during extraction field deletion
@pytest.mark.asyncio
async def test_delete_extraction_fields_failure():
    class FailingDeleteDAL(MockDAL):
        def delete_extraction_fields(self, field_ids):
            raise DatabaseError("Delete failed")

    service = ProjectService(dal=FailingDeleteDAL())
    req = DeleteExtractionFieldsRequest(field_ids=[uuid4()])
    result = await service.delete_extraction_fields(req)
    assert isinstance(result, Failure)
    assert isinstance(result.failure(), InternalServiceError)


# Test deleting an extraction config and its fields by project ID
@pytest.mark.asyncio
async def test_delete_extraction_config_success(service):
    project_id = uuid4()
    await service.create_extraction_config(CreateExtractionConfigRequest(project_id=project_id, fields=[]))
    req = DeleteExtractionConfigRequest(project_id=project_id)
    result = await service.delete_extraction_config(req)
    assert isinstance(result, Success)
    assert result.unwrap().status == ResponseStatus.SUCCESS


# Test deleting a config that doesn't exist (should return NOT_FOUND)
@pytest.mark.asyncio
async def test_delete_extraction_config_not_found(service):
    req = DeleteExtractionConfigRequest(project_id=uuid4())
    result = await service.delete_extraction_config(req)
    assert isinstance(result, Success)
    assert result.unwrap().status == ResponseStatus.NOT_FOUND


# Test DAL failure when deleting an extraction config
@pytest.mark.asyncio
async def test_delete_extraction_config_failure():
    class FailingDeleteDAL(MockDAL):
        def delete_extraction_config(self, config_id):
            raise DatabaseError("Delete failed")

        def client(self):
            class Client:
                def table(self, _):
                    class Query:
                        def select(self, *_):
                            return self

                        def eq(self, field, value):
                            return self

                        def limit(self, _):
                            return self

                        def execute(self):
                            return type("R", (), {"data": [{"id": str(uuid4())}]})

                    return Query()

            return Client()

    service = ProjectService(dal=FailingDeleteDAL())
    req = DeleteExtractionConfigRequest(project_id=uuid4())
    result = await service.delete_extraction_config(req)
    assert isinstance(result, Failure)
    assert isinstance(result.failure(), InternalServiceError)
