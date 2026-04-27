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
Finalize the registration by setting a unique username, full name, and birthday. Can only be called once — calling it again after the profile is already set returns a 400 error.

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
- **Response (400)** if profile is already completed:
```json
{
  "detail": "Profile has already been completed."
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
Update one or more profile fields. Send only the fields you want to change — unset fields are left as-is. `email` is the only permanently read-only field.

- **Endpoint**: `PATCH /auth/user/`
- **Auth Required**: Yes

| Field | Writable | Validation |
|---|---|---|
| `username` | ✅ Yes | 3–150 chars; letters, numbers, dots, underscores, hyphens only; must be unique |
| `full_name` | ✅ Yes | 2–255 chars; letters, hyphens, apostrophes, and spaces only |
| `birthday` | ✅ Yes | YYYY-MM-DD; must be in the past and no more than 120 years ago |
| `profile_picture` | ✅ Yes | Must be a valid HTTPS URL; send `null` to clear |
| `email` | ❌ Read-only | Cannot be changed |

- **Request Body** *(any subset of writable fields)*:
```json
{
  "username": "johnny",
  "full_name": "Jonathan Doe",
  "birthday": "1995-05-20",
  "profile_picture": "https://example.com/avatar.jpg"
}
```
- **Response (200 OK)**: Full user object (same shape as `GET /auth/user/`).
- **Response (400)** examples:
```json
{ "username": ["This username is already taken."] }
{ "birthday": ["Birthday must be in the past."] }
{ "profile_picture": ["Profile picture URL must use HTTPS protocol for security."] }
```

---

### 9. Change Password
Change password while authenticated. The current session stays active; all **other** active sessions are revoked automatically so other devices are forced to log in again.

- **Endpoint**: `POST /auth/password/change/`
- **Auth Required**: Yes
- **Rate Limit**: 5 requests/hour per user
- **Request Body**:
```json
{
  "old_password": "CurrentPass123!",
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
- **Response (400)** if `old_password` is wrong:
```json
{
  "old_password": ["Your old password was entered incorrectly. Please enter it again."]
}
```

> All sessions except the one making this request are blacklisted immediately. The current device stays logged in.

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
- **Rate Limit**: 20 requests/hour per user
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
- **Rate Limit**: 20 requests/hour per user
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
- **Rate Limit**: 20 requests/hour per user
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
- **Rate Limit**: 10 requests/hour per IP
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
| `is_current` | boolean | `true` if this session belongs to the token making the request |

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
    "last_active": "2026-04-14T09:30:00Z",
    "is_current": true
  },
  {
    "id": 4,
    "device": "iPhone",
    "browser": "Mobile Safari on iOS",
    "ip_address": "10.0.0.5",
    "created_at": "2026-04-13T20:00:00Z",
    "last_active": "2026-04-13T20:45:00Z",
    "is_current": false
  }
]
```

> **Frontend tip:** Use `is_current: true` to highlight and protect the active session in the UI. When building a "sign out all other devices" flow, skip the session where `is_current` is `true` and call `DELETE /auth/sessions/{id}/` on the rest, or use `POST /auth/sessions/revoke-all/` (which revokes everything including the current session).

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

### Dataset Object

| Field | Type | Description |
|---|---|---|
| `id` | int | Unique identifier |
| `user` | int | Owner user ID |
| `file` | string | URL to the stored file |
| `file_name` | string | Display name of the file |
| `file_format` | string | File extension (`csv`, `xlsx`, `json`, `parquet`) |
| `file_size` | int | File size in bytes |
| `uploaded_date` | datetime | When the file was first uploaded |
| `updated_date` | datetime | Last modification timestamp |

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

### 3. Delete Dataset
Removes the dataset record and its associated file from storage. Also logs the DELETE action.

- **Endpoint**: `DELETE /datasets/{id}/`
- **Auth Required**: Yes
- **Response (204 No Content)**

### 4. Rename Dataset
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
- **Response (400)** if `file_name` is missing or blank.

### 5. Export Dataset
Download the dataset converted to a requested format. Defaults to the dataset's original format if `?format` is omitted.

- **Endpoint**: `GET /datasets/{id}/export/`
- **Auth Required**: Yes
- **Query Params**: `?format=csv` *(options: `csv`, `json`, `xlsx`, `parquet`)*
- **Response**: Binary file download with appropriate `Content-Disposition` header.
- **Response (400)** if the format is unsupported.

### 6. Duplicate Dataset
Clone an existing dataset into a new record. Supports on-the-fly format conversion and maintains data lineage via the `parent` field.

- **Endpoint**: `POST /datasets/{id}/duplicate/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "new_file_name": "Sales Copy",
  "format": "csv"
}
```
> Both fields are optional. `new_file_name` defaults to `<original>_copy`. `format` defaults to the source dataset's format. Supported formats: `csv`, `json`, `xlsx`, `parquet`.

- **Response (201 Created)**: `Dataset` object of the new clone.

### 7. Activity Logs
Retrieve a stream of activities performed on datasets.

- **Endpoint**: `GET /datasets/activity_logs/`
- **Auth Required**: Yes
- **Query Params**: `?dataset={id}` *(optional — filter logs by a specific dataset)*
- **Response (200 OK)**:
```json
[
  {
    "id": 42,
    "user": 1,
    "dataset": 15,
    "dataset_name_snap": "survey.csv",
    "action": "UPLOAD",
    "details": {},
    "timestamp": "2026-03-17T10:00:00Z"
  }
]
```

**All logged action types:**

| Action | Triggered by | `details` payload |
|---|---|---|
| `UPLOAD` | File upload | `{}` |
| `RENAME` | Dataset rename | `{}` |
| `DELETE` | Dataset delete | `{}` |
| `DUPLICATE` | Dataset duplicate | `{}` |
| `EXPORT` | Dataset export | `{}` |
| `UPDATE_CELL` | Update cell | `{ row_index, column, value }` |
| `CAST` | Cast columns | `{ columns: { col: type } }` |
| `RENAME_COLUMN` | Rename column | `{ old_name, new_name }` |
| `DROP_DUPLICATES` | Drop duplicates | `{ mode, rows_dropped }` |
| `REPLACE_VALUES` | Replace values | `{ cells_replaced, columns }` |
| `DROP_NULLS` | Drop nulls | `{ axis, rows_dropped }` or `{ axis, columns_dropped }` |
| `FILL_NULLS` | Fill nulls | `{ strategy, cells_filled }` |
| `FILL_DERIVED` | Fill derived | `{ target, formula, cells_filled }` |
| `FIX_FORMULA` | Fix formula | `{ target, formula, cells_fixed }` |
| `TRIM_OUTLIERS` | Trim outliers | `{ method, threshold, rows_dropped }` |
| `IMPUTE_OUTLIERS` | Impute outliers | `{ method, strategy, cells_imputed }` |
| `CAP_OUTLIERS` | Cap outliers | `{ lower_pct, upper_pct, cells_capped }` |
| `TRANSFORM_COLUMN` | Transform column | `{ function, columns }` |

---

## 🧪 Datalab

The Datalab is the **data wrangling layer** — inspect, clean, transform, and audit datasets before analysis. It covers the full preparation pipeline: preview, inspect, type casting, null handling, deduplication, formula validation, and outlier treatment.

All endpoints below are under `/api/v1/datalab/`.

| # | Method | Endpoint | Description |
|---|--------|----------|-------------|
| 1 | `GET` | `/datalab/preview/{dataset_id}/` | Render dataset as a data table |
| 2 | `GET` | `/datalab/inspect/{dataset_id}/` | Return per-column dtype, null counts, null %, and memory usage |
| 3 | `GET` | `/datalab/describe/{dataset_id}/` | Return descriptive statistics for all columns (`df.describe()`) |
| 4 | `POST` | `/datalab/fill-derived/{dataset_id}/` | Fill nulls in a column by deriving values from two other columns using arithmetic |
| 5 | `POST` | `/datalab/validate-formula/{dataset_id}/` | Check whether a column's values match a formula across two operand columns |
| 6 | `POST` | `/datalab/fix-formula/{dataset_id}/` | Overwrite inconsistent values in a column by recomputing from trusted columns |
| 7 | `POST` | `/datalab/cast/{dataset_id}/` | Cast one or more columns to a new dtype and persist the change |
| 8 | `POST` | `/datalab/drop-duplicates/{dataset_id}/` | Remove duplicate rows and persist the cleaned dataset |
| 9 | `POST` | `/datalab/rename-column/{dataset_id}/` | Rename a column header and persist the change |
| 10 | `PATCH` | `/datalab/update-cell/{dataset_id}/` | Edit a single cell value with dtype validation |
| 11 | `POST` | `/datalab/replace-values/{dataset_id}/` | Replace sentinel/garbage values with NaN or another value |
| 12 | `POST` | `/datalab/drop-nulls/{dataset_id}/` | Drop rows or columns containing null values |
| 13 | `POST` | `/datalab/fill-nulls/{dataset_id}/` | Fill null values using a chosen imputation strategy |
| 14 | `GET` | `/datalab/detect-outliers/{dataset_id}/` | Detect outliers per column using IQR or Z-Score — read-only audit |
| 15 | `POST` | `/datalab/trim-outliers/{dataset_id}/` | Delete rows where any target column has an outlier value |
| 16 | `POST` | `/datalab/impute-outliers/{dataset_id}/` | Replace outlier values with column mean, median, or mode |
| 17 | `POST` | `/datalab/cap-outliers/{dataset_id}/` | Winsorize — cap values at lower/upper percentile bounds |
| 18 | `POST` | `/datalab/transform-column/{dataset_id}/` | Apply log, sqrt, or cbrt transformation to numeric columns |

---

### 1. Preview Dataset as Table

Returns a row-limited slice of the dataset rendered as rows and columns for display in a data table component.

- **Endpoint**: `GET /datalab/preview/{dataset_id}/`
- **Auth Required**: Yes
- **Query Params**:

| Param | Type | Default | Description |
|---|---|---|---|
| `limit` | int | `100` | Number of rows to return. `0` = all rows, capped at 10,000. Max positive value: `10,000`. |

Typical UI values: `100`, `200`, `500`, `0` (All).

- **Response (200 OK)**:
```json
{
  "dataset_id": 15,
  "file_name": "survey.csv",
  "file_format": "csv",
  "dataset_size": "1.0 MB",
  "total_rows": 1000,
  "total_columns": 3,
  "limit": 100,
  "truncated": false,
  "columns": ["Name", "Age", "Salary"],
  "rows": [
    { "Name": "Alice", "Age": 30, "Salary": 50000 },
    { "Name": "Bob", "Age": null, "Salary": 62000 }
  ]
}
```

- **Response (400)** — limit exceeds maximum:
```json
{ "detail": "'limit' cannot exceed 10000." }
```

- **Response (400)** — invalid limit:
```json
{ "detail": "'limit' must be a non-negative integer (0 = all rows, max 10000)." }
```

> `null` is used for missing values (`NaN`). The `columns` array preserves the original column order.
> `dataset_size` is a human-readable string (`B`, `KB`, `MB`, `GB`, `TB`).
> `total_rows` always reflects the full dataset regardless of `limit`.
> `truncated: true` means the dataset has more rows than what was returned — show a "Showing X of Y rows" indicator in the UI.
> `limit=0` returns up to 10,000 rows (capped). If `total_rows > 10,000` and `truncated: true`, the user is only seeing the first 10,000.

---

### 2. Inspect DataFrame Metadata

Returns structured per-column metadata: dtype, null counts, null percentage, and total memory usage.

- **Endpoint**: `GET /datalab/inspect/{dataset_id}/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "info": {
    "columns": [
      {
        "column": "user_id",
        "dtype": "int64",
        "non_null_count": 1000,
        "null_count": 0,
        "null_pct": 0.0,
        "unique_count": 1000,
        "is_unique": true
      },
      {
        "column": "Age",
        "dtype": "float64",
        "non_null_count": 988,
        "null_count": 12,
        "null_pct": 1.2,
        "unique_count": 72,
        "is_unique": false
      },
      {
        "column": "Salary",
        "dtype": "int64",
        "non_null_count": 1000,
        "null_count": 0,
        "null_pct": 0.0,
        "unique_count": 540,
        "is_unique": false
      }
    ],
    "memory_usage_bytes": 24128
  }
}
```

> `info.columns` is the structured per-column breakdown — use this to render the inspect table.
> `null_pct` is rounded to 1 decimal place (e.g. `1.2` means 1.2% of rows are null for that column).
> `unique_count` is the number of distinct non-null values in the column.
> `is_unique` is `true` when every **non-null** value in the column is distinct. Columns with nulls can still be `is_unique: true` — use it to identify ID/key columns (`user_id`, `transaction_id`, `product_id`, etc.).
> `memory_usage_bytes` is the total deep memory usage of the dataframe in bytes.

---

### 3. Describe Dataset (Summary Statistics)

Returns descriptive statistics for every column using pandas `df.describe(include='all')`. Numeric columns get distribution stats; categorical/string columns get frequency stats. `NaN` stats are omitted from the response.

- **Endpoint**: `GET /datalab/describe/{dataset_id}/`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "columns": {
    "Age": {
      "count": 988.0,
      "mean": 35.2,
      "std": 12.1,
      "min": 18.0,
      "25%": 25.0,
      "50%": 34.0,
      "75%": 45.0,
      "max": 72.0
    },
    "Salary": {
      "count": 1000.0,
      "mean": 58400.0,
      "std": 14200.0,
      "min": 22000.0,
      "25%": 48000.0,
      "50%": 56000.0,
      "75%": 68000.0,
      "max": 120000.0
    },
    "Country": {
      "count": 1000.0,
      "unique": 42.0,
      "top": "United States",
      "freq": 312.0
    }
  }
}
```

