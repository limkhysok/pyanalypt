from rest_framework.authtoken.models import Token as BaseToken


# Proxy model to show the DRF tokens in the 'core' admin app section
class Token(BaseToken):
    class Meta:
        proxy = True
        # Match the verbose name if needed
        verbose_name = "Auth Token"
        verbose_name_plural = "Auth Tokens"

    def __str__(self):
        return self.key
