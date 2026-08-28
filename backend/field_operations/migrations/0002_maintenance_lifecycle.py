from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("field_operations", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="workorder",
            name="maintenance_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="workorder",
            name="scheduled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workorder",
            name="started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="workorder",
            name="restored_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="workorder",
            name="status",
            field=models.CharField(
                choices=[
                    ("CREATED", "Created"),
                    ("ASSIGNED", "Assigned"),
                    ("DISPATCHED", "Dispatched"),
                    ("ONSITE", "Onsite"),
                    ("COMPLETED", "Completed"),
                    ("SCHEDULED", "Scheduled"),
                    ("STARTED", "Started"),
                    ("RESTORED", "Restored"),
                ],
                default="CREATED",
                max_length=30,
            ),
        ),
    ]
