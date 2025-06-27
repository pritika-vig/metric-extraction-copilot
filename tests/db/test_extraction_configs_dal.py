from datetime import datetime, timezone
from uuid import uuid4

import pytest
from app.db.exceptions import DatabaseError
from app.db.projects_dal import ProjectDAL

# === MOCKS ===


class MockResponse:
    def __init__(self, data=None, error=None, status_code=200):
        self.data = data
        self.error = error
        self.status_code = status_code


class MockClient:
    def __init__(self):
        self.inserted_data = None
        self.table_name = None
        self._limit = None
        self._field = None
        self._value = None

    def table(self, name):
        self.table_name = name
        return self

    def select(self, *_):
        return self

    def insert(self, data):
        self.inserted_data = data
        return self

    def delete(self):
        return self

    def eq(self, field, value):
        self._field = field
        self._value = value
        return self

    def in_(self, field, values):
        self._field = field
        self._value = values
        return self

    def limit(self, count):
        self._limit = count
        return self

    def execute(self):
        if self.table_name == "extraction_configs" and self._field == "project_id":
            # Simulate existing config for project ID
            return MockResponse(data=[{"id": str(uuid4())}])
        elif self._limit == 1:
            return MockResponse(data=[self.inserted_data] if self.inserted_data else [])
        return MockResponse(data=[self.inserted_data])


@pytest.fixture
def mock_dal():
    return ProjectDAL(client=MockClient())


# === TESTS ===


# Test creating a new extraction config for a project
def test_create_extraction_config_success(mock_dal):
    project_id = uuid4()

    # Simulate a successful insert response with expected structure
    inserted = {"id": str(uuid4()), "project_id": str(project_id), "created_at": datetime.now(timezone.utc).isoformat()}

    # Patch execute to return a response with that inserted config
    mock_dal.client.inserted_data = inserted
    mock_dal.client.execute = lambda: MockResponse(data=[inserted])

    result = mock_dal.create_extraction_config(project_id)

    assert result is not None
    assert result["project_id"] == str(project_id)


# Test failure to create a config due to DB constraint (duplicate project_id)
def test_create_extraction_config_duplicate_project():
    class DuplicateConstraintClient(MockClient):
        def execute(self):
            raise Exception("duplicate key value violates unique constraint")

    dal = ProjectDAL(client=DuplicateConstraintClient())
    with pytest.raises(DatabaseError, match="Error creating extraction config: duplicate key"):
        dal.create_extraction_config(uuid4())


# Test failure to create config due to general error
def test_create_extraction_config_failure():
    class FailingClient(MockClient):
        def execute(self):
            raise Exception("Insert failed")

    dal = ProjectDAL(client=FailingClient())
    with pytest.raises(DatabaseError, match="Error creating extraction config: Insert failed"):
        dal.create_extraction_config(uuid4())


# Test inserting multiple extraction fields
def test_insert_extraction_fields_success(mock_dal):
    config_id = uuid4()
    fields = [{"field_name": "title", "description": "Title field"}]
    mock_dal.insert_extraction_fields(config_id=config_id, fields=fields)
    assert mock_dal.client.inserted_data[0]["field_name"] == "title"
    assert mock_dal.client.table_name == "extraction_fields"


# Test error inserting fields
def test_insert_extraction_fields_failure():
    class FailingInsertClient(MockClient):
        def execute(self):
            raise Exception("Insert error")

    dal = ProjectDAL(client=FailingInsertClient())
    with pytest.raises(DatabaseError, match="Error inserting extraction fields: Insert error"):
        dal.insert_extraction_fields(uuid4(), [{"field_name": "test"}])


# Test deleting a full extraction config (and its fields)
def test_delete_extraction_config_success(mock_dal):
    config_id = uuid4()
    mock_dal.delete_extraction_config(config_id)
    assert mock_dal.client.table_name == "extraction_configs"  # Last table affected


# Test error while deleting config
def test_delete_extraction_config_failure():
    class FailingDeleteClient(MockClient):
        def execute(self):
            raise Exception("Delete error")

    dal = ProjectDAL(client=FailingDeleteClient())
    with pytest.raises(DatabaseError, match="Error deleting extraction config: Delete error"):
        dal.delete_extraction_config(uuid4())


# Test deleting specific extraction fields
def test_delete_extraction_fields_success(mock_dal):
    field_ids = [uuid4(), uuid4()]
    mock_dal.delete_extraction_fields(field_ids)
    assert mock_dal.client.table_name == "extraction_fields"
    assert mock_dal.client._value == [str(fid) for fid in field_ids]


# Test failure when deleting fields
def test_delete_extraction_fields_failure():
    class FailingDeleteClient(MockClient):
        def execute(self):
            raise Exception("Delete error")

    dal = ProjectDAL(client=FailingDeleteClient())
    with pytest.raises(DatabaseError, match="Error deleting extraction fields: Delete error"):
        dal.delete_extraction_fields([uuid4()])
