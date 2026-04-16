# Frontend Integration Prompt — Dataset Endpoints

Read this before building or updating any dataset-related UI. This reflects the **current implemented state** of the backend.

---

## Base URL

```
http://127.0.0.1:8000/api/v1/datasets/
```

All requests require:
```
Authorization: Bearer <access_token>
```

---

## Dataset Object Shape

Every dataset endpoint that returns a dataset returns this shape:

```json
{
  "id": 15,
  "user": 1,
  "file": "http://127.0.0.1:8000/media/datasets/2026/04/16/survey.csv",
  "file_name": "survey.csv",
  "file_format": "csv",
  "file_size": 1048576,
  "uploaded_date": "2026-04-16T10:00:00Z",
  "updated_date": "2026-04-16T10:30:00Z"
}
```

---

## Implemented Endpoints (7 total)

### 1. Upload
```
POST /datasets/upload/
Content-Type: multipart/form-data

Body: file=<File>
```
- Supported formats: `csv`, `xlsx`, `json`, `parquet`, `sql`
- Response: `201 Created` — Dataset object

---

### 2. List
```
GET /datasets/
```
- Returns all datasets belonging to the authenticated user.
- Response: `200 OK` — Array of Dataset objects

---

### 3. Delete
```
DELETE /datasets/{id}/
```
- Deletes the record and the physical file.
- Response: `204 No Content`

---

### 4. Rename
```
PATCH /datasets/{id}/rename/
Content-Type: application/json

{ "file_name": "new_name.csv" }
```
- `file_name` is required and cannot be blank.
- Response: `200 OK` — Updated Dataset object
- Error: `400` if `file_name` missing or blank

---

### 5. Export
```
GET /datasets/{id}/export/?format=csv
```
- `format` query param: `csv`, `json`, `xlsx`, `parquet`, `sql`
- Omitting `?format` defaults to the dataset's original format.
- Response: Binary file download (`Content-Disposition: attachment`)
- Error: `400` for unsupported format

> **Frontend tip:** Trigger via `window.location.href` or an `<a href>` link — do NOT use `fetch()` for file downloads unless you handle `Blob` responses manually.

---

### 6. Duplicate
```
POST /datasets/{id}/duplicate/
Content-Type: application/json

{
  "new_file_name": "Sales Copy",   // optional — defaults to "<original>_copy"
  "format": "sql"                  // optional — defaults to source format
}
```
- Converts the data on the fly if `format` differs from the source.
- The new dataset has `parent` pointing to the source dataset.
- Response: `201 Created` — Dataset object of the new clone

---

### 7. Activity Logs
```
GET /datasets/activity_logs/
GET /datasets/activity_logs/?dataset=15
```
- Optional `?dataset={id}` to filter to one dataset.
- Logged actions: `UPLOAD`, `RENAME`, `DELETE`, `DUPLICATE`, `EXPORT`
- Response: `200 OK`

```json
[
  {
    "id": 42,
    "user": 1,
    "dataset": 15,
    "dataset_name_snap": "survey.csv",
    "action": "UPLOAD",
    "details": { "format": "csv", "size": 1048576 },
    "timestamp": "2026-04-16T10:00:00Z"
  }
]
```

---

## What Does NOT Exist (do not build UI for these yet)

The following were previously mentioned in older docs or designs but are **not implemented** in the backend:

| Feature | Why it's absent |
|---|---|
| `GET /datasets/{id}/` — detail view | No `RetrieveModelMixin` in the ViewSet |
| `GET /datasets/{id}/preview/` — paginated rows | Endpoint removed from scope |
| `PATCH /datasets/{id}/update_cell/` — cell edit | Endpoint removed from scope |
| `POST /datasets/{id}/analyze_issues/` — AI analysis | Endpoint removed from scope |

If the frontend already has calls to these endpoints, remove or stub them out — they will return `404`.

---

## Error Handling

All error responses use this shape:
```json
{ "detail": "Error message here." }
```

| Status | Meaning |
|---|---|
| `400` | Validation error (missing field, unsupported format, etc.) |
| `401` | Missing or expired JWT token |
| `403` | Not the owner of this dataset |
| `404` | Dataset not found |
| `500` | Server-side failure (check `detail` for context) |
