from rest_framework.authtoken.models import Token as BaseToken


# REFERENCE ONLY - Matches authtoken_token table
class Token(BaseToken):
    class Meta:
        managed = False
        db_table = "authtoken_token"

    def __str__(self):
        return self.key
