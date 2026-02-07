from django.db import models
from django.contrib.sessions.models import Session

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class DjangoSession(Session):
    class Meta:
        managed = False
        db_table = "django_session"