> **Numeric columns** — `count`, `mean`, `std`, `min`, `25%`, `50%`, `75%`, `max`.
> **Categorical / string columns** — `count`, `unique`, `top` (most frequent value), `freq` (how many times it appears).
> Stats that don't apply to a column type (e.g. `mean` on a string column) are omitted — not returned as `null`.
> `count` reflects non-null rows only — compare against `total_rows` from `inspect` to derive the null count.

---

### 4. Fill Derived Values

Fill null values in a target column by computing them from two other columns using arithmetic. Only fills rows where the target is null **and** both operand columns have non-null values (and a non-zero denominator for `divide`).

- **Endpoint**: `POST /datalab/fill-derived/{dataset_id}/`
- **Auth Required**: Yes

#### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `target` | string | Yes | Column whose nulls should be filled |
| `formula` | string | Yes | Arithmetic operation: `"divide"`, `"multiply"`, `"add"`, `"subtract"` |
| `operand_a` | string | Yes | Left-hand column in the formula |
| `operand_b` | string | Yes | Right-hand column in the formula |

The fill value is computed as: `target = operand_a <formula> operand_b`

**Fill missing `Unit_Price` from `Total_Price ÷ Quantity`:**
```json
{
  "target": "Unit_Price",
  "formula": "divide",
  "operand_a": "Total_Price",
  "operand_b": "Quantity"
}
```

