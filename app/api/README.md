# Project API Reference

This API supports project creation, configuration of data extraction settings, and backend source tracking. Below is a breakdown of available endpoints.

---

## Project Endpoints

### ▶️ `POST /projects/`

**Description**: Create a new project.

#### Request Body: `CreateProjectRequest`

```json
{
  "description": "Exploring machine learning applications in healthcare"
}
```

#### Response: `CreateProjectResponse`

```json
{
  "project_id": "UUID",
  "description": "Exploring machine learning applications in healthcare",
  "created_at": "ISO datetime",
  "status": "SUCCESS"
}
```

---

### 🔍 `GET /projects/{project_id}`

**Description**: Get details of a project.

#### Response: `GetProjectResponse`

```json
{
  "project_id": "UUID",
  "description": "Exploring machine learning applications in healthcare",
  "created_at": "ISO datetime",
  "status": "SUCCESS | NOT_FOUND"
}
```

---

### ❌ `DELETE /projects/{project_id}`

**Description**: Delete a project by its ID.

#### Response: `DeleteProjectResponse`

```json
{
  "status": "SUCCESS | NOT_FOUND"
}
```

---

## 🌐 Project Sources

### ▶️ `POST /projects/{project_id}/sources`

**Description**: Attach external backend source queries to a project.

#### Request Body: `List[ProjectSourceRequest]`

```json
[
  { "backend_name": "arXiv", "backend_query": "deep learning" },
  { "backend_name": "PubMed", "backend_query": "cancer genomics" }
]
```

#### Response: `CreateProjectSourcesResponse`

```json
{
  "project_id": "UUID",
  "status": "SUCCESS"
}
```

---

## 🧪 Extraction Config Endpoints

### ▶️ `POST /projects/configs/`

**Description**: Create an extraction config with one or more fields for a given project.

#### Request Body: `CreateExtractionConfigRequest`

```json
{
  "project_id": "UUID",
  "fields": [
    { "field_name": "title", "description": "Paper title" },
    { "field_name": "authors" }
  ]
}
```

#### Response: `CreateExtractionConfigResponse`

```json
{
  "config_id": "UUID",
  "field_count": 2,
  "status": "SUCCESS"
}
```

---

### ➕ `POST /projects/configs/{config_id}/fields`

**Description**: Add new fields to an existing extraction config.

#### Request Body: `AddExtractionFieldsRequest`

```json
{
  "fields": [
    { "field_name": "abstract", "description": "Abstract text" }
  ]
}
```

#### Response: `AddExtractionFieldsResponse`

```json
{
  "status": "SUCCESS"
}
```

---

### ❌ `DELETE /projects/configs/by-project/{project_id}`

**Description**: Delete an extraction config and all of its fields for a given project.

#### Response: `DeleteExtractionConfigResponse`

```json
{
  "status": "SUCCESS | NOT_FOUND"
}
```

---

### ❌ `DELETE /projects/configs/{config_id}/fields`

**Description**: Delete specific fields from an extraction config.

#### Request Body: `DeleteExtractionFieldsRequest`

```json
{
  "field_ids": ["UUID", "UUID"]
}
```

#### Response: `DeleteExtractionFieldsResponse`

```json
{
  "status": "SUCCESS"
}
```

---

## 🧒 ResponseStatus Enum

All responses use a `status` field with one of the following values:

* `SUCCESS` – Operation completed as expected
* `NOT_FOUND` – Target project/config not found or inaccessible
* `DEGRADED` – Operation succeeded, but with missing pieces (e.g., partial data)
* `ERROR` – Generic failure