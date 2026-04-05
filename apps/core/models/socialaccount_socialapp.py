from allauth.socialaccount.models import SocialApp as BaseSocialApp


# THIS IS A REFERENCE FILE FOR DJANGO-ALLAUTH
class SocialApp(BaseSocialApp):
    class Meta:
        proxy = True

    def __str__(self):
        return f"{self.name} ({self.provider})"
