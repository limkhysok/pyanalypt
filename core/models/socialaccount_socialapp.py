from allauth.socialaccount.models import SocialApp as BaseSocialApp


# REFERENCE ONLY - Matches socialaccount_socialapp table
class SocialApp(BaseSocialApp):
    # explicit fields for reference
    # provider = models.CharField(verbose_name='provider', max_length=30)
    # name = models.CharField(verbose_name='name', max_length=40)
    # client_id = models.CharField(verbose_name='client id', max_length=191)
    # secret = models.CharField(verbose_name='secret icon', max_length=191)
    # key = models.CharField(verbose_name='key', max_length=191, blank=True)

    # sites = models.ManyToManyField(Site, blank=True)

    class Meta:
        managed = False
        db_table = "socialaccount_socialapp"

    def __str__(self):
        return self.name
