from django.db import models

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class AuthGroupPermissions(models.Model):
    id = models.AutoField(primary_key=True)
    group_id = models.IntegerField()  # FK to auth_group
    permission_id = models.IntegerField()  # FK to auth_permission

    class Meta:
        managed = False
        db_table = "auth_group_permissions"
