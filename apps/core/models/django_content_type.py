from django.contrib.contenttypes.models import ContentType


# THIS IS A REFERENCE FILE BASED ON mermaid_live.md
class DjangoContentType(ContentType):
    class Meta:
        proxy = True

    def __str__(self):
        return f"{self.app_label} | {self.model}"
