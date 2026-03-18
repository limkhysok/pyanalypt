# PyAnalypt API Documentation

## Base URLs

- **Development**: `http://127.0.0.1:8000/api/v1/`
- **Production**: `https://api.pyanalypt.com/api/v1/`

## Authentication

All protected endpoints require a JWT `access` token in the Authorization header:
```
Authorization: Bearer <access_token>
```

**Token Lifetimes**:
- Access Token: **60 minutes**
- Refresh Token: **1 day**
- Rotation: Enabled — new refresh token issued on every refresh call.

---

## 🔐 Authentication Endpoints

### 1. Register New User
Create a new account using only a username and password.

- **Endpoint**: `POST /auth/registration/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "username": "johndoe",
  "password1": "SecurePass123!",
  "password2": "SecurePass123!"
}
```

- **Response (201 Created)**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "johndoe",
    "email": null,
    "first_name": null,
    "last_name": null,
    "full_name": null,
    "profile_picture": null,
    "email_verified": false,
    "is_staff": false,
    "is_active": true,
    "date_joined": "2026-03-16T08:00:00Z"
  }
}
```

---

### 2. Login
Log in with either your **username** or **email**.

- **Endpoint**: `POST /auth/login/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "username": "johndoe", 
  "password": "SecurePass123!"
}
```
*(Note: You can pass your email in the "username" field to login via email)*

- **Response (200 OK)**:
```json
{
  "access": "...",
  "refresh": "...",
  "user": { ... }
}
```

---

### 3. Logout
Invalidate the current session by blacklisting the refresh token.

- **Endpoint**: `POST /auth/logout/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "refresh": "<refresh_token>"
}
```

---

### 4. Get Current User
Retrieve detailed profile information for the authenticated user.

- **Endpoint**: `GET /auth/user/`
- **Auth Required**: Yes

---

### 5. Update Profile (Partial)
Update specific fields of your profile.

- **Endpoint**: `PATCH /auth/user/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "first_name": "John",
  "email": "john@example.com"
}
```

---

## 🔑 JWT Token Management

### 6. Refresh Access Token
Exchange a refresh token for a new access token.

- **Endpoint**: `POST /auth/token/refresh/`
- **Request Body**: `{"refresh": "<token>"}`

### 7. Verify Token
Check if a token is still valid.

- **Endpoint**: `POST /auth/token/verify/`
- **Request Body**: `{"token": "<token>"}`

---

## 🛡️ Admin Access

PyAnalypt provides a full administrative interface for managing users and system data.

- **Admin URL**: `http://127.0.0.1:8000/admin/`
- **Default Credentials**: 
  - **Email**: `admin@pyanalypt.com`
  - **Password**: `admin123!@#`

---

## 📂 Dataset Management

All endpoints below are under `/api/v1/datasets/`.

### 1. Upload File
Standard multipart/form-data upload.

- **Endpoint**: `POST /datasets/upload/`
- **Auth Required**: Yes
- **Request (Form Data)**:
  - `file`: The `.csv`, `.xlsx`, or `.json` file.
- **Response (201 Created)**: The newly created `Dataset` object.

### 2. List All Datasets
Retrieves all datasets owned by the authenticated user.

- **Endpoint**: `GET /datasets/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
[
  {
    "id": 15,
    "user": 1,
    "file": "http://.../datasets/survey.csv",
    "file_name": "survey.csv",
    "file_format": "csv",
    "file_size": 1048576,
    "uploaded_date": "2026-03-17T10:00:00Z",
    "updated_date": "2026-03-17T10:30:00Z"
  }
]
```

### 3. Dataset Detail
Returns dataset metadata **plus** a `data_preview` (first 50 rows) for immediate table display.

- **Endpoint**: `GET /datasets/{id}/`
- **Auth Required**: Yes

### 4. Delete Dataset
Removes the dataset record and its associated file from storage.

- **Endpoint**: `DELETE /datasets/{id}/`
- **Auth Required**: Yes

### 5. Rename Dataset
Rename the display file name of a dataset.

- **Endpoint**: `PATCH /datasets/{id}/rename/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "file_name": "renamed_data.csv"
}
```
- **Response (200 OK)**: Updated `Dataset` object.

### 6. Preview Dataframe
Get the first N rows of the dataset for inspection.

- **Endpoint**: `GET /datasets/{id}/preview/`
- **Auth Required**: Yes
- **Query Params**: `?rows=50` *(default: 10, max: 1000)*

