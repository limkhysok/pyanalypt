"""
Custom adapter for django-allauth to handle Google OAuth signin
and populate AuthUser model fields with Google metadata
"""

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom Social Account Adapter to populate AuthUser fields
    from Google OAuth metadata automatically.
    """

    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed.

        This is where we connect existing users if their email matches.
        """
        # If user is already logged in, don't do anything
        if sociallogin.is_existing:
            return

        # Try to connect to existing user by email
        if sociallogin.account.provider == "google":
            try:
                email = sociallogin.account.extra_data.get("email")
                if email:
                    from core.models import AuthUser

                    try:
                        user = AuthUser.objects.get(email=email)
                        # Connect this social account to the existing user
                        sociallogin.connect(request, user)
                    except AuthUser.DoesNotExist:
                        # User doesn't exist, will be created in populate_user
                        pass
            except Exception:
                # Silently fail if there's any issue with email matching
                pass

    def populate_user(self, request, sociallogin, data):
        """
        Populate user information from social provider data (Google).
        This is called when creating a NEW user via social login.
        """
        user = super().populate_user(request, sociallogin, data)

        if sociallogin.account.provider == "google":
            # Extract data from Google OAuth response
            extra_data = sociallogin.account.extra_data

            # Populate name fields
            user.first_name = extra_data.get("given_name", "") or extra_data.get(
                "first_name", ""
            )
            user.last_name = extra_data.get("family_name", "") or extra_data.get(
                "last_name", ""
            )

            # Generate full_name from first + last name
            full_name = extra_data.get("name", "")
            if not full_name and user.first_name and user.last_name:
                full_name = f"{user.first_name} {user.last_name}"
            user.full_name = full_name

            # Set profile picture from Google
            picture_url = extra_data.get("picture", "")
            if picture_url:
                # Ensure it's HTTPS
                if picture_url.startswith("http://"):
                    picture_url = picture_url.replace("http://", "https://")
                user.profile_picture = picture_url

            # Mark email as verified (Google pre-verifies emails)
            if extra_data.get("verified_email", False) or extra_data.get(
                "email_verified", False
            ):
                user.email_verified = True

            # Generate username from email if not provided
            if not user.username:
                # Use email prefix as username
                email_prefix = user.email.split("@")[0]
                # Make it unique by appending random string if needed
                username = email_prefix
                from core.models import AuthUser

                counter = 1
                while AuthUser.objects.filter(username=username).exists():
                    username = f"{email_prefix}{counter}"
                    counter += 1
                user.username = username

        return user

    def save_user(self, request, sociallogin, form=None):
        """
        Save a newly created user via social login.
        """
        user = super().save_user(request, sociallogin, form)

        # Additional processing after user is saved
        if sociallogin.account.provider == "google":
            # Mark email as verified in account_emailaddress table
            from allauth.account.models import EmailAddress

            EmailAddress.objects.filter(user=user, email=user.email).update(
                verified=True
            )

        return user


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom Account Adapter for regular (non-social) signups.
    """

    def save_user(self, request, user, form, commit=True):
        """
        Save user from signup form.
        """
        user = super().save_user(request, user, form, commit=False)

        # Auto-generate full_name if not provided
        if not user.full_name and user.first_name and user.last_name:
            user.full_name = f"{user.first_name} {user.last_name}"

        # Ensure email is lowercase
        if user.email:
            user.email = user.email.lower()

        if commit:
            user.save()

        return user
