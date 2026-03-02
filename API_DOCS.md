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
- Access Token: **60 minutes** (decoded `exp` field inside the JWT)
- Refresh Token: **1 day**
- Rotation: enabled — new refresh token issued on every refresh call, old one blacklisted

---

## 🔐 Authentication Endpoints

### 1. Register New User
Create a new account. Only `email` and `password` are required. `username` is auto-generated from the email prefix if not provided.

- **Endpoint**: `POST /auth/registration/`
- **Auth Required**: No

**Minimum request:**
```json
{
  "email": "user@example.com",
  "password1": "SecurePass123!",
  "password2": "SecurePass123!"
}
```

**Full request (optional fields):**
```json
{
  "email": "user@example.com",
  "password1": "SecurePass123!",
  "password2": "SecurePass123!",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe"
}
```

- **Response (201 Created)**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 15,
    "email": "user@example.com",
    "username": "user",
    "first_name": null,
    "last_name": null,
    "full_name": null,
    "profile_picture": null,
    "email_verified": false,
    "is_staff": false,
    "is_active": true,
    "date_joined": "2026-02-21T06:07:28.102852Z",
    "last_login": "2026-02-21T06:07:28.149655Z"
  }
}
```

---

### 2. Login (Email & Password)
Log in with email and password. Returns both JWT tokens and the full user object.

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
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 14,
    "email": "user@example.com",
    "username": "user",
    "first_name": null,
    "last_name": null,
    "full_name": null,
    "profile_picture": null,
    "email_verified": false,
    "is_staff": false,
    "is_active": true,
    "date_joined": "2026-02-21T06:07:28.102852Z",
    "last_login": "2026-02-21T07:12:20.181539Z"
  }
}
```

---

### 3. Google OAuth Login
Login or auto-register using a Google account. The frontend gets a Google `access_token` and sends it here. The backend validates it, then creates or updates the user automatically.

- **Endpoint**: `POST /auth/google/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "access_token": "ya29.a0AfH6SMBx..."
}
```

- **Response (200 OK)**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 14,
    "email": "user@gmail.com",
    "username": "user",
    "first_name": "SOK",
    "last_name": "LIMKHY",
    "full_name": "SOK LIMKHY",
    "profile_picture": "https://lh3.googleusercontent.com/a/...",
    "email_verified": true,
    "is_staff": false,
    "is_active": true,
    "date_joined": "2026-02-21T06:07:28.102852Z",
    "last_login": "2026-02-21T07:16:44.742456Z"
  }
}
```

**Google fields auto-populated on user creation:**

| Google Field | AuthUser Field |
|---|---|
| `email` | `email` |
| `given_name` | `first_name` |
| `family_name` | `last_name` |
| `name` | `full_name` |
| `picture` | `profile_picture` |
| `verified_email` | `email_verified = True` |

**React Frontend Example:**
```javascript
import { useGoogleLogin } from '@react-oauth/google';

const login = useGoogleLogin({
  onSuccess: async ({ access_token }) => {
    const res = await fetch('http://localhost:8000/api/v1/auth/google/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ access_token }),
    });
    const data = await res.json();
    localStorage.setItem('access', data.access);
    localStorage.setItem('refresh', data.refresh);
  },
});
```

---

### 4. Logout
Blacklists the current refresh token, invalidating the session.

- **Endpoint**: `POST /auth/logout/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

- **Response (200 OK)**:
```json
{
  "detail": "Successfully logged out."
}
```

---

### 5. Get Current User
Returns the full profile of the currently authenticated user.

- **Endpoint**: `GET /auth/user/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "id": 14,
  "email": "user@example.com",
  "username": "user",
  "first_name": "SOK",
  "last_name": "LIMKHY",
  "full_name": "SOK LIMKHY",
  "profile_picture": "https://lh3.googleusercontent.com/...",
  "email_verified": true,
  "is_staff": false,
  "is_active": true,
  "date_joined": "2026-02-21T06:07:28.102852Z",
  "last_login": "2026-02-21T07:16:44.742456Z"
}
```

