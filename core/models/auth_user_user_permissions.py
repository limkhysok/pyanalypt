from django.db import models

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class AuthUserUserPermissions(models.Model):
    id = models.AutoField(primary_key=True)
    user_id = models.IntegerField()  # FK to auth_user
    permission_id = models.IntegerField()  # FK to auth_permission

    class Meta:
        managed = False
        db_table = "auth_user_user_permissions"
