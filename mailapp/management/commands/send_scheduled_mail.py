from django.core.management.base import BaseCommand
from django.utils import timezone

from mailapp.models import Email


class Command(BaseCommand):
    help = "Send DheeMail emails whose scheduled time has arrived."

    def handle(self, *args, **options):
        due_emails = Email.objects.filter(status=Email.Status.SCHEDULED, scheduled_at__lte=timezone.now())
        count = due_emails.count()
        for email in due_emails:
            email.mark_sent()
        self.stdout.write(self.style.SUCCESS(f"Sent {count} scheduled email(s)."))