**Fill missing `Quantity` from `Total_Price ÷ Unit_Price` (rounded to integer):**
```json
{
  "target": "Quantity",
  "formula": "divide",
  "operand_a": "Total_Price",
  "operand_b": "Unit_Price"
}
```

**Fill missing `Total_Price` from `Quantity × Unit_Price`:**
```json
{
  "target": "Total_Price",
  "formula": "multiply",
  "operand_a": "Quantity",
  "operand_b": "Unit_Price"
}
```

#### Responses

- **Response (200)** — nulls filled:
```json
{
  "target": "Unit_Price",
  "formula": "divide",
  "operand_a": "Total_Price",
  "operand_b": "Quantity",
  "cells_filled": 23
}
```

- **Response (200)** — nothing to fill (no file write occurs):
```json
{
  "target": "Unit_Price",
  "formula": "divide",
  "operand_a": "Total_Price",
  "operand_b": "Quantity",
  "cells_filled": 0,
  "detail": "No null values in 'Unit_Price' with complete operand data."
}
```

- **Response (400)** — missing fields:
```json
{ "detail": "'target', 'formula', 'operand_a', and 'operand_b' are all required." }
```
- **Response (400)** — invalid formula:
```json
{ "detail": "Invalid 'formula'. Choose one of: ['divide', 'multiply', 'add', 'subtract']" }
```
- **Response (400)** — non-numeric columns (target or operands):
```json
{ "detail": "All three columns must be numeric: ['Quantity']" }
```

> All three columns — `target`, `operand_a`, and `operand_b` — must be numeric.
> If `target` is an integer-typed column, derived values are automatically rounded and cast to `Int64`.
> Rows where `operand_b = 0` are skipped when `formula` is `"divide"` — they remain null.
> Run `fill_derived` **before** `fill_nulls` — this fills the recoverable nulls first; use `fill_nulls` for the rest.

---

### 5. Validate Formula

Check whether a column's values are mathematically consistent with a formula across two other columns. Read-only — does not modify the dataset. Use this after `fill_derived` to verify correctness, or as a data quality check on raw uploads.

- **Endpoint**: `POST /datalab/validate-formula/{dataset_id}/`
- **Auth Required**: Yes

#### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `result_column` | string | Yes | Column that should equal `operand_a <formula> operand_b` |
| `formula` | string | Yes | `"divide"`, `"multiply"`, `"add"`, `"subtract"` |
| `operand_a` | string | Yes | Left-hand operand column |
| `operand_b` | string | Yes | Right-hand operand column |
| `tolerance` | number | No | Acceptable absolute difference. Defaults to `0.01` (1 cent) |

**Check that `Total_Price ≈ Quantity × Unit_Price` within 1 cent:**
```json
{
  "result_column": "Total_Price",
  "formula": "multiply",
  "operand_a": "Quantity",
  "operand_b": "Unit_Price",
  "tolerance": 0.01
}
```

#### Responses

