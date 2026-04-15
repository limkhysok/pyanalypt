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

### 1. Register New User (Step 1)
Create a new inactive account with just email and password. A 6-digit verification code is sent to the email.

- **Endpoint**: `POST /auth/registration/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```
> Only `email` and `password` are required. No confirmation password field is needed on the backend.

- **Response (201 Created)**:
```json
{
  "detail": "Initial registration successful. Please check your email for the 6-digit verification code."
}
```

---

### 2. Resend Registration OTP
Request a new 6-digit verification code if the previous one expired or was not received.

- **Endpoint**: `POST /auth/registration/resend-otp/`
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
  "detail": "A new verification code has been sent to your email."
}
```

---

### 3. Verify Registration OTP (Step 2)
Activate the account and verify the email address. On success, JWT tokens are issued. The user is now authenticated but must complete their profile.

- **Endpoint**: `POST /auth/registration/verify-otp/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "email": "user@example.com",
  "otp": "123456"
}
```
- **Response (200 OK)**:
```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>",
  "requires_profile_completion": true,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "user_1234567890",
    "full_name": "",
    "birthday": null,
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

### 4. Complete Profile (Step 3)
Finalize the registration by setting a unique username, full name, and birthday.

- **Endpoint**: `POST /auth/registration/complete-profile/`
- **Auth Required**: Yes (JWT access token)
- **Request Body**:
```json
{
  "username": "johndoe",
  "full_name": "John Doe",
  "birthday": "1995-05-20"
}
```
- **Response (200 OK)**:
```json
{
  "detail": "Profile completed successfully.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "birthday": "1995-05-20",
    "email_verified": true,
    "is_active": true
  }
}
```

> **Frontend flow:**
> 1. User submits email/password → `POST /auth/registration/`
> 2. On `201 Created` → redirect to `/verify-otp?email=user@example.com`
> 3. User enters 6-digit code → `POST /auth/registration/verify-otp/`
> 4. On `200 OK` → store tokens and redirect to `/complete-profile`
> 5. User enters username, name, and birthday → `POST /auth/registration/complete-profile/`
> 6. On `200 OK` → redirect to `/dashboard`


---

### 5. Login
Log in with **email and password**. The response differs depending on whether the user has 2FA enabled.

- **Endpoint**: `POST /auth/login/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

#### Case A — 2FA disabled (normal login)
- **Response (200 OK)**:
```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>",
  "requires_profile_completion": true,
  "user": { ... }
}
```
> **IMPORTANT**: Check for `requires_profile_completion`. If `true`, the user has verified their email but has **not** completed Step 3 (username/full_name/birthday). Redirect them to `/complete-profile`.

#### Case B — 2FA enabled
- **Response (202 Accepted)**:
```json
{
  "requires_2fa": true,
  "totp_token": "<token>"
}
```

#### Case C — Email Not Verified
- **Response (403 Forbidden)**:
```json
{
  "detail": "Email address not verified.",
  "requires_verification": true,
  "email": "user@example.com"
}
```
> **IMPORTANT**: If the user tries to log in with an unverified email, they are blocked. Redirect them back to the `/verify-otp` page using the `email` provided in the response.
> **No JWT tokens are issued yet.** The `totp_token` expires in **5 minutes**.
> Frontend must redirect to the 2FA code screen and call [`POST /auth/2fa/verify-login/`](#10-complete-login-with-2fa-code) to finish.

> **Frontend flow for 2FA login:**
> 1. `POST /auth/login/` → check if `requires_2fa === true`
> 2. If yes → store `totp_token` in component state (not localStorage)
> 3. Show a 6-digit code input screen
> 4. User opens Google Authenticator, enters the code
> 5. `POST /auth/2fa/verify-login/` with `{ totp_token, code }` → receive JWT tokens
> 6. If `totp_token` expires → send user back to login

---

### 6. Logout
Invalidate the current session by blacklisting the refresh token.

- **Endpoint**: `POST /auth/logout/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "refresh": "<refresh_token>"
}
```
- **Response (200 OK)**:
```json
{
  "detail": "Successfully logged out."
}
```

---

### 7. Get Current User
Retrieve profile information for the authenticated user.

- **Endpoint**: `GET /auth/user/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "birthday": "1995-05-20",
  "profile_picture": null,
  "email_verified": true,
  "is_staff": false,
  "is_active": true,
  "date_joined": "2026-03-21T00:00:00Z",
  "last_login": "2026-03-21T06:00:00Z"
}
```

---

### 8. Update Profile
Update your profile name. Only these two fields are writable — all others are read-only and will be silently ignored if sent.

- **Endpoint**: `PATCH /auth/user/`
- **Auth Required**: Yes

| Field | Writable | Notes |
|---|---|---|
| `full_name` | ✅ Yes | Letters, hyphens, apostrophes, and spaces only |
| `birthday` | ✅ Yes | Date in YYYY-MM-DD format |
| `email` | ❌ Read-only | Cannot be changed via this endpoint |
| `username` | ❌ Read-only | Set during profile completion, not editable after |
| `profile_picture` | ❌ Read-only | Set via Google OAuth only |

- **Request Body** *(send only the fields you want to change)*:
```json
{
  "full_name": "Jonathan Doe"
}
```
- **Response (200 OK)**: Full user object (same shape as GET /auth/user/).

---

### 9. Change Password
Change password while authenticated. The user stays logged in after this.

- **Endpoint**: `POST /auth/password/change/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "new_password1": "NewSecurePass456!",
  "new_password2": "NewSecurePass456!"
}
```
- **Response (200 OK)**:
```json
{
  "detail": "New password has been saved."
}
```

---

### 10. Password Reset (Forgot Password)
Send a password reset link to the user's email.

**Step 1 — Request reset email**
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

**Step 2 — Confirm new password**
- **Endpoint**: `POST /auth/password/reset/confirm/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "uid": "<uid_from_reset_link>",
  "token": "<token_from_reset_link>",
  "new_password1": "NewSecurePass456!",
  "new_password2": "NewSecurePass456!"
}
```
- **Response (200 OK)**:
```json
{
  "detail": "Password has been reset with the new password."
}
```

> **Frontend flow:**
> 1. User submits their email on the "Forgot Password" page → `POST /auth/password/reset/`
> 2. User receives email with a link like `http://localhost:3000/reset-password/<uid>/<token>/`
> 3. Frontend extracts `uid` and `token` from the URL
> 4. User types a new password → `POST /auth/password/reset/confirm/` with `uid`, `token`, and both password fields
> 5. On `200 OK` → redirect to `/login`

