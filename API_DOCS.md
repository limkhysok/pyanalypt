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

### 2. Paste Data (Raw Text)
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

### 3. List All Datasets
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
    "row_count": 1250,
    "column_count": 14,
    "uploaded_date": "2026-03-17T10:00:00Z",
    "updated_date": "2026-03-17T10:30:00Z"
  }
]
```

### 4. Smart Cleaning Actions
Apply cleaning operations. Each operation creates a **new version** (a child dataset).

- **Endpoint**: `POST /datasets/{id}/clean/`
- **Request Body (Pipeline Example)**:
```json
{
  "pipeline": [
    { "operation": "handle_na", "params": { "strategy": "fill_mean" } },
    { "operation": "drop_duplicates", "params": { "columns": ["email"] } }
  ]
}
```

### 5. Smart Analysis & Visuals
Get stats and chart-ready data for the frontend.

- **Endpoint**: `GET /datasets/{id}/analyze/` - Get correlations and missing value reports.
- **Endpoint**: `POST /datasets/{id}/visualize/` - Generate ECharts data for scatter/bar/line/pie.
- **Endpoint**: `GET /datasets/{id}/preview/` - Get the first 10-100 rows for the table view.

---

## 🚨 Error Responses

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