---

### 6. Update Current User (Full Replace)
Replace all editable user profile fields.

- **Endpoint**: `PUT /auth/user/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe"
}
```
- **Response (200 OK)**: Full updated user object (same shape as GET /auth/user/)

---

### 7. Update Current User (Partial)
Update one or more user profile fields without replacing everything.

- **Endpoint**: `PATCH /auth/user/`
- **Auth Required**: Yes
- **Request Body** (any subset of fields):
```json
{
  "first_name": "Johnny"
}
```
- **Response (200 OK)**: Full updated user object

---

### 8. Password Reset Request
Sends a password reset link to the given email (printed to console in development).

- **Endpoint**: `POST /auth/password/reset/`
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
  "detail": "Password reset e-mail has been sent."
}
```

---

### 9. Password Reset Confirm
Set a new password using the token from the reset email.

- **Endpoint**: `POST /auth/password/reset/confirm/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "uid": "MQ",
  "token": "abc123-...",
  "new_password1": "NewSecurePass123!",
  "new_password2": "NewSecurePass123!"
}
```
- **Response (200 OK)**:
```json
{
  "detail": "Password has been reset with the new password."
}
```

---

## 🔑 JWT Token Management

### 10. Refresh Access Token
Exchange a valid refresh token for a new access token. The old refresh token is blacklisted and a new one is returned.

- **Endpoint**: `POST /auth/token/refresh/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- **Response (200 OK)**:
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### 11. Verify Token
Check if a JWT token is still valid.

- **Endpoint**: `POST /auth/token/verify/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```
- **Response (200 OK)**: `{}` — token is valid
- **Response (401 Unauthorized)**: token is invalid or expired

---

## 📂 Project Management

All project endpoints require authentication. Users can only see, modify, or delete their own projects.

### 12. List Projects
Get a list of all projects owned by the currently authenticated user.

- **Endpoint**: `GET /api/v1/projects/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
[
  {
    "id": "d3f4b5c6-a1b2-c3d4-e5f6-g7h8i9j0k1l2",
    "name": "Q1 Revenue Analysis",
    "slug": "q1-revenue-analysis",
    "description": "Analysis of sales performance in first quarter",
    "category": "Sales",
    "status": "active",
    "color_code": "#4F46E5",
    "thumbnail": null,
    "is_favorite": true,
    "created_at": "2026-03-01T07:45:00Z",
    "updated_at": "2026-03-01T08:00:00Z",
    "last_accessed_at": "2026-03-01T08:00:00Z",
    "settings": {},
    "datasets": [
      {
        "id": 4,
        "file": "http://127.0.0.1:8000/media/datasets/2026/03/02/data.csv",
        "name": "sales_q1.csv",
        "file_format": "csv",
        "row_count": 1500,
        "column_count": 12,
        "uploaded_at": "2026-03-02T09:00:00Z"
      }
    ]
  }
]
```

---

### 13. Create Project
Create a new project. The `user` field is automatically set to the current user.

- **Endpoint**: `POST /api/v1/projects/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "name": "Market Research 2026",
  "description": "Exploring new market opportunities",
  "category": "Marketing",
  "color_code": "#EF4444"
}
```
- **Response (201 Created)**: Full project object.

---

### 14. Get Project Details
Retrieve details of a specific project by UUID.

- **Endpoint**: `GET /api/v1/projects/<uuid>/`
- **Auth Required**: Yes
- **Response (200 OK)**: Full project object.

---

### 15. Update Project (Full)
Replace all fields of a project.

- **Endpoint**: `PUT /api/v1/projects/<uuid>/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "name": "Updated Analysis Name",
  "description": "New description text",
  "category": "Finance",
  "status": "active",
  "is_favorite": false,
  "color_code": "#10B981"
}
```
- **Response (200 OK)**: Updated project object.

---

### 16. Update Project (Partial)
Update specific fields of a project (e.g., mark as favorite).

