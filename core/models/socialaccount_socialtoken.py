from allauth.socialaccount.models import SocialToken as BaseSocialToken


# REFERENCE ONLY - Matches socialaccount_socialtoken table
class SocialToken(BaseSocialToken):
    # explicit fields for reference
    # token = models.TextField(verbose_name='token')
    # token_secret = models.TextField(verbose_name='token secret', blank=True)
    # expires_at = models.DateTimeField(verbose_name='expires at', blank=True, null=True)

    # account = models.ForeignKey(SocialAccount, on_delete=models.CASCADE)
    # app = models.ForeignKey(SocialApp, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = "socialaccount_socialtoken"

    def __str__(self):
        return f"{self.app.name}: {self.token[:10]}..."
