"""
Core API Views

Note: Authentication views are now handled by dj-rest-auth.
The custom RegisterView and UserDetailView below are kept for reference
but are no longer used (commented out).

dj-rest-auth provides:
- POST   /api/v1/auth/registration/  → User registration
- GET    /api/v1/auth/user/          → Current user details
- PUT    /api/v1/auth/user/          → Update user
- PATCH  /api/v1/auth/user/          → Partial update user

If you need custom user endpoints in the future, you can uncomment and modify these.
"""

from rest_framework import generics, permissions
from .serializers import RegisterSerializer, UserSerializer


# ===== DEPRECATED VIEWS (Replaced by dj-rest-auth) =====
#
# These views are no longer used since we're using dj-rest-auth for authentication.
# Kept here for reference in case you need custom user management endpoints later.

# class RegisterView(generics.CreateAPIView):
#     """
#     DEPRECATED: Use dj-rest-auth registration endpoint instead
#     POST /api/v1/auth/registration/
#     """
#     serializer_class = RegisterSerializer
#     permission_classes = [permissions.AllowAny]


# class UserDetailView(generics.RetrieveAPIView):
#     """
#     DEPRECATED: Use dj-rest-auth user endpoint instead
#     GET /api/v1/auth/user/
#     """
#     serializer_class = UserSerializer
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get_object(self):
#         return self.request.user


# ===== ADD YOUR CUSTOM VIEWS HERE =====
#
# Example: Custom user list view (for admins)
# class UserListView(generics.ListAPIView):
#     """
#     GET /api/v1/users/
#     List all users (admin only)
#     """
#     queryset = AuthUser.objects.all()
#     serializer_class = UserSerializer
#     permission_classes = [permissions.IsAdminUser]
#
# Example: Custom user profile view
# class UserProfileView(generics.RetrieveUpdateAPIView):
#     """
#     GET/PUT/PATCH /api/v1/users/me/
#     Get or update current user profile
#     """
#     serializer_class = UserSerializer
#     permission_classes = [permissions.IsAuthenticated]
#
#     def get_object(self):
#         return self.request.user
