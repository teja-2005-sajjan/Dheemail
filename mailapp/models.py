from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Gender(models.TextChoices):
        FEMALE = "female", "Female"
        MALE = "male", "Male"
        OTHER = "other", "Other"
        PREFER_NOT_TO_SAY = "prefer_not_to_say", "Prefer not to say"

    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True)
    contact = models.CharField(max_length=20, blank=True)

    def initials(self):
        name = self.get_full_name() or self.username
        return "".join(part[0].upper() for part in name.split()[:2]) or "U"


class Email(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        SENT = "sent", "Sent"
        READ = "read", "Read"
        STARRED = "starred", "Starred"
        DELETED = "deleted", "Deleted"

    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_emails")
    deleted_by = models.ManyToManyField(User, blank=True, related_name="deleted_emails")
    starred_by = models.ManyToManyField(User, blank=True, related_name="starred_emails")
    parent_email = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="responses",
    )
    thread_root = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="thread_messages",
    )
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.subject or "(No subject)"

    def mark_sent(self):
        self.status = self.Status.SENT
        self.sent_at = timezone.now()
        self.scheduled_at = None
        self.save(update_fields=["status", "sent_at", "scheduled_at", "updated_at"])


class Recipient(models.Model):
    class Kind(models.TextChoices):
        TO = "to", "To"
        CC = "cc", "CC"
        BCC = "bcc", "BCC"

    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name="recipients")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="received_emails")
    kind = models.CharField(max_length=3, choices=Kind.choices)
    has_read = models.BooleanField(default=False)

    class Meta:
        unique_together = ("email", "user", "kind")

    def __str__(self):
        return f"{self.get_kind_display()}: {self.user.username}"


def validate_attachment_size(file):
    max_size = 25 * 1024 * 1024
    if file.size > max_size:
        raise ValidationError("Attachment size cannot exceed 25MB.")


class Attachment(models.Model):
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="attachments/%Y/%m/%d/", validators=[validate_attachment_size])
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name


class Label(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="labels")
    name = models.CharField(max_length=40)
    emails = models.ManyToManyField(Email, blank=True, related_name="labels")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("owner", "name")

    def __str__(self):
        return self.name


class EmailSnooze(models.Model):
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name="snoozes")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_snoozes")
    snoozed_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("email", "user")
        ordering = ["snoozed_until"]

    def __str__(self):
        return f"{self.email} snoozed for {self.user} until {self.snoozed_until}"
