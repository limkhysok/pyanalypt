from django.contrib.sessions.models import Session


# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
class DjangoSession(Session):
    class Meta:
        proxy = True

    def __str__(self):
        return self.session_key
