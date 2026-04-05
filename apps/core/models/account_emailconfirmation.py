from allauth.account.models import EmailConfirmation


# THIS IS A REFERENCE FILE FOR DJANGO-ALLAUTH
class AccountEmailConfirmation(EmailConfirmation):
    class Meta:
        proxy = True

    def __str__(self):
        return f"Confirmation for {self.email_address}"