- **Endpoint**: `PATCH /api/v1/projects/<uuid>/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "is_favorite": true
}
```
- **Response (200 OK)**: Updated project object.

---

### 17. Delete Project
Permanently delete a project and all associated data.

- **Endpoint**: `DELETE /api/v1/projects/<uuid>/`
- **Auth Required**: Yes
- **Response (204 No Content)**: (Empty response)

---

## 📊 Dataset Management

Endpoints for adding data to a project via file upload or raw text paste.

### 18. Upload Dataset (File / Drag & Drop)
Use this for physical files selected via a file input or dragged into the UI.

- **Endpoint**: `POST /api/v1/datasets/upload/`
- **Auth Required**: Yes
- **Content-Type**: `multipart/form-data`
- **Request Body**:
    - `project`: (UUID) The ID of the project to attach this file to.
    - `file`: (Binary) The actual CSV, Excel, or JSON file.
    - `name`: (String, optional) custom name for the dataset.

- **Response (201 Created)**:
```json
{
  "id": 4,
  "project": "d3f4b5c6...",
  "file": "http://127.0.0.1:8000/media/datasets/2026/03/02/data.csv",
  "name": "sales_q1.csv",
  "file_format": "csv",
  "uploaded_at": "2026-03-02T09:00:00Z"
}
```

---

### 19. Paste Dataset (Raw Text)
Use this for users who want to copy-paste data directly into a text area.

- **Endpoint**: `POST /api/v1/datasets/paste/`
- **Auth Required**: Yes
- **Content-Type**: `application/json`
- **Request Body**:
```json
{
  "project": "d3f4b5c6...",
  "raw_data": "id,name,price\n1,Apples,1.50\n2,Oranges,2.00",
  "name": "Manual Entry",
  "format": "csv" 
}
```

- **Response (201 Created)**: Same as Upload Dataset.

---

### 20. Get Dataset Preview (Columns & Rows)
Returns the list of column names and a subset of rows. Supports CSV, Excel, and JSON.

- **Endpoint**: `GET /api/v1/datasets/items/<id>/preview/?rows=50`
- **Auth Required**: Yes
- **Query Parameters**:
    - `rows`: (Integer, optional) Number of rows to return. Default is `10`, max is `1000`.
- **Response (200 OK)**:
```json
{
  "columns": ["id", "name", "price"],
  "rows": [
    {"id": 1, "name": "Apples", "price": 1.50},
    {"id": 2, "name": "Oranges", "price": 2.00}
  ],
  "metadata": {
    "dtypes": {"id": "int64", "name": "object", "price": "float64"},
    "shape": [450, 3]
  },
  "summary": {
    "price": {"count": 450, "mean": 15.2, "std": 5.1, "min": 0.5, "max": 99.0}
  },
  "total_rows_hint": 450
}
```

---

### 21. Update Dataset (Rename)
Update metadata like the display name of a dataset.

- **Endpoint**: `PATCH /api/v1/datasets/items/<id>/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "name": "Updated Dataset Name"
}
```
- **Response (200 OK)**: Updated dataset object.

---

### 22. Delete Dataset
Permanently remove a dataset from the project and delete the file from storage.

- **Endpoint**: `DELETE /api/v1/datasets/items/<id>/`
- **Auth Required**: Yes
- **Response (204 No Content)**: (Empty response)

---

### 23. Clean Dataset (Transformations)
Apply a pipeline of cleaning operations (filling NAs, dropping duplicates, changing types). This creates a **new** cleaned version of the dataset.

- **Endpoint**: `POST /api/v1/datasets/items/<id>/clean/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "pipeline": [
    { "operation": "handle_na", "params": { "columns": ["age"], "strategy": "fill_mean" } },
    { "operation": "drop_columns", "params": { "columns": ["temp_id"] } }
  ]
}
```

#### 🛠️ Supported Operations (Top 10):

