from django.db import models
from allauth.socialaccount.models import SocialAccount as BaseSocialAccount

# THIS IS A REFERENCE FILE FOR DJANGO-ALLAUTH
# DO NOT MIGRATE.


class SocialAccount(BaseSocialAccount):
    class Meta:
        managed = False
        db_table = "socialaccount_socialaccount"

    def __str__(self):
        return f"{self.provider}: {self.uid}"
