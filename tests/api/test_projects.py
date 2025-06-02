# # tests/api/test_projects.py


# def test_create_project(client):
#     response = client.post("/projects", json={
#         "query": "Find papers...",
#         "sources": ["arxiv", "pubmed"]
#     })

#     print(response.json())  # optional debug
#     assert response.status_code == 200
#     assert response.json()["status"] == "fetched"

# def test_create_project_missing_sources(client):
#     response = client.post("/projects", json={"query": "Find papers..."})
#     assert response.status_code == 422
