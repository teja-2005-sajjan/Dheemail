from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("mailapp", "0005_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="email",
            name="scheduled_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="email",
            name="status",
            field=models.CharField(choices=[("draft", "Draft"), ("scheduled", "Scheduled"), ("sent", "Sent"), ("read", "Read"), ("starred", "Starred"), ("deleted", "Deleted")], default="draft", max_length=20),
        ),
        migrations.CreateModel(
            name="EmailSnooze",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("snoozed_until", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("email", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="snoozes", to="mailapp.email")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="email_snoozes", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["snoozed_until"],
                "unique_together": {("email", "user")},
            },
        ),
    ]