### 7. Edit a Single Cell
Modify a specific cell in the underlying data file.

- **Endpoint**: `POST /datasets/{id}/update_cell/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "row_index": 5,
  "column_name": "Age",
  "value": 25
}
```
- **Response (200 OK)**:
```json
{
  "detail": "Cell updated.",
  "row_index": 5,
  "column_name": "Age",
  "new_value": 25
}
```

### 8. Export Dataset
Download the dataset in a requested format.

- **Endpoint**: `GET /datasets/{id}/export/`
- **Auth Required**: Yes
- **Query Params**: `?format=csv` *(options: `csv`, `json`, `xlsx`; defaults to original format)*

---

## ⚠️ Issue Management

All endpoints below are under `/api/v1/issues/`.

### Issue Object Schema

| Field | Type | Description |
|---|---|---|
| `id` | int | Unique identifier |
| `dataset` | int | FK to the parent Dataset |
| `issue_type` | string | See type choices below |
| `column_name` | string | Column where the issue was detected (empty = dataset-level) |
| `row_index` | int\|null | Specific row index (cell-level issues only) |
| `affected_rows` | int\|null | Number of rows affected (column-level issues) |
| `description` | string | Human-readable explanation |
| `suggested_fix` | string | Recommended action |
| `detected_at` | datetime | Timestamp of detection |

**Issue Type Choices**: `MISSING_VALUE` | `DUPLICATE` | `OUTLIER` | `SEMANTIC_ERROR` | `DATA_TYPE` | `INCONSISTENT_FORMATTING` | `INVALID_VALUE` | `WHITESPACE_ISSUE` | `SPECIAL_CHAR_ENCODING` | `INCONSISTENT_NAMING` | `LOGICAL_INCONSISTENCY`

### 1. Run Diagnosis Scan
Trigger a Pandas-based scan on a dataset to detect dirty data. Results are saved as `Issue` records and returned grouped by column. Re-scanning **replaces** all previous issues.

- **Endpoint**: `POST /issues/diagnose/{dataset_id}/`
- **Auth Required**: Yes
- **Request Body**: *(empty — no parameters needed)*
- **Response (200 OK)**:
```json
{
  "dataset_id": 15,
  "total_issues": 3,
  "issues_by_column": {
    "email": [
      {
        "id": 42,
        "issue_type": "MISSING_VALUE",
        "affected_rows": 12,
        "description": "'email' has 12 missing value(s).",
        "suggested_fix": "Use the 'handle_na' operation to fill or drop these rows."
      }
    ],
    "age": [
      {
        "id": 43,
        "issue_type": "OUTLIER",
        "affected_rows": 2,
        "description": "'age' has 2 outlier(s) with Z-score > 3.",
        "suggested_fix": "Use 'outlier_clip' to bound these values."
      }
    ],
    "__dataset__": [
      {
        "id": 44,
        "issue_type": "DUPLICATE",
        "affected_rows": 5,
        "description": "Found 5 exact duplicate row(s) across the dataset.",
        "suggested_fix": "Use the 'drop_duplicates' operation."
      }
    ]
  }
}
```

### 2. List Issues for a Dataset
Get all issues for a specific dataset, scoped to the authenticated user.

- **Endpoint**: `GET /issues/?dataset={id}`
- **Auth Required**: Yes
- **Response**: Array of Issue objects.

### 3. Get Single Issue
- **Endpoint**: `GET /issues/{id}/`
- **Auth Required**: Yes

### 4. Update an Issue
Edit writable fields (e.g. `suggested_fix`, `description`).

- **Endpoint**: `PATCH /issues/{id}/`
- **Auth Required**: Yes
- **Request Body** *(any subset of writable fields)*:
```json
{
  "issue_type": "INVALID_VALUE",
  "suggested_fix": "Drop these rows manually."
}
```

### 5. Delete an Issue
- **Endpoint**: `DELETE /issues/{id}/`
- **Auth Required**: Yes

---

### Standard Error Format
```json
{
  "detail": "Error message description"
}
```

### Common HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | User created successfully |
| 400 | Bad Request | Validation error or missing fields |
| 401 | Unauthorized | Invalid or expired token |
| 403 | Forbidden | Permissions mapping error |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server-side crash |

---

## 🔗 Resources

- **GitHub Repository**: [soklimkhy/pyanalypt](https://github.com/soklimkhy/pyanalypt)
- **Last Updated**: 2026-03-18
- **Status**: 🛠️ Refactoring for "Big Change"
