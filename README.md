# Research Pipeline API

This project provides a REST API for the research pipeline system using **FastAPI** and **Supabase**.
It includes endpoints for project creation, source configuration, extraction configs, and more.

👉 Detailed documentation is available in the respective subfolders (e.g., API usage, database schema, auth logic, etc.).

---

## 📦 API Capabilities

The API enables users to:

* **Create and manage research projects**, each with a custom description.
* **Configure data sources** by specifying public research backends such as arXiv and PubMed, along with associated search criteria.
* **Define extraction configurations** to guide a large language model (LLM) in analyzing retrieved research papers.
* **Set up filtering logic**, including field-specific filters and criteria to exclude irrelevant papers from a given project.
* **FUTURE: allow collaborators**, add project collaborators that may have specific roles, such as reviewing AI extractions for certain filters/extraction fields/papers. 


## 🚀 Getting Started

### ▶️ Run the API Locally

```bash
uvicorn app.main:app --reload
```

### 🔐 Generate a JWT for Local Authentication

```bash
PYTHON=. python ./tools/get_access_token.py
```

### 🌐 Access the Local API Docs

[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---