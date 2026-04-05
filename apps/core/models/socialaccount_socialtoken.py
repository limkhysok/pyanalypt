from allauth.socialaccount.models import SocialToken as BaseSocialToken


# REFERENCE ONLY - Matches socialaccount_socialtoken table
class SocialToken(BaseSocialToken):
    class Meta:
        proxy = True

    def __str__(self):
        # Accessing account details via base model
        return f"{self.app.name}: {self.token[:10]}..."
