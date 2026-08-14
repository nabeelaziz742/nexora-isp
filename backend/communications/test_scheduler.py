from datetime import datetime
from uuid import uuid4
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from communications.scheduler import CommunicationScheduleService


class CommunicationScheduleServiceTests(TestCase):
    def test_monthly_schedule_handles_short_month(self):
        value = timezone.make_aware(datetime(2026, 1, 31, 10, 0))
        result = CommunicationScheduleService._add_month(value)
        self.assertEqual(result.date().isoformat(), "2026-02-28")

    def test_process_schedule_skips_missing_schedule(self):
        self.assertFalse(CommunicationScheduleService.process_schedule(uuid4()))

    def test_process_due_has_a_safe_batch_limit(self):
        with patch.object(
            CommunicationScheduleService,
            "_due_schedule_ids",
            return_value=[],
        ) as due_ids:
            self.assertEqual(CommunicationScheduleService.process_due(limit=7), 0)
            due_ids.assert_called_once_with(limit=7)
