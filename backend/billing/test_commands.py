from io import StringIO
from unittest.mock import patch

from django.core.management import call_command, CommandError
from django.test import TestCase

from tenancy.models import Organization


class CollectionCommandTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Command Test ISP",
            code="CMD-TEST",
            city="Lahore",
            timezone="Asia/Karachi",
            currency="PKR",
        )

    @patch(
        "billing.management.commands.run_collections.run_collection_automation",
        side_effect=ValueError("simulated automation failure"),
    )
    def test_collection_command_returns_failure_status_when_organization_fails(
        self,
        run_automation,
    ):
        stdout = StringIO()
        stderr = StringIO()

        with self.assertRaises(CommandError) as context:
            call_command(
                "run_collections",
                organization_code=self.organization.code,
                stdout=stdout,
                stderr=stderr,
            )

        self.assertIn(
            "completed with 1 failure(s)",
            str(context.exception),
        )
        self.assertIn(
            "CMD-TEST: simulated automation failure",
            stderr.getvalue(),
        )
        run_automation.assert_called_once()