- **Response (200)** — validation complete:
```json
{
  "result_column": "Total_Price",
  "formula": "multiply",
  "operand_a": "Quantity",
  "operand_b": "Unit_Price",
  "tolerance": 0.01,
  "total_rows": 1000,
  "checked_rows": 950,
  "error_rows": 12,
  "error_pct": 1.3,
  "sample_errors": [
    {
      "row_index": 42,
      "Quantity": 3,
      "Unit_Price": 15.99,
      "Total_Price": 50.00,
      "calculated": 47.97,
      "diff": 2.03
    }
  ]
}
```

- **Response (200)** — no checkable rows (all null or zero denominator):
```json
{
  "result_column": "Total_Price",
  "formula": "multiply",
  "operand_a": "Quantity",
  "operand_b": "Unit_Price",
  "tolerance": 0.01,
  "total_rows": 1000,
  "checked_rows": 0,
  "error_rows": 0,
  "error_pct": 0.0,
  "sample_errors": []
}
```

> `checked_rows` — rows where all three columns are non-null (and denominator ≠ 0 for `divide`). Rows with any null are excluded from the check.
> `sample_errors` — up to 5 example rows where the difference exceeds tolerance. Use `row_index` to locate them in the preview table.
> `error_pct` — percentage of checked rows that failed. `0.0` means the dataset is fully consistent within tolerance.
> This endpoint never writes to disk — safe to call freely.

---

### 6. Fix Formula Inconsistencies

Overwrite values in a target column for rows where the math doesn't add up — replacing the wrong value with one recomputed from trusted operand columns. Unlike `fill-derived` which only fills nulls, this overwrites **existing non-null values** that are mathematically inconsistent.

Use this after `validate-formula` detects errors. The typical pattern is: **trust two columns, recompute the third.**

- **Endpoint**: `POST /datalab/fix-formula/{dataset_id}/`
- **Auth Required**: Yes

#### Request Body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `target` | string | Yes | — | Column whose wrong values should be overwritten |
| `formula` | string | Yes | — | `"divide"`, `"multiply"`, `"add"`, `"subtract"` |
| `operand_a` | string | Yes | — | Trusted left-hand column |
| `operand_b` | string | Yes | — | Trusted right-hand column |
| `tolerance` | number | No | `0.01` | Rows within this threshold are considered correct and left untouched |

The fix is applied as: `target = operand_a <formula> operand_b` — but **only for rows** where the current `target` value differs from the formula result by more than `tolerance`.

**Fix `Unit_Price` by trusting `Total_Price` and `Quantity`:**
```json
{
  "target": "Unit_Price",
  "formula": "divide",
  "operand_a": "Total_Price",
  "operand_b": "Quantity",
  "tolerance": 0.01
}
```

#### Responses

- **Response (200)** — inconsistencies fixed:
```json
{
  "target": "Unit_Price",
  "formula": "divide",
  "operand_a": "Total_Price",
  "operand_b": "Quantity",
  "tolerance": 0.01,
  "cells_fixed": 14
}
```

- **Response (200)** — no inconsistencies found (no file write occurs):
```json
{
  "target": "Unit_Price",
  "formula": "divide",
  "operand_a": "Total_Price",
  "operand_b": "Quantity",
  "tolerance": 0.01,
  "cells_fixed": 0,
  "detail": "No inconsistent rows found within the given tolerance."
}
```

- **Response (400)** — non-numeric columns:
```json
{ "detail": "All three columns must be numeric: ['Unit_Price']" }
```

> This only touches rows where all three columns are non-null and (for `divide`) `operand_b != 0`.
> Rows that are already consistent within `tolerance` are left unchanged.
> Integer-typed target columns are auto-rounded after recomputation.
> After fixing, run `validate-formula` again with the same params to confirm `error_rows === 0`.

---

### 7. Cast Column Dtypes

Cast one or more columns to a new dtype. The change is persisted back to the dataset file on disk. Use this after `inspect` reveals columns with wrong types (e.g. `Date` as `object` instead of `datetime64`).

- **Endpoint**: `POST /datalab/cast/{dataset_id}/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "casts": {
    "Date": "datetime",
    "Quantity": "integer",
    "Unit_Price": "float"
  }
}
```

**Supported target types:**

| Type | Pandas operation | Use when |
|---|---|---|
| `datetime` | `pd.to_datetime(errors='coerce')` | Column contains dates/timestamps stored as strings |
| `numeric` | `pd.to_numeric(errors='coerce')` | Column contains numbers stored as strings (keeps float) |
| `float` | `pd.to_numeric(errors='coerce')` | Same as numeric, explicit float output |
| `integer` | `pd.to_numeric(errors='coerce').astype('Int64')` | Whole numbers; supports nulls via nullable Int64 |
| `string` | `.astype(str)` | Force everything to string — ⚠️ null values become the literal string `"nan"` |
| `boolean` | `.astype(bool)` | Convert truthy/falsy values |
| `category` | `.astype('category')` | Low-cardinality string columns |

> Values that cannot be converted are coerced to `null` (NaT for datetime, NaN for numeric) rather than raising an error.

- **Response (200 OK)**:
```json
{
  "updated_columns": [
    { "column": "Date",       "from_dtype": "object", "to_dtype": "datetime64[ns]", "status": "ok" },
    { "column": "Quantity",   "from_dtype": "object", "to_dtype": "Int64",          "status": "ok" },
    { "column": "Unit_Price", "from_dtype": "object", "to_dtype": "float64",        "status": "ok" }
  ]
}
```

> If a column cast fails, `status` will be `"error: <reason>"` and `to_dtype` will be `null`. Other columns in the same request that succeeded are still saved.
> Casting to `"string"` when the column has null values returns a `"warning"` status — nulls become the literal string `"nan"`. Use `force: true` to proceed anyway.
> Successful casts are recorded in the activity log with `action: "CAST"` and `details: { columns: { col: type } }`.
> `dataset.file_size` is synced after every successful cast.

