# PyAnalypt API Documentation

## Base URLs

- **Development**: `http://127.0.0.1:8000/api/v1/`
- **Production**: `https://api.pyanalypt.com/api/v1/`

## Authentication

All authenticated endpoints require a JWT token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## 🔐 Authentication Endpoints

### 1. Register New User
Create a new user account using only email and password. Other profile fields are optional.

- **Endpoint**: `POST /auth/registration/`
- **Auth Required**: No
- **Request Body (Minimum)**:
```json
{
  "email": "user@example.com",
  "password1": "SecurePass123!",
  "password2": "SecurePass123!"
}
```

- **Request Body (Full - Optional Fields)**:
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
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "pk": 2,
    "email": "user@example.com",
    "username": "user",
    "first_name": null,
    "last_name": null
  }
}
```

---

### 2. Login (Email/Password)
Log in with your email and password to receive JWT tokens.

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
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
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
    "last_login": "2026-02-21T06:07:28.149655Z"
  }
}
```

---

### 3. Google OAuth Login
Login or register using Google account (for frontend applications).

- **Endpoint**: `POST /auth/google/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "access_token": "ya29.a0AfH6SMBx..." 
}
```

**How it works:**
1. Frontend uses Google Sign-In to get `access_token`
2. Frontend sends `access_token` to this endpoint
3. Backend validates token with Google
4. Backend creates/updates user with Google data
5. Backend returns JWT tokens

- **Response (200 OK)**:
```json
{
  "access": "eyJ0eXAiOiJKV1Qi...",
  "refresh": "eyJ0eXAiOiJKV1Qi...",
  "user": {
    "pk": 5,
    "email": "user@gmail.com",
    "username": "user",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "profile_picture": "https://lh3.googleusercontent.com/...",
    "email_verified": true
  }
}
```

**Frontend Integration Example (React):**
```javascript
import { GoogleOAuthProvider, useGoogleLogin } from '@react-oauth/google';

function GoogleLoginButton() {
  const login = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      // Send access_token to your backend
      const response = await fetch('http://localhost:8000/api/v1/auth/google/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          access_token: tokenResponse.access_token
        })
      });
      
      const data = await response.json();
      // Save JWT tokens
      localStorage.setItem('access', data.access);
      localStorage.setItem('refresh', data.refresh);
    }
  });

  return <button onClick={() => login()}>Sign in with Google</button>;
}
```

---

### 4. Logout
Logout and blacklist the current refresh token.

- **Endpoint**: `POST /auth/logout/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "detail": "Successfully logged out."
}
```

---

### 5. Get Current User
Retrieve details of the currently authenticated user.

- **Endpoint**: `GET /auth/user/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "pk": 2,
  "email": "user@example.com",
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe Example",
  "profile_picture": "https://lh3.googleusercontent.com/...",
  "email_verified": true,
  "is_staff": false,
  "is_active": true,
  "date_joined": "2026-02-10T08:30:00Z",
  "last_login": "2026-02-10T10:00:00Z"
}
```

---

### 5. Update Current User (Full)
Update all user profile fields.

- **Endpoint**: `PUT /auth/user/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "username": "johndoe",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe Updated",
  "email": "user@example.com"
}
```

- **Response (200 OK)**: Updated user object

---

### 6. Update Current User (Partial)
Update specific user profile fields.

- **Endpoint**: `PATCH /auth/user/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "first_name": "Johnny"
}
```

- **Response (200 OK)**: Updated user object

---

### 7. Password Reset Request
Request a password reset email.

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

### 8. Password Reset Confirm
Confirm password reset with token from email.

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

---

### 9. Google OAuth Login
Initiate Google OAuth login flow.

- **Endpoint**: `GET /accounts/google/login/`
- **Auth Required**: No
- **Flow**:
  1. User is redirected to Google OAuth consent screen
  2. User authorizes application
  3. Callback to `/accounts/google/login/callback/`
  4. User is created/updated with Google metadata
  5. JWT tokens are returned

**Google Metadata Extracted**:
- Email → `user.email`
- First Name → `user.first_name`
- Last Name → `user.last_name`
- Full Name → `user.full_name`
- Profile Picture → `user.profile_picture`
- Email Verified → `user.email_verified = True`

---

## 🔑 JWT Token Management

### 10. Obtain JWT Token
Get access and refresh tokens (alternative to login endpoint).

- **Endpoint**: `POST /auth/token/`
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
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