---

## 🔑 JWT Token Management

### 11. Refresh Access Token
Exchange a refresh token for a new access token. A new refresh token is also returned (rotation enabled). The active session record is updated automatically.

- **Endpoint**: `POST /auth/token/refresh/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "refresh": "<refresh_token>"
}
```
- **Response (200 OK)**:
```json
{
  "access": "<new_access_token>",
  "refresh": "<new_refresh_token>"
}
```
> Always replace both stored tokens when this endpoint responds. The old refresh token is immediately invalidated.

### 12. Verify Token
Check if an access or refresh token is still valid.

- **Endpoint**: `POST /auth/token/verify/`
- **Auth Required**: No
- **Request Body**: `{ "token": "<token>" }`
- **Response (200 OK)**: `{}` *(empty body = valid)*
- **Response (401)**: Token is expired or invalid.

---

## 🔒 Two-Factor Authentication (TOTP)

All 2FA endpoints require the user to be **logged in** (JWT Bearer token), except `verify-login` which is used before tokens are issued.

### 13. Setup 2FA — Get QR Code
Generates a new TOTP secret and returns the `otpauth://` URI for rendering a QR code. This does **not** enable 2FA yet — the user must scan and confirm first.

- **Endpoint**: `GET /auth/2fa/setup/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "otpauth_uri": "otpauth://totp/PyAnalypt:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=PyAnalypt"
}
```

