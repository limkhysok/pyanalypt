from allauth.socialaccount.models import SocialAccount as BaseSocialAccount

# THIS IS A REFERENCE FILE FOR DJANGO-ALLAUTH
# DO NOT MIGRATE.


class SocialAccount(BaseSocialAccount):
    # Explicit fields for reference (matches allauth schema)
    # provider = models.CharField(verbose_name='provider', max_length=30)
    # uid = models.CharField(verbose_name='uid', max_length=191)
    # last_login = models.DateTimeField(verbose_name='last login', auto_now=True)
    # date_joined = models.DateTimeField(verbose_name='date joined', auto_now_add=True)

    # This is where Google metadata (profile, etc.) is stored as JSON
    # extra_data = models.JSONField(verbose_name='extra data', default=dict)

    # user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = "socialaccount_socialaccount"
        unique_together = (("provider", "uid"),)

    def __str__(self):
        return f"{self.provider}: {self.uid} (User: {self.user_id})"
