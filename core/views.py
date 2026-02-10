"""
Core API Views

Authentication is handled by dj-rest-auth.
Add your custom views here as needed.
"""

from rest_framework import generics, permissions


# Add your custom views here
# Example:
#
# class UserListView(generics.ListAPIView):
#     """List all users (admin only)"""
#     queryset = AuthUser.objects.all()
#     serializer_class = UserSerializer
#     permission_classes = [permissions.IsAdminUser]
