from django.db import models

# THIS IS A REFERENCE FILE FOR DJANGO-ALLAUTH
# DO NOT MIGRATE.


class SocialAccount(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()  # FK to auth_user
    provider = models.CharField(max_length=30)
    uid = models.CharField(max_length=191)
    last_login = models.DateTimeField(auto_now=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    # Google sends {"email_verified": true, ...} in this JSON field.
    # We rely on this for "is_email_confirm".
    extra_data = models.JSONField(default=dict)

    class Meta:
        managed = False
        db_table = "socialaccount_socialaccount"
        unique_together = ("provider", "uid")

    def __str__(self):
        return f"{self.provider}: {self.uid}"
