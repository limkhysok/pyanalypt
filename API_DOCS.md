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

### 2. Identifying the Issues
Identify "dirty" data automatically or manually.

- **Endpoint**: `GET /api/v1/datasets/{id}/diagnose/` - **Auto-Scan**: Runs Pandas + Google Gemini AI to find missing values, duplicates, and semantic errors. Saves results to the **Issues** table.
- **Endpoint**: `GET /api/v1/datasets/{id}/query/` - **Analyst Search**: Manually filter the dataset to find specific issues.
  - Query params: `?column=price&operator=lt&value=0` (operators: `eq`, `gt`, `lt`, `contains`).
- **Endpoint**: `GET /api/v1/datasets/{id}/preview/` - Get the first 10-100 rows for general inspection.

---

## ⚠️ Issue Management
Manage the "Dirty Data" found during diagnosis.

### a. List Issues
Get all detected problems for your datasets.

- **Endpoint**: `GET /api/v1/issues/`
- **Response**: List of `Issue` objects.

### b. Update/Resolve Issue
Mark an issue as fixed or change its severity.

- **Endpoint**: `PATCH /api/v1/issues/{id}/`
- **Body**: `{"is_resolved": true}`

---

## 🔑 JWT Token Management

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
- **Last Updated**: 2026-03-16
- **Status**: 🛠️ Refactoring for "Big Change"