### 11. Refresh JWT Token
Obtain a new access token using a refresh token.

- **Endpoint**: `POST /auth/token/refresh/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

- **Response (200 OK)**:
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Note**: Token rotation is enabled. A new refresh token is returned and the old one is blacklisted.

---

### 12. Verify JWT Token
Verify if a JWT token is valid.

- **Endpoint**: `POST /auth/token/verify/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

- **Response (200 OK)**: Empty object `{}` (token is valid)
- **Response (401 Unauthorized)**: Token is invalid or expired

---

## 📁 File Operations

### 13. Upload File
Upload a dataset (CSV, Excel, Parquet) for analysis. Supports both authenticated and guest users.

- **Endpoint**: `POST /upload/`
- **Content-Type**: `multipart/form-data`
- **Auth Required**: Optional

#### Scenario A: Authenticated User
- **Headers**: `Authorization: Bearer <access_token>`
- **Form Data**:
  - `file`: (File binary)
  - `session_id`: (Optional/Ignored)

#### Scenario B: Guest User
- **Headers**: None
- **Form Data**:
  - `file`: (File binary)
  - `session_id`: "unique-uuid-string" (Required for guests)

- **Response (201 Created)**:
```json
{
  "id": "a1b2c3d4-e5f6-...",
  "file": "/media/uploads/2026/02/10/data.csv",
  "original_filename": "data.csv",
  "file_size": 1024,
  "session_id": "...",
  "uploaded_at": "2026-02-10T08:30:00Z"
}
```

---

## 📊 Error Responses

### Standard Error Format
```json
{
  "detail": "Error message description",
  "code": "error_code"
}
```

### Common HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required or failed |
| 403 | Forbidden | Permission denied |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

---

## 🔒 Authentication Flow

### Email/Password Registration & Login

```
1. Register
   POST /api/v1/auth/registration/
   → Returns: access + refresh tokens

2. Use Access Token
   GET /api/v1/auth/user/
   Headers: Authorization: Bearer <access_token>

3. Refresh Expired Token
   POST /api/v1/auth/token/refresh/
   Body: { "refresh": "<refresh_token>" }
   → Returns: new access + refresh tokens

4. Logout
   POST /api/v1/auth/logout/
   → Blacklists refresh token
```

### Google OAuth Flow

```
1. Initiate OAuth
   GET /accounts/google/login/
   → Redirects to Google

2. User Authorizes
   → Google callback

3. Backend Processing
   - Extract Google metadata
   - Create/update AuthUser
   - Populate: name, email, picture, email_verified

4. Return Tokens
   → JWT access + refresh tokens
```

---

## 🧪 Testing Examples

### cURL Examples

#### Register
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/registration/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User",
    "full_name": "Test User Example",
    "password1": "SecurePass123!",
    "password2": "SecurePass123!"
  }'
```

#### Login
```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123!"
  }'
```

#### Get Current User
```bash
curl -X GET http://127.0.0.1:8000/api/v1/auth/user/ \
  -H "Authorization: Bearer <your_access_token>"
```

#### Update User
```bash
curl -X PATCH http://127.0.0.1:8000/api/v1/auth/user/ \
  -H "Authorization: Bearer <your_access_token>" \
  -H "Content-Type: application/json" \
  -d '{"first_name": "Updated"}'
```

---

## 📝 Notes

### JWT Token Lifetimes
- **Access Token**: 60 minutes
- **Refresh Token**: 1 day
- **Token Rotation**: Enabled (new refresh token on each refresh)
- **Blacklisting**: Enabled (old tokens invalidated on refresh/logout)

### Custom User Model
- **Model**: `core.models.AuthUser`
- **Authentication**: Email-based (email is the USERNAME_FIELD)
- **Required Fields**: email, username, first_name, last_name, full_name, password
- **Optional Fields**: profile_picture
- **Google OAuth**: Automatically populates name, email, picture, email_verified

### API Versioning
- Current version: **v1**
- Base path: `/api/v1/`
- Future versions will use `/api/v2/`, etc.

### Rate Limiting
*To be implemented*

### Pagination
*To be implemented*

---

## 🔗 Additional Resources

- **Admin Panel**: http://127.0.0.1:8000/admin/
- **Django Admin Credentials**: 
  - Email: `admin@pyanalypt.com`
  - Password: `admin123!@#`

---

**Last Updated**: 2026-02-10  
**API Version**: v1  
**Status**: ✅ Production Ready
