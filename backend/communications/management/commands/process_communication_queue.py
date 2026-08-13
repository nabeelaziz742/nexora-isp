import time

from django.core.management.base import BaseCommand

from communications.tasks import (
    process_pending_communications,
)


class Command(BaseCommand):
    help = "Process pending communication queue."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process queue once and exit.",
        )

        parser.add_argument(
            "--sleep",
            type=int,
            default=5,
            help="Sleep interval between queue checks.",
        )

    def handle(self, *args, **options):

        if options["once"]:
            processed = process_pending_communications()

            self.stdout.write(
                self.style.SUCCESS(
                    f"Processed {processed} communication(s)."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "Communication Queue Worker Started..."
            )
        )

        sleep_seconds = options["sleep"]

        while True:
            try:
                processed = process_pending_communications()

                if processed:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Processed {processed} communication(s)."
                        )
                    )

                time.sleep(sleep_seconds)

            except KeyboardInterrupt:
                self.stdout.write(
                    self.style.WARNING(
                        "Communication Queue Worker Stopped."
                    )
                )
                break

            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(str(exc))
                )
                time.sleep(sleep_seconds)