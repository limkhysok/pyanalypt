from django.db import models
from django.contrib.auth.models import Group

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class AuthGroup(Group):
    class Meta:
        managed = False
        db_table = "auth_group"

    def __str__(self):
        return self.name
