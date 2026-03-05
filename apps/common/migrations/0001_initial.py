from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="OutboxEvent",
            fields=[
                ("outbox_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("aggregate_type", models.CharField(max_length=64)),
                ("aggregate_id", models.CharField(blank=True, max_length=64, null=True)),
                ("event_type", models.CharField(max_length=128)),
                ("payload", models.JSONField()),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "Pending"), ("published", "Published"), ("failed", "Failed")],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("available_at", models.DateTimeField(auto_now_add=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "db_table": "outbox_events",
                "ordering": ["outbox_id"],
            },
        ),
        migrations.AddIndex(
            model_name="outboxevent",
            index=models.Index(fields=["status", "available_at"], name="outbox_even_status_8e03e0_idx"),
        ),
        migrations.AddIndex(
            model_name="outboxevent",
            index=models.Index(fields=["event_type", "created_at"], name="outbox_even_event_t_1ba95d_idx"),
        ),
    ]
