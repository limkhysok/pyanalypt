from django.db import migrations


class Migration(migrations.Migration):
    """
    Drop the orphan `issues_issue` table left behind by a removed app.
    Its FK constraint on datasets_dataset.id was blocking dataset deletion.
    """

    dependencies = [
        ("datasets", "0008_extend_action_choices"),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS issues_issue CASCADE;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
