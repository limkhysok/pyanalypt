# Frontend Sync — API Breaking Changes

This document describes every backend change that requires a frontend update.
Read it top to bottom and work through each section before shipping.

---

## 1. Change Password — `POST /auth/password/change/`

### What changed
- `old_password` is now **required**. The request will return `400` if it is missing.
- All other active sessions (other devices) are **revoked automatically** on success.
- Rate limited to **5 requests/hour** per user.

### What you must update

**Form field**
Add an `old_password` / "Current password" input field above the new-password fields. Submit it together:

```json
{
  "old_password": "CurrentPass123!",
  "new_password1": "NewSecurePass456!",
  "new_password2": "NewSecurePass456!"
}
```

**Error handling**
Handle the new `400` shape when the current password is wrong:

```json
{
  "old_password": ["Your old password was entered incorrectly. Please enter it again."]
}
```
Display this error inline under the "Current password" field.

**Post-success UX**
After a `200 OK`, show a confirmation message that explains other devices have been signed out — e.g. *"Password updated. All other devices have been signed out."* The current session stays active, so do **not** clear tokens or redirect to login.

**Rate limit**
On `429 Too Many Requests`, show: *"Too many attempts. Please try again later."*

---

## 2. Session List — `GET /auth/sessions/`

### What changed
Each session object now includes an `is_current` boolean field:

```json
{
  "id": 3,
  "device": "Desktop",
  "browser": "Chrome on Windows",
  "ip_address": "192.168.1.10",
  "created_at": "2026-04-14T08:00:00Z",
  "last_active": "2026-04-14T09:30:00Z",
  "is_current": true
}
```

### What you must update

**Remove the UA/IP heuristic**
Any existing logic that tries to identify the current session by matching `browser`, `ip_address`, or `last_active` should be deleted and replaced with a direct check on `is_current`.

**Highlight the current session**
Use `is_current === true` to visually distinguish the active session (e.g. a badge, bold label, or "This device" annotation).

**Protect it from accidental revocation**
When rendering the revoke button per session, disable or hide it for the session where `is_current === true`. Do not allow users to revoke their own current session from this list — they can use logout for that.

**"Sign out all other devices" flow**
If you have this button, call `DELETE /auth/sessions/{id}/` for every session where `is_current === false`, rather than calling `POST /auth/sessions/revoke-all/` (which also kills the current session and forces a redirect to login).

---

## 3. Complete Profile — `POST /auth/registration/complete-profile/`

### What changed
This endpoint now returns `400` if the user's profile is already complete. It is a one-time call.

```json
{
  "detail": "Profile has already been completed."
}
```

### What you must update

**Guard the route**
Before rendering the complete-profile page or calling this endpoint, check `user.full_name && user.birthday`. If both are set, redirect to `/dashboard` immediately — do not show the form.

**Handle the 400 gracefully**
If somehow the endpoint is called twice (e.g. a double-submit), catch the `400` and redirect to `/dashboard` rather than showing an error screen.

---

## 4. Update Profile — `PATCH /auth/user/`

### What changed
The endpoint now accepts edits to all four profile fields: `username`, `full_name`, `birthday`, and `profile_picture`. Previously only `full_name` was writable. `email` remains permanently read-only.

### What you must update

**Show all four fields as editable inputs** on the profile edit screen.

**Client-side validation to add before submitting:**

| Field | Rule |
|---|---|
| `username` | 3–150 chars; only letters, numbers, `.` `_` `-` |
| `full_name` | 2–255 chars; only letters, hyphens, apostrophes, spaces |
| `birthday` | Must be in the past; no more than 120 years ago |
| `profile_picture` | Must start with `https://`; allow empty/null to clear |

**Handle per-field errors from `400` responses:**
```json
{ "username": ["This username is already taken."] }
{ "birthday": ["Birthday must be in the past."] }
{ "profile_picture": ["Profile picture URL must use HTTPS protocol for security."] }
```
Display each error inline under its respective field.

**Profile picture UX:** Allow the user to paste an HTTPS URL or clear the current picture by sending `null`.

---

## 5. 2FA Endpoints — Rate Limits

The following endpoints are now rate-limited. None of them were previously throttled.

| Endpoint | Limit | Scope |
|---|---|---|
| `GET /auth/2fa/setup/` | 20/hour | Per authenticated user |
| `POST /auth/2fa/enable/` | 20/hour | Per authenticated user |
| `POST /auth/2fa/disable/` | 20/hour | Per authenticated user |
| `POST /auth/2fa/verify-login/` | 10/hour | Per IP address |

### What you must update

Add `429 Too Many Requests` handling to all four of these endpoints if it is not already in place. A single shared error handler is sufficient:

```
"Too many attempts. Please try again later."
```

For `POST /auth/2fa/verify-login/` specifically, the 10/hour limit is per IP — important for users behind shared networks. If a user hits this limit during the 5-minute 2FA window, they must restart the login flow (go back to `POST /auth/login/`). Make sure the expiry error and the rate-limit error lead to the same outcome: redirect back to the login screen.

---

## Summary Checklist

- [ ] Add `old_password` field to the change-password form
- [ ] Handle `400 { old_password: [...] }` inline error on that field
- [ ] Show post-password-change confirmation that other devices were signed out
- [ ] Handle `429` on `POST /auth/password/change/`
- [ ] Replace session current-detection heuristic with `is_current` flag
- [ ] Disable/hide the revoke button on the session where `is_current === true`
- [ ] Update "sign out all other devices" to use per-session DELETE, not revoke-all
- [ ] Guard the complete-profile route — redirect if profile is already set
- [ ] Handle `400` on `POST /auth/registration/complete-profile/` gracefully
- [ ] Make all four fields editable on the profile edit screen: `username`, `full_name`, `birthday`, `profile_picture`
- [ ] Add client-side validation for each field (see Section 4 rules)
- [ ] Handle per-field `400` errors inline
- [ ] Handle `429` on all four 2FA endpoints
