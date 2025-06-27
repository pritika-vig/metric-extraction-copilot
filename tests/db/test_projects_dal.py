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
        self.table_name = None
        self._limit = None

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
        if self._limit == 1:
            return MockResponse(data=[self.inserted_data] if self.inserted_data else [])
        return MockResponse(data=[self.inserted_data])


@pytest.fixture
def mock_dal():
    return ProjectDAL(client=MockClient())


def test_create_project(mock_dal):
    inserted_project = {"id": str(uuid4()), "description": "A test project"}

    mock_dal.client.inserted_data = inserted_project
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
    result = mock_dal.delete_project(uuid4())
    assert result is True


def test_create_project_failure():
    class FailingClient(MockClient):
        def execute(self):
            return MockResponse(data=None, error="Insert failed", status_code=400)

    dal = ProjectDAL(client=FailingClient())
    with pytest.raises(DatabaseError):
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
            raise Exception("Delete error")

    dal = ProjectDAL(client=FailingDeleteClient())
    with pytest.raises(DatabaseError, match="Error deleting project: Delete error"):
        dal.delete_project(project_id=uuid4())


def test_delete_project_not_found():
    class NoMatchClient(MockClient):
        def execute(self):
            return MockResponse(data=None, error="Nothing found", status_code=404)

    dal = ProjectDAL(client=NoMatchClient())
    result = dal.delete_project(uuid4())
    assert result is False


def test_insert_project_sources(mock_dal):
    source_data = [
        {"id": str(uuid4()), "project_id": str(uuid4()), "backend_name": "arXiv", "backend_query": "machine learning"},
        {"id": str(uuid4()), "project_id": str(uuid4()), "backend_name": "PubMed", "backend_query": "cancer genomics"},
    ]
    mock_dal.insert_project_sources(source_data)
    assert mock_dal.client.inserted_data == source_data
    assert mock_dal.client.table_name == "project_sources"


def test_insert_project_sources_failure():
    class FailingInsertClient(MockClient):
        def execute(self):
            raise Exception("Insert error")

    dal = ProjectDAL(client=FailingInsertClient())
    with pytest.raises(DatabaseError, match="Error inserting project sources: Insert error"):
        dal.insert_project_sources([{"id": str(uuid4()), "project_id": str(uuid4()), "backend_name": "Test", "backend_query": "query"}])


def test_delete_project_sources(mock_dal):
    project_id = uuid4()
    mock_dal.delete_project_sources(project_id)
    assert mock_dal.client.table_name == "project_sources"


def test_delete_project_sources_failure():
    class FailingDeleteClient(MockClient):
        def execute(self):
            raise Exception("Delete error")

    dal = ProjectDAL(client=FailingDeleteClient())
    with pytest.raises(DatabaseError, match="Error deleting project sources: Delete error"):
        dal.delete_project_sources(uuid4())
