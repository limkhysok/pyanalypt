from django.contrib.auth.models import Group


# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
class AuthGroup(Group):
    class Meta:
        proxy = True

    def __str__(self):
        return self.name
