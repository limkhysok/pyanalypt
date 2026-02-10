"""
Core API URLs - RESTful Structure

Following REST best practices:
- Resource-based URLs (nouns, not verbs)
- HTTP methods define actions
- Proper nesting and hierarchy
- Clear naming conventions

Available Endpoints:
- POST   /api/v1/auth/registration/       → Register new user
- POST   /api/v1/auth/login/              → Login with email/password
- POST   /api/v1/auth/logout/             → Logout
- GET    /api/v1/auth/user/               → Get current user
- PUT    /api/v1/auth/user/               → Update current user (full)
- PATCH  /api/v1/auth/user/               → Update current user (partial)
- POST   /api/v1/auth/password/reset/     → Request password reset
- POST   /api/v1/auth/token/              → Obtain JWT token
- POST   /api/v1/auth/token/refresh/      → Refresh JWT token
- POST   /api/v1/auth/token/verify/       → Verify JWT token
"""

from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    # ===== AUTHENTICATION RESOURCES =====
    # User Authentication & Management (dj-rest-auth - already RESTful)
    # Provides: login, logout, user (GET/PUT/PATCH), password reset, etc.
    path("auth/", include("dj_rest_auth.urls")),
    # User Registration (dj-rest-auth registration)
    # Provides: registration, email verification
    path("auth/registration/", include("dj_rest_auth.registration.urls")),
    # JWT Token Management (djangorestframework-simplejwt)
    path("auth/token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token-verify"),
    # ===== FUTURE RESOURCES =====
    # Add your app resources here following the same RESTful pattern:
    #
    # Example: User management (if you want custom endpoints beyond dj-rest-auth)
    # path("users/", include([
    #     path("", UserListView.as_view(), name="user-list"),              # GET: List users
    #     path("me/", UserMeView.as_view(), name="user-me"),               # GET/PUT/PATCH/DELETE: Current user
    #     path("<int:pk>/", UserDetailView.as_view(), name="user-detail"), # GET/PUT/PATCH/DELETE: Specific user
    # ])),
    #
    # Example: Projects
    # path("projects/", include("projects.urls")),
    #
    # Example: Analytics
    # path("analytics/", include("analytics.urls")),
]


# ===== RESTful API DESIGN PATTERNS =====
#
# Good Examples (Resource-based):
# ✅ GET    /api/v1/users/              → List all users
# ✅ POST   /api/v1/users/              → Create new user
# ✅ GET    /api/v1/users/me/           → Get current user profile
# ✅ PUT    /api/v1/users/me/           → Update current user (full update)
# ✅ PATCH  /api/v1/users/me/           → Update current user (partial)
# ✅ DELETE /api/v1/users/me/           → Delete current user account
# ✅ GET    /api/v1/users/{id}/         → Get specific user by ID
# ✅ POST   /api/v1/auth/token/         → Obtain JWT token (login)
# ✅ POST   /api/v1/auth/token/refresh/ → Refresh JWT token
# ✅ GET    /api/v1/projects/           → List all projects
# ✅ POST   /api/v1/projects/           → Create new project
# ✅ GET    /api/v1/projects/{id}/      → Get specific project
# ✅ GET    /api/v1/projects/{id}/analytics/ → Get project analytics
#
# Bad Examples (Action-based - avoid these):
# ❌ /api/register/                    → Use POST /api/v1/users/ instead
# ❌ /api/login/                       → Use POST /api/v1/auth/token/ instead
# ❌ /api/getUserById/{id}/            → Use GET /api/v1/users/{id}/ instead
# ❌ /api/deleteUser/{id}/             → Use DELETE /api/v1/users/{id}/ instead
# ❌ /api/updateProfile/               → Use PUT/PATCH /api/v1/users/me/ instead
# ❌ /api/createProject/               → Use POST /api/v1/projects/ instead
#
# REST Principles:
# 1. URLs represent RESOURCES (nouns), not ACTIONS (verbs)
# 2. HTTP METHODS represent actions:
#    - GET    → Retrieve resource(s)
#    - POST   → Create new resource
#    - PUT    → Full update of resource
#    - PATCH  → Partial update of resource
#    - DELETE → Delete resource
# 3. Use plural nouns for collections: /users/, /projects/
# 4. Use nesting for relationships: /projects/{id}/members/
# 5. Version your API: /api/v1/, /api/v2/
# 6. Use query parameters for filtering: /users/?is_active=true&role=admin
# 7. Use consistent naming convention (snake_case or kebab-case)
