from django.db import models

# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
# DO NOT MIGRATE.


class AuthGroupPermissions(models.Model):
    id = models.AutoField(primary_key=True)
    # The column name in the database is 'group_id'
    group = models.ForeignKey(
        "AuthGroup", on_delete=models.CASCADE, db_column="group_id"
    )
    # The column name in the database is 'permission_id'
    permission = models.ForeignKey(
        "AuthPermission", on_delete=models.CASCADE, db_column="permission_id"
    )

    class Meta:
        managed = False
        db_table = "auth_group_permissions"
        unique_together = (("group", "permission"),)
