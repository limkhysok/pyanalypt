from django.contrib.admin.models import LogEntry


# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
class DjangoAdminLog(LogEntry):
    class Meta:
        proxy = True

    def __str__(self):
        return f"{self.user} - {self.action_time}"
