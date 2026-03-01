from allauth.socialaccount.models import SocialAccount as BaseSocialAccount


# THIS IS A REFERENCE FILE FOR DJANGO-ALLAUTH
class SocialAccount(BaseSocialAccount):
    class Meta:
        proxy = True

    def __str__(self):
        return f"{self.provider}: {self.uid} (User: {self.user_id})"
