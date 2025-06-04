# tests/db/test_projects_dal.py
from uuid import uuid4

import pytest
from app.db.exceptions import DatabaseError
from app.db.projects_dal import ProjectDAL

# Mocked unit test for DAL


class MockResponse:
    def __init__(self, data=None, error=None, status_code=200):
        self.data = data
        self.error = error
        self.status_code = status_code


class MockClient:
    def __init__(self):
        self._data = {}
        self.inserted_data = None

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
        return self

    def limit(self, count):
        self._limit = count
        return self

    def execute(self):
        if getattr(self, "_return_single", False):
            return MockResponse(data=self.inserted_data)
        if getattr(self, "_limit", None) == 1:
            # Return list of one or empty list
            return MockResponse(data=[self.inserted_data] if self.inserted_data else [])
        return MockResponse(data=[self.inserted_data])


@pytest.fixture
def mock_dal():
    return ProjectDAL(client=MockClient())


def test_create_project(mock_dal):
    result = mock_dal.create_project(description="A test project")
    assert result is not None
    assert result["description"] == "A test project"


def test_get_project_by_id(mock_dal):
    id = uuid4()
    mock_dal.client.inserted_data = {"id": str(id), "description": "A test project"}
    result = mock_dal.get_project_by_id(id)
    assert result is not None
    assert "description" in result


def test_delete_project(mock_dal):
    success = mock_dal.delete_project(uuid4())
    assert success is True


def test_create_project_failure():
    class FailingClient(MockClient):
        def execute(self):
            return MockResponse(data=None, error="Insert failed", status_code=400)

    dal = ProjectDAL(client=FailingClient())
    with pytest.raises(Exception):
        dal.create_project(description="Fail this")


def test_get_project_not_found():
    class EmptyClient(MockClient):
        def execute(self):
            return MockResponse(data=[])

    dal = ProjectDAL(client=EmptyClient())
    result = dal.get_project_by_id(uuid4())
    assert result is None


def test_delete_project_failure():
    class FailingDeleteClient(MockClient):
        def execute(self):
            raise Exception("Delete error")  # <- match real behavior

    dal = ProjectDAL(client=FailingDeleteClient())
    with pytest.raises(DatabaseError, match="Error deleting project: Delete error"):
        dal.delete_project(project_id=uuid4())


def test_delete_project_not_found():
    class NoMatchClient(MockClient):
        def execute(self):
            return MockResponse(data=None, error="Nothing found", status_code=404)

    dal = ProjectDAL(client=NoMatchClient())
    success = dal.delete_project(uuid4())
    assert success is False
