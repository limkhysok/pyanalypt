from allauth.account.signals import email_confirmed
from django.dispatch import receiver


@receiver(email_confirmed)
def mark_email_verified(sender, request, email_address, **kwargs):
    """
    Sync AuthUser.email_verified when allauth confirms the email address.
    This fires when the user clicks the verification link in their email.
    """
    user = email_address.user
    if not user.email_verified:
        user.email_verified = True
        user.save(update_fields=["email_verified"])
