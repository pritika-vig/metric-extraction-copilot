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

    def single(self):
        self._return_single = True
        return self

    def execute(self):
        if getattr(self, "_return_single", False):
            return MockResponse(data=self.inserted_data)  # Single dict
        return MockResponse(data=[self.inserted_data])  # List of dicts


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
            return MockResponse(data=None)

    dal = ProjectDAL(client=EmptyClient())
    result = dal.get_project_by_id(uuid4())
    assert result is None


def test_delete_project_failure():
    class FailingDeleteClient(MockClient):
        def execute(self):
            return MockResponse(data=None, error="Delete error", status_code=400)

    dal = ProjectDAL(client=FailingDeleteClient())

    with pytest.raises(DatabaseError, match="Error deleting project: Delete error"):
        dal.delete_project(uuid4())


def test_get_project_by_id_error():
    class ErrorClient(MockClient):
        def execute(self):
            return MockResponse(data=None, error="Fetch error", status_code=500)

    dal = ProjectDAL(client=ErrorClient())
    with pytest.raises(DatabaseError, match="Error fetching project: Fetch error"):
        dal.get_project_by_id(uuid4())


def test_create_project_no_data():
    class NoDataClient(MockClient):
        def execute(self):
            return MockResponse(data=[], error=None, status_code=201)

    dal = ProjectDAL(client=NoDataClient())
    result = dal.create_project(description="Should return None")
    assert result is None


def test_delete_project_not_found():
    class NoMatchClient(MockClient):
        def execute(self):
            return MockResponse(data=None, error="Nothing found", status_code=404)

    dal = ProjectDAL(client=NoMatchClient())
    success = dal.delete_project(uuid4())
    assert success is True  # Or adjust logic if you want False when nothing was deleted


def test_delete_project_204_no_content():
    class NoContentClient(MockClient):
        def execute(self):
            return MockResponse(data=None, error=None, status_code=204)

    dal = ProjectDAL(client=NoContentClient())
    success = dal.delete_project(uuid4())
    assert success is True