> **Frontend flow:**
> 1. Call `GET /auth/2fa/setup/`
> 2. Render `otpauth_uri` as a QR code using a library like [`qrcode.react`](https://www.npmjs.com/package/qrcode.react)
> 3. Also show the raw `secret` as a fallback for manual entry in Google Authenticator
> 4. Prompt user to scan and enter their first code to confirm → `POST /auth/2fa/enable/`

---

### 14. Enable 2FA
Activates 2FA by verifying the first TOTP code from the authenticator app. Must be called after `GET /auth/2fa/setup/`.

- **Endpoint**: `POST /auth/2fa/enable/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "code": "123456"
}
```
> `code` must be exactly **6 digits** (e.g. `"123456"`). Non-digit characters are rejected.
- **Response (200 OK)**:
```json
{
  "detail": "2FA enabled successfully."
}
```
- **Response (400)** if code is wrong:
```json
{
  "code": ["Invalid or expired code."]
}
```

---

### 15. Disable 2FA
Turns off 2FA. Requires both the current password and a valid TOTP code to confirm intent.

- **Endpoint**: `POST /auth/2fa/disable/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "code": "123456",
  "password": "CurrentPassword123!"
}
```
> `code` must be exactly **6 digits**. Non-digit characters are rejected.
- **Response (200 OK)**:
```json
{
  "detail": "2FA disabled successfully."
}
```

---

### 16. Complete Login with 2FA Code
Finishes a login that was paused by the 2FA gate. Receives the same JWT response as a normal login.

- **Endpoint**: `POST /auth/2fa/verify-login/`
- **Auth Required**: No *(user is not authenticated yet at this point)*
- **Request Body**:
```json
{
  "totp_token": "<token_from_login_response>",
  "code": "123456"
}
```
> `code` must be exactly **6 digits**. `totp_token` comes from the `202 Accepted` response of `POST /auth/login/` or `POST /auth/google/`.

- **Response (200 OK)**:
```json
{
  "access": "<access_token>",
  "refresh": "<refresh_token>",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "birthday": "1995-05-20",
    "profile_picture": null,
    "email_verified": true,
    "is_staff": false,
    "is_active": true,
    "date_joined": "2026-03-21T00:00:00Z",
    "last_login": "2026-03-21T06:00:00Z"
  }
}
```
- **Response (400)** if `totp_token` expired (> 5 minutes):
```json
{
  "detail": "Token expired, please log in again."
}
```
- **Response (400)** if account has been deactivated:
```json
{
  "detail": "Account is disabled."
}
```

---

## 📱 Session Management

Each login creates a session record that tracks the device, browser, and IP address. Sessions are tied to refresh tokens — revoking a session blacklists its token immediately.

### Session Object

| Field | Type | Description |
|---|---|---|
| `id` | int | Session identifier |
| `device` | string | Device family (e.g. `"iPhone"`, `"Desktop"`) |
| `browser` | string | Browser and OS (e.g. `"Chrome on Windows"`) |
| `ip_address` | string | IP address at login |
| `created_at` | datetime | When the session was created (login time) |
| `last_active` | datetime | Last time the refresh token was used |

---

### 17. List Active Sessions
Returns all active sessions for the current user.

- **Endpoint**: `GET /auth/sessions/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
[
  {
    "id": 3,
    "device": "Desktop",
    "browser": "Chrome on Windows",
    "ip_address": "192.168.1.10",
    "created_at": "2026-04-14T08:00:00Z",
    "last_active": "2026-04-14T09:30:00Z"
  },
  {
    "id": 4,
    "device": "iPhone",
    "browser": "Mobile Safari on iOS",
    "ip_address": "10.0.0.5",
    "created_at": "2026-04-13T20:00:00Z",
    "last_active": "2026-04-13T20:45:00Z"
  }
]
```

> **Frontend tip:** You can visually highlight the "current" session by comparing `ip_address` and `browser` against the user's current device. There is no explicit `is_current` flag — identify it by recency (`last_active`) or matching UA.

---

### 18. Revoke a Specific Session
Blacklists the refresh token for that session, forcing that device to log in again.

- **Endpoint**: `DELETE /auth/sessions/{id}/`
- **Auth Required**: Yes
- **Response (204 No Content)**: *(empty — success)*
- **Response (404)**: Session not found or doesn't belong to the current user.

---

### 19. Revoke All Sessions (Logout Everywhere)
Blacklists **all** active sessions for the current user, including the current one. The user will need to log in again on all devices.

- **Endpoint**: `POST /auth/sessions/revoke-all/`
- **Auth Required**: Yes
- **Request Body**: *(empty)*
- **Response (200 OK)**:
```json
{
  "detail": "Revoked 3 session(s)."
}
```

> **Frontend tip:** After calling this endpoint, immediately clear stored tokens and redirect to `/login`.

---

## 🌐 Google OAuth

### 20. Google Login
Exchange a Google OAuth `access_token` for PyAnalypt JWT tokens. New users are registered automatically.

- **Endpoint**: `POST /auth/google/`
- **Auth Required**: No
- **Request Body**:
```json
{
  "access_token": "<google_access_token>"
}
```

#### Case A — 2FA disabled (normal)
- **Response (200 OK)**: Same shape as normal login (access + refresh + user).

#### Case B — 2FA enabled on the account
- **Response (202 Accepted)**:
```json
{
  "requires_2fa": true,
  "totp_token": "<short_lived_signed_token>"
}
```
> JWT tokens are **not** issued yet. Pass `totp_token` to `POST /auth/2fa/verify-login/` with the TOTP code to complete login. The token expires in **5 minutes**.

> **Frontend flow:**
> 1. Trigger Google Sign-In using the Google Identity SDK
> 2. On success, receive a Google `access_token`
> 3. `POST /api/v1/auth/google/` with `{ "access_token": "<google_token>" }`
> 4. If `requires_2fa === true` → treat identically to the 2FA branch of `POST /auth/login/` (show code screen, call `POST /auth/2fa/verify-login/`)
> 5. Otherwise, store the returned JWT tokens normally

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
| 202 | Accepted | Credentials valid but action pending — 2FA code required to complete login |
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
