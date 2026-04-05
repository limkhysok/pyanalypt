from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("issues", "0002_alter_issue_column_name_alter_issue_suggested_fix"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="detected_by",
            field=models.CharField(
                choices=[
                    ("PANDAS", "Pandas Scan"),
                    ("GEMINI", "Gemini AI Scan"),
                    ("MANUAL", "Manual"),
                ],
                default="PANDAS",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="affected_rows",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="issue",
            name="is_user_modified",
            field=models.BooleanField(default=False),
        ),
    ]
