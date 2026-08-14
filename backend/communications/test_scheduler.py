from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase
from django.utils import timezone

from communications.models import CommunicationSchedule
from communications.scheduler import CommunicationScheduleService


class CommunicationScheduleServiceTests(SimpleTestCase):
    def test_monthly_schedule_handles_short_month(self):
        value = timezone.make_aware(datetime(2026, 1, 31, 10, 0))
        result = CommunicationScheduleService._add_month(value)
        self.assertEqual(result.date().isoformat(), "2026-02-28")

    def test_process_schedule_skips_missing_schedule(self):
        self.assertFalse(CommunicationScheduleService.process_schedule("missing"))

    @patch("communications.scheduler.Customer.objects.filter")
    @patch("communications.scheduler.CommunicationAutomationService.execute_automation")
    def test_process_due_has_a_safe_batch_limit(self, execute_automation, customer_filter):
        customer_filter.return_value.order_by.return_value.iterator.return_value = iter(())
        with patch.object(
            CommunicationScheduleService,
            "_due_schedule_ids",
            return_value=[],
        ) as due_ids:
            self.assertEqual(CommunicationScheduleService.process_due(limit=7), 0)
            due_ids.assert_called_once_with(limit=7)
        execute_automation.assert_not_called()
