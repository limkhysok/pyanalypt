from allauth.account.models import EmailAddress


# THIS IS A REFERENCE FILE FOR DJANGO-ALLAUTH
class AccountEmailAddress(EmailAddress):
    class Meta:
        proxy = True

    def __str__(self):
        return f"{self.email} ({self.user})"