- **Response (400)** — unknown column:
```json
{ "detail": "Columns not found in dataset: ['BadCol']" }
```
- **Response (400)** — unsupported type:
```json
{ "detail": "Unsupported types: ['text']. Supported: ['boolean', 'category', 'datetime', 'float', 'integer', 'numeric', 'string']" }
```
---

### 8. Drop Duplicate Rows

Remove duplicate rows from the dataset and persist the result to disk. Choose a `mode` to control which rows are compared and which are kept.

- **Endpoint**: `POST /datalab/drop-duplicates/{dataset_id}/`
- **Auth Required**: Yes

#### Modes

| Mode | subset | keep | Behaviour |
|---|---|---|---|
| `"all_first"` | — | — | Compare all columns, keep first occurrence of each duplicate |
| `"all_last"` | — | — | Compare all columns, keep last occurrence of each duplicate |
| `"subset_keep"` | required | required | Compare only the listed columns, keep first or last match |
| `"drop_all"` | optional | — | Remove every copy of any duplicate row — no survivors |

#### Request Body

**Mode `all_first`** (default — can omit body entirely):
```json
{ "mode": "all_first" }
```

**Mode `all_last`**:
```json
{ "mode": "all_last" }
```

**Mode `subset_keep`** — dedupe by specific columns, keep first or last:
```json
{
  "mode": "subset_keep",
  "subset": ["transaction_id", "product_id"],
  "keep": "first"
}
```

**Mode `drop_all`** — remove every row that has any duplicate (optional subset):
```json
{
  "mode": "drop_all",
  "subset": ["email"]
}
```

#### Field Reference

| Field | Type | Required | Description |
|---|---|---|---|
| `mode` | `"all_first"` \| `"all_last"` \| `"subset_keep"` \| `"drop_all"` | No | Dedup strategy. Defaults to `"all_first"`. |
| `subset` | array of strings | Only for `subset_keep` | Columns to compare. Optional for `drop_all` (omit = all columns). |
| `keep` | `"first"` \| `"last"` | Only for `subset_keep` | Which occurrence to keep. Defaults to `"first"`. |

- **Response (200 OK)** — duplicates found and removed:
```json
{
  "mode": "subset_keep",
  "rows_before": 1000,
  "rows_after": 950,
  "rows_dropped": 50
}
```

- **Response (200 OK)** — no duplicates found (file unchanged):
```json
{
  "rows_before": 1000,
  "rows_after": 1000,
  "rows_dropped": 0,
  "detail": "No duplicate rows found."
}
```

- **Response (400)** — invalid mode:
```json
{ "detail": "Invalid 'mode'. Choose one of: ['all_first', 'all_last', 'subset_keep', 'drop_all']" }
```
- **Response (400)** — `subset_keep` missing `subset`:
```json
{ "detail": "'subset' is required for mode 'subset_keep'." }
```
- **Response (400)** — `subset_keep` invalid `keep`:
```json
{ "detail": "For mode 'subset_keep', 'keep' must be 'first' or 'last'." }
```
- **Response (400)** — unknown column in `subset`:
```json
{ "detail": "Columns not found in dataset: ['bad_col']" }
```
- **Response (400)** — `subset` not a list of strings:
```json
{ "detail": "'subset' must be a non-empty list of column names." }
```

> When duplicates are dropped, `dataset.file_size` is updated automatically to reflect the smaller file.
> The cached DataFrame is invalidated so the next preview/inspect call returns the cleaned data.

---

### 9. Rename Column Header

Rename a single column header and persist the change to disk. If the column had a stored dtype cast, the cast is automatically migrated to the new name.

