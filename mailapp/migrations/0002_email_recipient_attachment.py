import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import mailapp.models


class Migration(migrations.Migration):
    dependencies = [
        ("mailapp", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Email",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(blank=True, max_length=255)),
                ("body", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("draft", "Draft"), ("sent", "Sent"), ("read", "Read"), ("starred", "Starred"), ("deleted", "Deleted")], default="draft", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sent_emails", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="Attachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="attachments/%Y/%m/%d/", validators=[mailapp.models.validate_attachment_size])),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("email", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="mailapp.email")),
            ],
        ),
        migrations.CreateModel(
            name="Recipient",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("to", "To"), ("cc", "CC"), ("bcc", "BCC")], max_length=3)),
                ("has_read", models.BooleanField(default=False)),
                ("email", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="recipients", to="mailapp.email")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="received_emails", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("email", "user", "kind")},
            },
        ),
    ]
