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

## 📂 Dataset Management (The Data Engine)

All endpoints below follow the **api/v1/datasets/** prefix.

### 1. Upload File (Multipart)
Standard multipart/form-data upload using your system's file picker.

- **Endpoint**: `POST /datasets/upload/`
- **Request (Form Data)**:
  - `file`: The `.csv`, `.xlsx`, or `.json` file.
- **Response**: The newly created `Dataset` object.

### a. Paste Data (Raw Text)
Create a dataset by pasting raw CSV/JSON text directly from your clipboard.

- **Endpoint**: `POST /datasets/paste/`
- **Request Body**:
```json
{
  "file_name": "survey_results.csv",
  "raw_data": "id,name,value\n1,test,100",
  "format": "csv"
}
```

### b. Dataset Actions (CRUD)

- **Endpoint**: `GET /datasets/` - List all datasets for the logged-in user.
- **Endpoint**: `GET /datasets/{id}/` - **Detail View**. Returns model fields **plus** a `data_preview` for immediate table display.
- **Endpoint**: `PATCH /datasets/{id}/` - **Update Metadata**. Example: `{"file_name": "renamed.csv"}`.
- **Endpoint**: `PATCH /datasets/{id}/update_cell/` - **Manual Edit**. Modify a specific cell in the file.
  - Body: `{"row_index": 5, "column_name": "Age", "value": 25}`.
- **Endpoint**: `DELETE /datasets/{id}/` - **Delete**. Removes the dataset and its associated file.

### c. List All Datasets
Retrieves a list of all datasets owned by the authenticated user.

- **Endpoint**: `GET /datasets/`
- **Response Format**:
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

`file_size` is stored in bytes and is read-only metadata populated by the server.

### 2. Run Diagnosis Scan
Trigger a Pandas or Gemini AI scan on a dataset to detect dirty data. Results are saved as `Issue` records and returned grouped by column.

- **Endpoint**: `POST /api/v1/datasets/{id}/diagnose/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "method": "pandas"
}
```
`method` options: `"pandas"` | `"gemini"` | `"both"` *(default: `"both"`)*

- **Response (200 OK)**:
```json
{
  "dataset_id": 15,
  "method": "pandas",
  "total_issues": 3,
  "warnings": [],
  "issues_by_column": {
    "email": [
      {
        "id": 42,
        "issue_type": "MISSING_VALUE",
        "affected_rows": 12,
        "description": "'email' has 12 missing value(s).",
        "severity": "MEDIUM",
        "suggested_fix": "Use the 'handle_na' operation to fill or drop these rows.",
        "detected_by": "PANDAS",
        "is_user_modified": false,
        "is_resolved": false
      }
    ],
    "age": [
      {
        "id": 43,
        "issue_type": "OUTLIER",
        "affected_rows": 2,
        "description": "'age' has 2 outlier(s) with Z-score > 3.",
        "severity": "LOW",
        "suggested_fix": "Use 'outlier_clip' to bound these values.",
        "detected_by": "PANDAS",
        "is_user_modified": false,
        "is_resolved": false
      }
    ],
    "__dataset__": [
      {
        "id": 44,
        "issue_type": "DUPLICATE",
        "affected_rows": 5,
        "description": "Found 5 exact duplicate row(s) across the dataset.",
        "severity": "LOW",
        "suggested_fix": "Use the 'drop_duplicates' operation.",
        "detected_by": "PANDAS",
        "is_user_modified": false,
        "is_resolved": false
      }
    ]
  }
}
```
> Re-scanning preserves any issue the user has manually modified (`is_user_modified: true`).
> If Gemini quota is exceeded, the response still returns `200` with a message in `warnings`, and previous Gemini issues remain unchanged.

### 3. Other Dataset Utilities

- **Endpoint**: `GET /api/v1/datasets/{id}/query/` — **Analyst Search**: Manually filter the dataset.
  - Query params: `?column=price&operator=lt&value=0` *(operators: `eq`, `gt`, `lt`, `contains`)*
- **Endpoint**: `GET /api/v1/datasets/{id}/preview/` — Get the first 10–100 rows for inspection.
  - Query params: `?rows=50` *(default: 10, max: 1000)*

---

## ⚠️ Issue Management
View and manage dirty-data issues detected during diagnosis.

### Issue Object Schema

| Field | Type | Description |
|---|---|---|
| `id` | int | Unique identifier |
| `dataset` | int | FK to the parent Dataset |
| `issue_type` | string | `MISSING_VALUE` \| `DUPLICATE` \| `OUTLIER` \| `TYPE_MISMATCH` \| `SEMANTIC_ERROR` |
| `column_name` | string | Column where the issue was detected (empty = dataset-level) |
| `row_index` | int\|null | Specific row index (cell-level issues only) |
| `affected_rows` | int\|null | Number of rows affected (column-level issues) |
| `description` | string | Human-readable explanation |
| `severity` | string | `LOW` \| `MEDIUM` \| `HIGH` |
| `suggested_fix` | string | Recommended action |
| `detected_by` | string | `PANDAS` \| `GEMINI` \| `MANUAL` |
| `is_user_modified` | bool | `true` if user has manually edited this issue |
| `is_resolved` | bool | `true` if the issue has been fixed |
| `detected_at` | datetime | Timestamp of detection |

### a. List Issues for a Dataset
Get all issues for a specific dataset, scoped to the authenticated user.

- **Endpoint**: `GET /api/v1/issues/?dataset={id}`
- **Auth Required**: Yes
- **Response**: Array of Issue objects.

### b. Update / Override an Issue
User can edit any field (e.g. severity, suggested_fix, description) or resolve it.
Any PATCH automatically sets `is_user_modified: true` to protect it from being overwritten on re-scan.

- **Endpoint**: `PATCH /api/v1/issues/{id}/`
- **Auth Required**: Yes
- **Request Body** *(any subset of writable fields)*:
```json
{
  "severity": "HIGH",
  "suggested_fix": "Drop these rows manually.",
  "is_resolved": true
}
```
- **Response (200 OK)**: Updated Issue object with `"is_user_modified": true`.

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
- **Last Updated**: 2026-03-17
- **Status**: 🛠️ Refactoring for "Big Change"
