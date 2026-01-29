# PyAnalypt API Documentation

Base URL: `http://localhost:8000/api`

## Authentication

### 1. Register New User
Creates a new user account.

*   **Endpoint:** `/auth/registration/` (Updated for dj-rest-auth)
*   **Method:** `POST`
*   **Auth Required:** No
*   **Body:**
    ```json
    {
      "username": "johndoe", (Optional if email is primary)
      "email": "john@example.com",
      "password1": "strongpassword123",
      "password2": "strongpassword123" (Optional validation)
    }
    ```
*   **Response (201 Created):**
    ```json
    {
      "access": "eyJ...",
      "refresh": "eyJ...",
      "user": {
          "pk": 1,
          "username": "",
          "email": "john@example.com",
          "first_name": "",
          "last_name": ""
      }
    }
    ```

### 2. Login (Get Token)
*   **Endpoint:** `/auth/login/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
      "email": "john@example.com",
      "password": "strongpassword123"
    }
    ```
*   **Response (200 OK):**
    ```json
    {
      "access": "eyJ...",
      "refresh": "eyJ...",
      "user": { ... }
    }
    ```

### 3. Google Login
*   **Endpoint:** `/auth/google/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
      "access_token": "GOOGLE_ACCESS_TOKEN_FROM_FRONTEND"
    }
    ```

### 4. Logout
*   **Endpoint:** `/auth/logout/`
*   **Method:** `POST`


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
