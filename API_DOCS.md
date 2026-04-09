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
Create a new account with email and password. A verification link is sent to the email — the user cannot log in until the link is clicked.

- **Endpoint**: `POST /auth/registration/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```
> Optionally include `"first_name"` and `"last_name"`.

- **Response (201 Created)**:
```json
{
  "detail": "Verification e-mail sent."
}
```

---

### 2. Verify Email
Confirm the email address using the key from the verification link sent to the user's inbox. This must be completed before the user can log in.

- **Endpoint**: `POST /auth/registration/verify-email/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "key": "<key_from_email_link>"
}
```
- **Response (200 OK)**:
```json
{
  "detail": "ok"
}
```

> **Frontend flow:**
> 1. User clicks link in email → lands on `http://localhost:3000/verify-email/MjA:1w3wGL:SkMWk8Po...`
> 2. Frontend extracts the key from the **URL path** (everything after `/verify-email/`)
> 3. Frontend calls `POST /api/v1/auth/registration/verify-email/` with `{"key": "<extracted_key>"}`
> 4. On `200 OK` → redirect to `/dashboard` or `/login`

---

### 3. Resend Verification Email
Resend the verification link if the user didn't receive it or it expired (links expire after **3 days**).

- **Endpoint**: `POST /auth/registration/resend-email/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "email": "user@example.com"
}
```
- **Response (200 OK)**:
```json
{
  "detail": "ok"
}
```

---

### 4. Login
Log in with **email and password**.

- **Endpoint**: `POST /auth/login/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

- **Response (200 OK)**:
```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "user",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "profile_picture": null,
    "email_verified": true,
    "is_staff": false,
    "is_active": true,
    "date_joined": "2026-03-21T00:00:00Z",
    "last_login": "2026-03-21T06:00:00Z"
  }
}
```

---

### 5. Logout
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

### 6. Get Current User
Retrieve detailed profile information for the authenticated user.

- **Endpoint**: `GET /auth/user/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "user",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe",
  "profile_picture": null,
  "email_verified": true,
  "is_staff": false,
  "is_active": true,
  "date_joined": "2026-03-21T00:00:00Z",
  "last_login": "2026-03-21T06:00:00Z"
}
```

---

### 7. Update Profile (Partial)
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

### 8. Refresh Access Token
Exchange a refresh token for a new access token. A new refresh token is also returned (rotation enabled).

- **Endpoint**: `POST /auth/token/refresh/`
- **Auth Required**: No
- **Request Body**: `{"refresh": "<refresh_token>"}`
- **Response (200 OK)**: `{"access": "<new_access_token>", "refresh": "<new_refresh_token>"}`

### 9. Verify Token
Check if an access or refresh token is still valid.

- **Endpoint**: `POST /auth/token/verify/`
- **Auth Required**: No
- **Request Body**: `{"token": "<token>"}`
- **Response (200 OK)**: `{}` *(empty = valid)*

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
  - `file`: The `.csv`, `.xlsx`, `.json`, or `.parquet` file.
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
- **Query Params**: `?format=csv` *(options: `csv`, `json`, `xlsx`, `parquet`; defaults to original format)*

### 9. AI Data Analysis (Ollama)
Generate "problem statements" or analysis goals for the dataset using a local Ollama AI model. This endpoint analyzes column metadata (names, types, missing values, unique values) to provide AI-generated insights.

- **Endpoint**: `POST /datasets/{id}/analyze_issues/`
- **Auth Required**: Yes

**Sample Request**:
```http
POST /api/v1/datasets/15/analyze_issues/
Authorization: Bearer <access_token>
Content-Type: application/json

