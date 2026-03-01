from django.db import models

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class AuthUserUserPermissions(models.Model):
    id = models.AutoField(primary_key=True)
    # The column name in the database is 'authuser_id'
    user = models.ForeignKey(
        "AuthUser", on_delete=models.CASCADE, db_column="authuser_id"
    )
    # The column name in the database is 'permission_id'
    permission = models.ForeignKey(
        "AuthPermission", on_delete=models.CASCADE, db_column="permission_id"
    )

    class Meta:
        managed = False
        db_table = "auth_user_user_permissions"
        unique_together = (("user", "permission"),)