- **Endpoint**: `POST /datalab/rename-column/{dataset_id}/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "old_name": "Unnamed: 0",
  "new_name": "product_id"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `old_name` | string | Yes | Current column name |
| `new_name` | string | Yes | Desired column name |

- **Response (200 OK)**:
```json
{
  "old_name": "Unnamed: 0",
  "new_name": "product_id",
  "columns": ["product_id", "name", "price", "quantity"]
}
```

> `columns` is the full updated column list in original order — use it to refresh the column headers in the UI.
> Rename is recorded in the activity log with `action: "RENAME_COLUMN"` and `details: { old_name, new_name }`.
> `dataset.file_size` is synced after every rename.

- **Response (400)** — column not found:
```json
{ "detail": "Column 'Unnamed: 0' not found in dataset." }
```
- **Response (400)** — name already taken:
```json
{ "detail": "Column 'product_id' already exists in dataset." }
```
- **Response (400)** — identical names:
```json
{ "detail": "New name is identical to the current name." }
```

---

### 10. Update Cell Value

Edit a single cell at a specific row and column. The value is coerced to match the column's existing dtype — if it can't be converted, a `400` is returned before anything is written to disk.

- **Endpoint**: `PATCH /datalab/update-cell/{dataset_id}/`
- **Auth Required**: Yes
- **Request Body**:
```json
{
  "row_index": 4,
  "column": "Quantity",
  "value": 99
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `row_index` | int | Yes | 0-based row position from the current preview |
| `column` | string | Yes | Column name to edit |
| `value` | any \| `null` | Yes | New cell value. Send `null` to set the cell to NaN |

**Dtype coercion rules:**

| Column dtype | Accepted values | Rejected example |
|---|---|---|
| `int64` / `Int64` | Whole numbers (`99`, `"99"`) | `"hello"` |
| `float64` | Decimal numbers (`3.14`, `"3.14"`) | `"hello"` |
| `bool` | `true`, `false`, `"true"`, `"false"`, `"1"`, `"0"` | `"yes"` |
| `datetime64` | ISO date strings (`"2024-01-15"`) | `"not-a-date"` |
| `object` / `string` / `category` | Anything — coerced to string | — |

- **Response (200 OK)**:
```json
{
  "row_index": 4,
  "column": "Quantity",
  "value": 99
}
```
> For datetime columns, `value` is returned as an ISO 8601 string (e.g. `"2024-01-15T00:00:00"`).
> For `null` input, `value` is returned as `null`.

- **Response (400)** — wrong dtype:
```json
{ "detail": "Cannot assign 'hello' to column 'Quantity' (dtype: int64)." }
```
- **Response (400)** — row out of range:
```json
{ "detail": "Row index 9999 is out of range (dataset has 1000 rows)." }
```
- **Response (400)** — column not found:
```json
{ "detail": "Column 'Quantity' not found in dataset." }
```

> Every successful cell edit is recorded in the activity log with `action: "UPDATE_CELL"` and `details: { row_index, column, value }`.
> `dataset.file_size` is synced after every successful cell edit.
> Always use `row_index` values from the **current** preview response — row positions shift after operations like drop_duplicates.

---

### 11. Replace Values

Replace specific sentinel or garbage values (e.g. `"N/A"`, `"-"`, `"?"`) with `null` (NaN) or any other value, across all columns or a targeted subset.

- **Endpoint**: `POST /datalab/replace-values/{dataset_id}/`
- **Auth Required**: Yes

#### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `replacements` | object | Yes | Map of `{ "old_value": new_value }`. Use `null` as the new value to convert to NaN. |
| `columns` | array of strings | No | Columns to apply replacements to. Omit to apply across all columns. |

**Replace common sentinel strings with NaN (all columns):**
```json
{
  "replacements": { "N/A": null, "-": null, "?": null, "none": null, "null": null }
}
```

**Replace a specific value in targeted columns only:**
```json
{
  "replacements": { "999": null, "0": null },
  "columns": ["age", "salary"]
}
```

**Replace one value with another (not NaN):**
```json
{
  "replacements": { "Yes": "true", "No": "false" },
  "columns": ["is_active"]
}
```

#### Responses

- **Response (200)** — replacements applied:
```json
{
  "replacements": { "N/A": null, "-": null },
  "columns_affected": ["name", "email", "country"],
  "cells_replaced": 47
}
```

- **Response (200)** — no matches found (no file write occurs):
```json
{
  "replacements": { "N/A": null },
  "columns_affected": ["name", "email"],
  "cells_replaced": 0,
  "detail": "No matching values found."
}
```

- **Response (400)** — missing or invalid `replacements`:
```json
{ "detail": "'replacements' must be an object mapping old values to new values." }
```

- **Response (400)** — column not found:
```json
{ "detail": "Columns not found in dataset: ['unknown_col']" }
```

> Run `replace_values` **before** `fill_nulls` or `drop_nulls` — real-world CSVs often contain
> string sentinels (`"N/A"`, `"-"`) that pandas does not recognise as NaN, causing fill/drop
> operations to silently miss them.
> When replacements are applied, `dataset.file_size` is updated automatically to reflect the new file.

---

### 12. Drop Nulls

Drop rows or entire columns that contain null values. Covers two axes in one endpoint.

- **Endpoint**: `POST /datalab/drop-nulls/{dataset_id}/`
- **Auth Required**: Yes

#### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `axis` | string | No | `"rows"` (default) or `"columns"` |
| `how` | string | No | Rows only — `"any"` (default) or `"all"` |
| `subset` | array of strings | No | Rows only — check nulls only in these columns |
| `thresh_pct` | number (0–100) | Columns only | Drop columns whose null % exceeds this threshold |

**Drop rows where ANY column is null:**
```json
{ "axis": "rows", "how": "any" }
```

**Drop rows where ALL columns are null:**
```json
{ "axis": "rows", "how": "all" }
```

**Drop rows where a key column is null:**
```json
{ "axis": "rows", "how": "any", "subset": ["user_id", "transaction_date"] }
```

**Drop columns with more than 70% null values:**
```json
{ "axis": "columns", "thresh_pct": 70 }
```

#### Responses

- **Response (200)** — rows dropped:
```json
{
  "axis": "rows",
  "rows_before": 1000,
  "rows_after": 943,
  "rows_dropped": 57
}
```

- **Response (200)** — columns dropped:
```json
{
  "axis": "columns",
  "columns_before": 12,
  "columns_after": 9,
  "columns_dropped": ["notes", "legacy_id", "deprecated_field"]
}
```

- **Response (200)** — nothing matched (no file write occurs):
```json
{
  "axis": "rows",
  "rows_before": 1000,
  "rows_after": 1000,
  "rows_dropped": 0,
  "detail": "No null rows/columns matched the criteria."
}
```

- **Response (400)** — missing `thresh_pct` for column axis:
```json
{ "detail": "'thresh_pct' is required when axis is 'columns'." }
```

- **Response (400)** — invalid `how`:
```json
{ "detail": "'how' must be 'any' or 'all'." }
```

> When dropping columns, `column_casts` entries for removed columns are not automatically
> cleaned up — they are silently ignored on next load since `apply_stored_casts` skips missing columns.
> Re-fetch `inspect` after this operation as column count will have changed.

---

### 13. Fill Nulls

Fill missing (NaN) values using a chosen imputation strategy. Apply to all columns or a targeted subset.

- **Endpoint**: `POST /datalab/fill-nulls/{dataset_id}/`
- **Auth Required**: Yes

#### Strategies

| Strategy | Description | Applies to |
|---|---|---|
| `constant` | Fill with a literal value (requires `value` field) | Any dtype |
| `mean` | Fill with column mean | Numeric only |
| `median` | Fill with column median (robust to outliers) | Numeric only |
| `mode` | Fill with most frequent value | Any dtype |
| `ffill` | Forward fill — use the previous row's value | Any dtype |
| `bfill` | Backward fill — use the next row's value | Any dtype |

#### Request Body

| Field | Type | Required | Description |
|---|---|---|---|
| `strategy` | string | Yes | One of the strategies above |
| `value` | any | When `strategy` is `"constant"` | The literal fill value |
| `columns` | array of strings | No | Columns to fill. Omit to apply to all columns. |

**Fill all nulls with median (numeric columns only):**
```json
{ "strategy": "median" }
```

**Fill a categorical column with a constant:**
```json
{
  "strategy": "constant",
  "value": "Unknown",
  "columns": ["country", "status"]
}
```

**Forward-fill a time-series column:**
```json
{
  "strategy": "ffill",
  "columns": ["daily_price"]
}
```

**Fill numeric nulls with mean across specific columns:**
```json
{
  "strategy": "mean",
  "columns": ["age", "salary", "score"]
}
```

#### Responses

- **Response (200)** — nulls filled:
```json
{
  "strategy": "median",
  "cells_filled": 143,
  "skipped_columns": ["name", "country"]
}
```
> `skipped_columns` — columns that were skipped because the strategy is incompatible with their dtype
> (e.g. `mean`/`median` on a string column). No error is raised — they are silently skipped and reported here.

- **Response (200)** — nothing to fill (no file write occurs):
```json
{
  "strategy": "mean",
  "cells_filled": 0,
  "skipped_columns": [],
  "detail": "No null values found to fill."
}
```

- **Response (400)** — invalid strategy:
```json
{ "detail": "'strategy' must be one of: ['bfill', 'constant', 'ffill', 'mean', 'median', 'mode']" }
```

- **Response (400)** — missing `value` for constant strategy:
```json
{ "detail": "'value' is required when strategy is 'constant'." }
```

> Recommended order: `replace_values` → `drop_nulls` → `fill_nulls`.
> Run `replace_values` first so sentinel strings (`"N/A"`, `"-"`) become real NaN before fill strategies are applied.
> When nulls are filled, `dataset.file_size` is updated automatically to reflect the new file.

---

### 14. Detect Outliers

Scan one or more numeric columns for outliers using IQR or Z-Score and return per-column stats with sample rows. **Read-only — does not modify the dataset.**

- **Endpoint**: `GET /datalab/detect-outliers/{dataset_id}/`
- **Auth Required**: Yes

#### Query Parameters

| Param | Type | Default | Description |
|---|---|---|---|
| `columns` | string | — | **Required.** Comma-separated list of numeric column names to inspect |
| `method` | string | `"iqr"` | Detection method: `"iqr"` or `"zscore"` |
| `threshold` | number | `1.5` (IQR) / `3.0` (Z-Score) | Sensitivity. Lower = more outliers flagged |

**Method reference:**

| Method | How it works | Threshold meaning |
|---|---|---|
| `iqr` | Outlier if value < Q1 − t×IQR or > Q3 + t×IQR | Multiplier on IQR. `1.5` = standard; `3.0` = only extreme outliers |
| `zscore` | Outlier if \|z-score\| > threshold | Standard deviations from mean. `3.0` = standard; `2.0` = stricter |

**Detect outliers in `unit_price` and `quantity` using IQR:**
```
GET /datalab/detect-outliers/15/?columns=unit_price,quantity&method=iqr&threshold=1.5
```

**Detect using Z-Score with strict threshold:**
```
GET /datalab/detect-outliers/15/?columns=salary&method=zscore&threshold=2.5
```

#### Response (200 OK)
```json
{
  "dataset_id": 15,
  "method": "iqr",
  "threshold": 1.5,
  "columns": {
    "unit_price": {
      "outlier_count": 8,
      "outlier_pct": 0.8,
      "lower_bound": 2.125,
      "upper_bound": 49.875,
      "min": -5.0,
      "max": 210.0,
      "mean": 24.3,
      "median": 22.5,
      "sample_outliers": [
        { "row_index": 12, "unit_price": -5.0 },
        { "row_index": 47, "unit_price": 210.0 }
      ]
    },
    "quantity": {
      "outlier_count": 3,
      "outlier_pct": 0.3,
      "lower_bound": 0.0,
      "upper_bound": 18.0,
      "min": 1,
      "max": 500,
      "mean": 8.7,
      "median": 7.0,
      "sample_outliers": [
        { "row_index": 201, "quantity": 500 }
      ]
    }
  }
}
```

- **Response (400)** — missing columns:
```json
{ "detail": "'columns' is required." }
```
- **Response (400)** — non-numeric column:
```json
{ "detail": "Outlier operations require numeric columns: ['product_name']" }
```
- **Response (400)** — invalid method:
```json
{ "detail": "'method' must be one of: ['iqr', 'zscore']" }
```

> `lower_bound` / `upper_bound` — the computed fence values. Values outside this range are flagged as outliers.
> `sample_outliers` — up to 5 example rows. Use `row_index` to locate them in the preview table.
> This endpoint is safe to call freely — it never writes to disk.

---

### 15. Trim Outliers (Deletion)

Delete rows where any of the target columns contains an outlier. Use this when you are certain the values are measurement errors and the affected rows are a small fraction of your data.

- **Endpoint**: `POST /datalab/trim-outliers/{dataset_id}/`
- **Auth Required**: Yes

#### Request Body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `columns` | array of strings | Yes | — | Numeric columns to check for outliers |
| `method` | string | No | `"iqr"` | `"iqr"` or `"zscore"` |
| `threshold` | number | No | `1.5` | Detection sensitivity (see Detect Outliers) |

```json
{
  "columns": ["unit_price", "quantity"],
  "method": "iqr",
  "threshold": 1.5
}
```

#### Responses

- **Response (200)** — rows deleted:
```json
{
  "columns": ["unit_price", "quantity"],
  "method": "iqr",
  "threshold": 1.5,
  "rows_before": 1000,
  "rows_after": 991,
  "rows_dropped": 9
}
```

- **Response (200)** — no outliers found (no file write occurs):
```json
{
  "columns": ["unit_price"],
  "method": "iqr",
  "threshold": 1.5,
  "rows_before": 1000,
  "rows_after": 1000,
  "rows_dropped": 0,
  "detail": "No outlier rows found."
}
```

> A row is dropped if **any** of the listed columns is an outlier for that row.
> Run `detect-outliers` first to preview how many rows will be removed before committing.
> Risk: information is permanently lost if the outlier was a real, rare event — use `impute-outliers` or `cap-outliers` instead when in doubt.

---

### 16. Impute Outliers (Replacement)

Replace outlier values in-place with the column's mean, median, or mode. The row is kept — only the offending value is replaced. Use this when you want to preserve the row but the specific value is clearly wrong.

- **Endpoint**: `POST /datalab/impute-outliers/{dataset_id}/`
- **Auth Required**: Yes

#### Request Body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `columns` | array of strings | Yes | — | Numeric columns to impute |
| `method` | string | No | `"iqr"` | `"iqr"` or `"zscore"` |
| `threshold` | number | No | `1.5` | Detection sensitivity |
| `strategy` | string | No | `"median"` | Replacement value: `"mean"`, `"median"`, or `"mode"` |

**Replace negative prices with the column median:**
```json
{
  "columns": ["unit_price"],
  "method": "iqr",
  "threshold": 1.5,
  "strategy": "median"
}
```

**Replace extreme salary values with the mean:**
```json
{
  "columns": ["salary"],
  "method": "zscore",
  "threshold": 3.0,
  "strategy": "mean"
}
```

#### Responses

- **Response (200)** — outliers replaced:
```json
{
  "columns": ["unit_price"],
  "method": "iqr",
  "threshold": 1.5,
  "strategy": "median",
  "cells_imputed": 8
}
```

- **Response (200)** — no outliers found (no file write occurs):
```json
{
  "columns": ["unit_price"],
  "method": "iqr",
  "threshold": 1.5,
  "strategy": "median",
  "cells_imputed": 0,
  "detail": "No outliers found."
}
```

- **Response (400)** — invalid strategy:
```json
{ "detail": "'strategy' must be one of: ['mean', 'median', 'mode']" }
```

> `median` is the recommended default — it is robust to the very outliers being replaced, unlike `mean` which can itself be pulled by extreme values.
> Integer-typed columns are auto-rounded after imputation.
> The replacement value is computed from all non-null values in the column, including non-outlier rows.

---

### 17. Cap Outliers / Winsorization

Instead of deleting or replacing, cap extreme values at a chosen percentile boundary. Values below the lower percentile are set to that percentile's value; values above the upper percentile are set to the upper percentile's value. This keeps the data distribution meaningful without letting extremes distort aggregates.

- **Endpoint**: `POST /datalab/cap-outliers/{dataset_id}/`
- **Auth Required**: Yes

#### Request Body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `columns` | array of strings | Yes | — | Numeric columns to winsorize |
| `lower_pct` | number (0–100) | No | `5.0` | Lower percentile floor (e.g. `5` = 5th percentile) |
| `upper_pct` | number (0–100) | No | `95.0` | Upper percentile ceiling (e.g. `95` = 95th percentile) |

**Cap at 5th / 95th percentile (standard winsorization):**
```json
{
  "columns": ["unit_price", "salary"],
  "lower_pct": 5,
  "upper_pct": 95
}
```

**Tighter cap — only the top and bottom 1%:**
```json
{
  "columns": ["transaction_amount"],
  "lower_pct": 1,
  "upper_pct": 99
}
```

#### Responses

- **Response (200)** — values capped:
```json
{
  "columns": ["unit_price", "salary"],
  "lower_pct": 5.0,
  "upper_pct": 95.0,
  "cells_capped": 42
}
```

- **Response (200)** — all values already within bounds (no file write occurs):
```json
{
  "columns": ["unit_price"],
  "lower_pct": 5.0,
  "upper_pct": 95.0,
  "cells_capped": 0,
  "detail": "No values outside the percentile bounds."
}
```

- **Response (400)** — invalid percentile range:
```json
{ "detail": "'lower_pct' and 'upper_pct' must be numbers where 0 <= lower_pct < upper_pct <= 100." }
```

> Unlike trimming, no rows are deleted — the shape of the dataset is preserved.
> `cells_capped` is the total count across all columns — values that were already exactly at the boundary are not counted.
> After capping, run `describe` to confirm the new min/max values look correct.

---

### 18. Transform Column

Apply a mathematical transformation to one or more numeric columns. Useful for right-skewed data (many small values, a few very large ones) — a log transform pulls the distribution closer to normal and reduces the influence of extreme values.

- **Endpoint**: `POST /datalab/transform-column/{dataset_id}/`
- **Auth Required**: Yes

#### Request Body

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `columns` | array of strings | Yes | — | Numeric columns to transform |
| `function` | string | No | `"log"` | Transformation to apply: `"log"`, `"sqrt"`, or `"cbrt"` |

**Function reference:**

| Function | Formula | Requirement | Use when |
|---|---|---|---|
| `log` | `ln(x)` | All values must be **> 0** | Right-skewed data (sales, income, counts) |
| `sqrt` | `√x` | All values must be **≥ 0** | Moderate skew; count data |
| `cbrt` | `∛x` | No restriction — works with negatives | When `log` / `sqrt` won't apply due to zeros or negatives |

**Log-transform sales and revenue (right-skewed):**
```json
{
  "columns": ["sales_amount", "revenue"],
  "function": "log"
}
```

**Square-root transform count columns:**
```json
{
  "columns": ["page_views", "click_count"],
  "function": "sqrt"
}
```

#### Responses

- **Response (200)** — columns transformed:
```json
{
  "function": "log",
  "transformed_columns": ["sales_amount", "revenue"],
  "skipped_columns": []
}
```

- **Response (200)** — some columns skipped due to invalid values:
```json
{
  "function": "log",
  "transformed_columns": ["revenue"],
  "skipped_columns": [
    { "column": "sales_amount", "reason": "log requires all values > 0" }
  ]
}
```

- **Response (200)** — all columns skipped (no file write occurs):
```json
{
  "function": "log",
  "transformed_columns": [],
  "skipped_columns": [
    { "column": "sales_amount", "reason": "log requires all values > 0" }
  ],
  "detail": "No columns were transformed."
}
```

- **Response (400)** — invalid function:
```json
{ "detail": "'function' must be one of: ['log', 'sqrt', 'cbrt']" }
```

> Transformation is applied to the entire column including non-outlier values — this is a column-wide reshape, not an outlier fix.
> Columns with any value that violates the function's constraint are skipped entirely (not partially transformed) and reported in `skipped_columns`.
> After transforming, run `describe` to verify the new distribution looks as expected.
> **This operation is irreversible** — duplicate the dataset first if you need to compare before/after.

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
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Validation error or missing fields |
| 401 | Unauthorized | Invalid or expired token |
| 403 | Forbidden | Permissions mapping error |
| 404 | Not Found | Resource not found |
---