| Operation | Description | Parameters |
| :--- | :--- | :--- |
| **`handle_na`** | Handle missing values | `columns` (array/all), `strategy` (drop, fill_zero, fill_mean, fill_median) |
| **`drop_duplicates`** | Remove duplicate rows | `columns` (array/all) |
| **`astype`** | Change column data type | `column` (string), `target_type` (int, float, string, datetime) |
| **`drop_columns`** | Remove columns | `columns` (array) |
| **`rename_columns`** | Rename headers | `mapping` (object: `{"old": "new"}`) |
| **`trim_strings`** | Remove whitespace | `columns` (array/all) |
| **`case_convert`** | Change text case | `columns` (array), `case` (lower, upper, title) |
| **`replace_value`** | Replace specific value | `column` (string), `old_value`, `new_value` |
| **`outlier_clip`** | Cap extreme values | `columns` (array), `lower_quantile` (0.05), `upper_quantile` (0.95) |
| **`round_numeric`** | Round decimal points | `columns` (array), `decimals` (int) |
- **Response (200 OK)**: Returns the preview of the **newly created** cleaned dataset.
```json
{
  "columns": ["id", "name", "price", "age", "created_at"],
  "rows": [],
  "metadata": {
    "dtypes": {},
    "shape": [448, 5]
  },
  "summary": {},
  "total_rows_hint": 448,
  "dataset_id": 12,
  "name": "cleaned_sales_data.csv"
}
```

---

## 📊 Error Responses

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
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data or missing fields |
| 401 | Unauthorized | Missing, invalid, or expired token |
| 403 | Forbidden | Authenticated but not permitted |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server error |

---

## � Authentication Flow

### Email/Password
```
1. POST /api/v1/auth/registration/  →  {access, refresh, user}
2. Store access + refresh tokens on client
3. Every request: Authorization: Bearer <access>
4. When access expires (60 min): POST /api/v1/auth/token/refresh/
5. On logout: POST /api/v1/auth/token/logout/
```

### Google OAuth (SPA/Mobile)
```
1. Frontend: Google Sign-In  →  access_token from Google
2. POST /api/v1/auth/google/  with { access_token }
3. Receive JWT tokens  →  {access, refresh, user}
```
3. Backend validates with Google, creates/updates user
4. Returns {access, refresh, user}  — same as email login
5. Store tokens on client, use identically from here
```

### How to Decode Token Expiry (Frontend)
The expiry is embedded inside the JWT — no extra API call needed:
```javascript
const payload = JSON.parse(atob(accessToken.split('.')[1]));
const expiresAt = new Date(payload.exp * 1000);  // Unix → JS Date

if (Date.now() >= expiresAt) {
  // Token expired — call /auth/token/refresh/
}
```

---

## 🧪 Testing with cURL

**Register (minimum):**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/registration/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password1":"Pass123!","password2":"Pass123!"}'
```

**Login:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Pass123!"}'
```

**Get Current User:**
```bash
curl -X GET http://127.0.0.1:8000/api/v1/auth/user/ \
  -H "Authorization: Bearer <access_token>"
```

**Refresh Token:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

**Logout:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/logout/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

**List Projects:**
```bash
curl -X GET http://127.0.0.1:8000/api/v1/projects/ \
  -H "Authorization: Bearer <access_token>"
```

**Create Project:**
```bash
curl -X POST http://127.0.0.1:8000/api/v1/projects/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name":"New Project","category":"Data"}'
```

---

## 📝 Custom User Model

- **Model**: `core.models.AuthUser`
- **Auth field**: `email` (unique, used for login)
- **Required on registration**: `email`, `password1`, `password2`
- **Optional on registration**: `username` (auto-gen from email), `first_name`, `last_name`
- **Read-only**: `id`, `email`, `email_verified`, `date_joined`, `last_login`

---

## 🔗 Resources

- **Admin Panel**: http://127.0.0.1:8000/admin/
    - email : dev_admin@pyanalypt.com
    - password : devadminpass123

---

**Last Updated**: 2026-03-01
**API Version**: v1
**Status**: ✅ Active
