from django.conf import settings
from django.core.management.base import BaseCommand

from common.services.outbox_publisher import publish_outbox_batch


class Command(BaseCommand):
    help = "Publish pending outbox notification events to EventBridge."

    def add_arguments(self, parser):
        parser.add_argument("--database", default="default")
        parser.add_argument("--limit", type=int, default=settings.OUTBOX_PUBLISH_BATCH_SIZE)
        parser.add_argument(
            "--aggregate-type",
            default=settings.OUTBOX_NOTIFICATION_AGGREGATE_TYPE,
        )
        parser.add_argument("--max-retries", type=int, default=settings.OUTBOX_MAX_RETRIES)
        parser.add_argument(
            "--retry-base-delay-seconds",
            type=int,
            default=settings.OUTBOX_RETRY_BASE_DELAY_SECONDS,
        )

    def handle(self, *args, **options):
        result = publish_outbox_batch(
            database=options["database"],
            aggregate_type=options["aggregate_type"],
            limit=options["limit"],
            max_retries=options["max_retries"],
            retry_base_delay_seconds=options["retry_base_delay_seconds"],
        )
        self.stdout.write(
            self.style.SUCCESS(
                "picked={picked} published={published} failed={failed}".format(**result)
            )
        )
