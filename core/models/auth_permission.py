from django.db import models
from django.contrib.auth.models import Permission

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class AuthPermission(Permission):
    class Meta:
        managed = False
        db_table = "auth_permission"

    def __str__(self):
        return f"{self.content_type_id} | {self.codename}"
