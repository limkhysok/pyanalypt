from django.db import models
from allauth.account.models import EmailConfirmation

# THIS IS A REFERENCE FILE
# DO NOT MIGRATE.


class AccountEmailConfirmation(EmailConfirmation):
    class Meta:
        managed = False
        db_table = "account_emailconfirmation"
