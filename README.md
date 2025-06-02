
# Database Schema: Research Pipeline API

This document describes the Supabase-backed Postgres tables that support the Research Pipeline API. It includes usage patterns, constraints, and implementation quirks relevant to developers working on the FastAPI backend.

---

## Core Tables and Relationships

### `projects`
- Represents a single user’s research pipeline project.
- Owned by a single user (`owner_id`) but may have collaborators.

**Fields**:
- `id`: `UUID` (PK)
- `owner_id`: `UUID` (FK to `auth.users`)
- `query`: `TEXT`
- `created_at`: `TIMESTAMP`

**Notes**:
- Deleting a `project` will **cascade delete** related records:
  - `papers`, `filters`, `project_sources`, `collaborators`, `extraction_configs`, and associated nested tables.

---

### `papers`
- A document (e.g. academic paper) attached to a project.

**Fields**:
- `id`: `UUID` (PK)
- `project_id`: `UUID` (FK to `projects`)
- `title`, `abstract`: `TEXT`

---

### `filters`
- Text-matching or rule-based logic that evaluates paper content.

**Fields**:
- `id`: `UUID`
- `project_id`: `UUID` (FK to `projects`)
- `filter_scope`: ENUM (`abstract`, `title`, etc.)
- `user_specified_text_filter`: `TEXT`
- `timestamp`: `TIMESTAMP`

**Constraints**:
- **Create/Delete allowed**
- **Update is not allowed**: attempts to update will silently fail due to RLS `WITH CHECK`.

**FastAPI Tip**:
```python
# Creating a filter
await client.post("/rest/v1/filters", headers=headers, json={
    "id": str(uuid4()),
    "project_id": project_id,
    "timestamp": datetime.utcnow().isoformat(),
    "filter_scope": "abstract",
    "user_specified_text_filter": "machine learning"
})
```

---

### `paper_filter_results`
- Maps a filter's evaluation result on a specific paper.

**Fields**:
- `id`: `UUID`
- `paper_id`: `UUID`
- `filter_id`: `UUID`
- `passed`: `BOOLEAN`

**Cascade Behavior**:
- Deleting a `filter` or `paper` **automatically deletes** corresponding rows in `paper_filter_results`.

---

### `project_sources`
- Sources of documents (e.g., arXiv, PubMed).

**Fields**:
- `id`: `UUID`
- `project_id`: `UUID`
- `backend_name`, `backend_query`: `TEXT`

---

### `extraction_configs`
- Groups of extraction logic tied to a project.

**Fields**:
- `id`: `UUID`
- `project_id`: `UUID`
- `created_at`: `TIMESTAMP`

---

### `extraction_fields`
- Specific fields extracted from papers (e.g. Author, Date).

**Fields**:
- `id`: `UUID`
- `config_id`: `UUID`
- `field_name`, `description`: `TEXT`

---

### `extracted_fields`
- Results of an extraction field applied to a paper.

**Fields**:
- `id`: `UUID`
- `paper_id`: `UUID`
- `extraction_field_id`: `UUID`
- `field_value`: `TEXT`

**Cascade Behavior**:
- Deleting a `paper` or `extraction_field` removes `extracted_fields`.

---

## 🔐 Row-Level Security (RLS)

Note: Collaborator policies are not yet implemented, but are planned.

### General Rules

| Table | Read | Write | Notes |
|-------|------|-------|-------|
| `projects` | Owner + Collaborators | Owner | |
| `papers`, `filters`, `extraction_configs`, `extraction_fields`, `extracted_fields` | Owner via project | Owner only | |
| `filters` | **Read/Create/Delete allowed** | **Update blocked via RLS** | |
| `paper_filter_results` | Owner via paper+filter | Owner | Cascade-deleted if parent is deleted |

---

## 🧪 Example FastAPI Snippets

### Insert a Paper
```python
await client.post("/rest/v1/papers", headers=headers, json={
    "id": str(uuid4()),
    "project_id": project_id,
    "title": "New Paper",
    "abstract": "Some abstract..."
})
```

### Delete a Project (Triggers full cascade)
```python
await client.delete(
    f"/rest/v1/projects?id=eq.{project_id}",
    headers={**headers, "Prefer": "return=minimal"}
)
```

### Filter Access Denial Example
```python
# Attempt to patch — will return 200 but change nothing
resp = await client.patch(f"/rest/v1/filters?id=eq.{filter_id}", headers=headers, json={
    "user_specified_text_filter": "new-value"
})
assert resp.status_code == 200
assert resp.json() == []  # RLS silently blocks update
```

---

## ⚠️ Quirks to Know

- **RLS silent failures**: Supabase returns `200 OK` even if update is blocked (e.g. filters). Always verify changes by re-reading the row.
- **Deletion is cascade-based** but depends on PostgreSQL triggers and RLS visibility: ensure cascading deletes have visibility into child rows.
- **UUIDs**: All IDs are UUIDv4 — never use sequential integers.