{}
```
> Note: Body can be empty as headers/stats are extracted automatically from the stored file.

**Sample Response (200 OK)**:
```json
{
  "dataset_id": 15,
  "file_name": "pharma_sales_data.csv",
  "problem_statements": "1. **Negative Price Outliers**: The 'unit_price' column contains negative values...\n2. **Missing Dosage Metadata**: A significant number of rows are missing 'dosage' info...\n3. **Temporal Analysis Gap**: The distribution of 'sale_date' suggests reporting gaps."
}
```
> **Note**: This requires a local Ollama instance running with the `llama3` model (configurable in `config/settings.py`).

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

The response includes a full **dataset overview** (shape, data types, null counts, duplicate rows, and numeric `describe()` stats) so the frontend can display summary info alongside the issues.

**Scanners run automatically**:
| Scanner | Issue Type | What it detects |
|---|---|---|
| Missing values | `MISSING_VALUE` | Null / NaN cells per column |
| Duplicates | `DUPLICATE` | Exact duplicate rows |
| Type inconsistencies | `DATA_TYPE` | Mixed Python types in a column |
| Outliers | `OUTLIER` | Z-score > 3 in numeric columns |
| Inconsistent formatting | `INCONSISTENT_FORMATTING` | Mixed date formats (e.g. YYYY-MM-DD vs MM/DD/YYYY) |
| Invalid values | `INVALID_VALUE` | Negative numbers in columns like age, price, salary |
| Whitespace issues | `WHITESPACE_ISSUE` | Leading/trailing/extra spaces in strings |
| Encoding issues | `SPECIAL_CHAR_ENCODING` | Mojibake / garbled characters (Ã©, â€™, ï¿½) |
| Inconsistent naming | `INCONSISTENT_NAMING` | Same category in mixed case (Male vs male vs MALE) |
| Logical inconsistencies | `LOGICAL_INCONSISTENCY` | start_date > end_date, min > max |

- **Endpoint**: `POST /issues/diagnose/{dataset_id}/`
- **Auth Required**: Yes
- **Request Body**: *(empty — no parameters needed)*
- **Response (200 OK)**:
```json
{
  "dataset_id": 15,
  "overview": {
    "shape": { "rows": 1000, "columns": 8 },
    "duplicate_rows": 5,
    "total_missing": 23,
    "columns": {
      "Name": { "dtype": "object", "non_null_count": 1000, "null_count": 0 },
      "Age": { "dtype": "int64", "non_null_count": 988, "null_count": 12 },
      "Salary": { "dtype": "float64", "non_null_count": 989, "null_count": 11 },
      "Department": { "dtype": "object", "non_null_count": 1000, "null_count": 0 },
      "Join_Date": { "dtype": "object", "non_null_count": 1000, "null_count": 0 }
    },
    "numeric_summary": {
      "Age": {
        "count": 988.0,
        "mean": 35.42,
        "std": 12.15,
        "min": 18.0,
        "25%": 26.0,
        "50%": 34.0,
        "75%": 44.0,
        "max": 65.0
      },
      "Salary": {
        "count": 989.0,
        "mean": 72500.50,
        "std": 25000.75,
        "min": 30000.0,
        "25%": 52000.0,
        "50%": 70000.0,
        "75%": 90000.0,
        "max": 150000.0
      }
    }
  },
  "total_issues": 7,
  "issues_by_column": {
    "Age": [
      {
        "id": 42,
        "issue_type": "MISSING_VALUE",
        "affected_rows": 12,
        "description": "'Age' has 12 missing value(s).",
        "suggested_fix": "Use the 'handle_na' operation to fill or drop these rows."
      },
      {
        "id": 43,
        "issue_type": "OUTLIER",
        "affected_rows": 2,
        "description": "'Age' has 2 outlier(s) with Z-score > 3.",
        "suggested_fix": "Use 'outlier_clip' to bound these values."
      }
    ],
    "Salary": [
      {
        "id": 45,
        "issue_type": "MISSING_VALUE",
        "affected_rows": 11,
        "description": "'Salary' has 11 missing value(s).",
        "suggested_fix": "Use the 'handle_na' operation to fill or drop these rows."
      }
    ],
    "Department": [
      {
        "id": 46,
        "issue_type": "INCONSISTENT_NAMING",
        "affected_rows": 15,
        "description": "'Department' has inconsistent naming: 'Sales' / 'sales'.",
        "suggested_fix": "Standardize values to a consistent case (e.g. Title Case)."
      }
    ],
    "Join_Date": [
      {
        "id": 47,
        "issue_type": "INCONSISTENT_FORMATTING",
        "affected_rows": null,
        "description": "'Join_Date' has mixed date formats: MM/DD/YYYY, YYYY-MM-DD.",
        "suggested_fix": "Standardize all dates to a single format (e.g. YYYY-MM-DD)."
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

### 6. Issue Summary / Stats
Get aggregated issue counts for a dataset, grouped by type and column.

- **Endpoint**: `GET /issues/summary/{dataset_id}/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "dataset_id": 15,
  "total_issues": 5,
  "by_type": {
    "MISSING_VALUE": 2,
    "DUPLICATE": 1,
    "OUTLIER": 2
  },
  "by_column": {
    "email": 1,
    "age": 2,
    "salary": 1
  },
  "dataset_level_issues": 1
}
```

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

## 🧹 Cleaning Operations

All endpoints below are under `/api/v1/cleaning/`.

### CleaningOperation Object Schema

| Field           | Type    | Description                                      |
|-----------------|---------|--------------------------------------------------|
| `id`            | int     | Unique identifier                                |
| `dataset`       | int     | FK to the parent Dataset                         |
| `issue`         | int\|null | FK to the related Issue (nullable)               |
| `operation_type`| string  | Cleaning operation type (see choices below)      |
| `column_name`   | string  | Column affected (blank for dataset-level ops)    |
| `parameters`    | object  | Operation parameters (varies by type)            |
| `rows_affected` | int\|null | Number of rows affected (if known)               |
| `status`        | string  | PENDING, APPLIED, FAILED, REVERTED               |
| `applied_at`    | datetime\|null | When operation was applied (if any)         |
| `created_at`    | datetime| When operation was created                       |

**Operation Type Choices:**
`FILL_NA` | `DROP_ROWS` | `DROP_DUPLICATES` | `CLIP_OUTLIERS` | `REMOVE_OUTLIERS` | `CAST_COLUMN` | `STANDARDIZE_FORMAT` | `REPLACE_VALUES` | `STRIP_WHITESPACE` | `FIX_ENCODING` | `STANDARDIZE_CASE` | `RENAME_COLUMN`

### 1. List Cleaning Operations
- **Endpoint**: `GET /cleaning/?dataset={id}`
- **Auth Required**: Yes
- **Response (200 OK)**: Array of CleaningOperation objects

### 2. Create (Apply) a Cleaning Operation
- **Endpoint**: `POST /cleaning/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "dataset": 1,
  "issue": 101,
  "operation_type": "FILL_NA",
  "column_name": "Salary",
  "parameters": { "method": "mean" }
}
```
- **Response (201 Created)**: CleaningOperation object (status will be PENDING or APPLIED)

### 3. Revert a Cleaning Operation
- **Endpoint**: `POST /cleaning/{id}/revert/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "detail": "Operation reverted (not actually implemented)."
}
```

### 4. Preview a Cleaning Operation
- **Endpoint**: `POST /cleaning/preview/`
- **Auth Required**: Yes
- **Request Body**: Same as create
- **Response (501 Not Implemented)**:
```json
{
  "detail": "Preview not implemented yet."
}
```

---
