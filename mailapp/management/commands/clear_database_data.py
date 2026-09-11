from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Delete all existing data from the database while keeping tables and migrations intact."

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_true",
            dest="noinput",
            help="Delete data without asking for confirmation.",
        )

    def handle(self, *args, **options):
        call_command(
            "flush",
            interactive=not options["noinput"],
            verbosity=options.get("verbosity", 1),
        )
        self.stdout.write(self.style.SUCCESS("Database data cleared successfully."))
