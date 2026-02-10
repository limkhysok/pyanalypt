from django.db import models
from allauth.account.models import EmailAddress

# THIS IS A REFERENCE FILE
# DO NOT MIGRATE.


class AccountEmailAddress(EmailAddress):
    id = models.AutoField(primary_key=True)
    email = models.EmailField()
    verified = models.BooleanField()
    primary = models.BooleanField()
    user_id = models.ManyToOneRel("AuthUser", models.CASCADE, "emailaddress_set")

    class Meta:
        managed = False
        db_table = "account_emailaddress"
