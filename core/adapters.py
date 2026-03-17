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
            extra_data = sociallogin.account.extra_data
            self._extract_google_names(user, extra_data)
            self._extract_google_picture(user, extra_data)
            self._verify_google_email(user, extra_data)

            if not user.username:
                user.username = self._generate_unique_username(user.email)

        return user

    def _extract_google_names(self, user, extra_data):
        user.first_name = extra_data.get("given_name", "") or extra_data.get(
            "first_name", ""
        )
        user.last_name = extra_data.get("family_name", "") or extra_data.get(
            "last_name", ""
        )
        full_name = extra_data.get("name", "")
        if not full_name and user.first_name and user.last_name:
            full_name = f"{user.first_name} {user.last_name}"
        user.full_name = full_name

    def _extract_google_picture(self, user, extra_data):
        picture_url = extra_data.get("picture", "")
        if picture_url:
            if picture_url.startswith("http://"):
                picture_url = picture_url.replace("http://", "https://")
            user.profile_picture = picture_url

    def _verify_google_email(self, user, extra_data):
        if extra_data.get("verified_email", False) or extra_data.get(
            "email_verified", False
        ):
            user.email_verified = True

    def _generate_unique_username(self, email):
        from core.models import AuthUser

        email_prefix = email.split("@")[0]
        username = email_prefix
        counter = 1
        while AuthUser.objects.filter(username=username).exists():
            username = f"{email_prefix}{counter}"
            counter += 1
        return username

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

        # Keep username internal: generate from email when not provided.
        if not user.username and user.email:
            user.username = self._generate_unique_username(user.email)

        if commit:
            user.save()

        return user

    def _generate_unique_username(self, email):
        from core.models import AuthUser

        email_prefix = email.split("@")[0]
        username = email_prefix
        counter = 1
        while AuthUser.objects.filter(username=username).exists():
            username = f"{email_prefix}{counter}"
            counter += 1
        return username
