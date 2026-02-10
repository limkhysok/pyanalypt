from django.db import models
from django.contrib.admin.models import LogEntry

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class DjangoAdminLog(LogEntry):
    class Meta:
        managed = False
        db_table = "django_admin_log"
