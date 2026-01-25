# PyAnalypt API Documentation

Base URL: `http://localhost:8000/api`

## Authentication

### 1. Register New User
Creates a new user account.

*   **Endpoint:** `/auth/register/`
*   **Method:** `POST`
*   **Auth Required:** No
*   **Body:**
    ```json
    {
      "username": "johndoe",
      "email": "john@example.com",
      "password": "strongpassword123"
    }
    ```
*   **Response (201 Created):**
    ```json
    {
      "username": "johndoe",
      "email": "john@example.com"
      // Note: Password is never returned
    }
    ```

### 2. Login (Get Token)
Exchanges user credentials for access and refresh tokens.

*   **Endpoint:** `/auth/login/`
*   **Method:** `POST`
*   **Auth Required:** No
*   **Body:**
    ```json
    {
      "username": "johndoe",
      "password": "strongpassword123"
    }
    ```
*   **Response (200 OK):**
    ```json
    {
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1...",
      "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1..."
    }
    ```

### 3. Refresh Token
Get a new access token using a valid refresh token.

*   **Endpoint:** `/auth/refresh/`
*   **Method:** `POST`
*   **Auth Required:** No
*   **Body:**
    ```json
    {
      "refresh": "your_refresh_token_here"
    }
    ```
*   **Response (200 OK):**
    ```json
    {
      "access": "new_access_token_here"
    }
    ```

### 4. Get Current User
Retrieve details of the currently logged-in user.

*   **Endpoint:** `/auth/user/`
*   **Method:** `GET`
*   **Auth Required:** Yes
*   **Headers:**
    *   `Authorization: Bearer <your_access_token>`
*   **Response (200 OK):**
    ```json
    {
      "id": 1,
      "username": "johndoe",
      "email": "john@example.com"
    }
    ```

---

## File Operations

### 5. Upload File
Upload a dataset (CSV, Excel, Parquet) for analysis. Supports both Authenticated and Guest users.

*   **Endpoint:** `/upload/`
*   **Method:** `POST`
*   **Content-Type:** `multipart/form-data`
*   **Auth Required:** Optional (See Logic below)

#### **Scenario A: Authenticated User**
*   **Headers:**
    *   `Authorization: Bearer <your_access_token>`
*   **Body (FormData):**
    *   `file`: (The file binary)
    *   `session_id`: (Optional/Ignored)

#### **Scenario B: Guest User (Anonymous)**
*   **Headers:** None
*   **Body (FormData):**
    *   `file`: (The file binary)
    *   `session_id`: "unique-uuid-string" (Required for guests)

#### **Response (201 Created)**
The backend automatically triggers data analysis upon successful upload.

```json
{
    "id": "a1b2c3d4-e5f6-...",
    "file": "/media/uploads/2026/01/23/data.csv",
    "original_filename": "data.csv",
    "file_size": 1024,
    "session_id": "...", 
    "uploaded_at": "2026-01-23T07:30:00Z"
}
```

#### **Error Responses**
*   **400 Bad Request:** Missing file or missing `session_id` (for guests).
*   **401 Unauthorized:** Invalid token (if provided).
*   **500 Internal Server Error:** File processing or analysis failed.
