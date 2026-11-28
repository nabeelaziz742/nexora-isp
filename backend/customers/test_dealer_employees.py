from datetime import date
from decimal import Decimal

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from accounts.models import User
from billing.models import Payment
from customers.models import Country, Dealer, DealerEmployee
from customers import test_dealer_portal as portal_tests
from tenancy.models import Organization, OrganizationMembership

EMPLOYEE_PASSWORD = "Collector!2345"


class DealerEmployeeTests(TestCase):
    # Same ISP, two dealers and three customers as the dealer portal tests.
    # (Borrowed through the module so the runner does not collect those tests twice.)
    setUp = portal_tests.DealerPortalTests.setUp
    grant = portal_tests.DealerPortalTests.grant
    dealer_login = portal_tests.DealerPortalTests.dealer_login

    def as_dealer(self):
        self.assertEqual(self.grant().status_code, 200)
        self.assertEqual(self.dealer_login().status_code, 200)

    def add_employee(self, email="ali@dealer.test", **rights):
        response = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Ali", "last_name": "Collector", "phone": "03005555555",
            "email": email, "password": EMPLOYEE_PASSWORD, "rights": rights,
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def employee_login(self, email="ali@dealer.test"):
        self.client.credentials()
        response = self.client.post("/api/v1/auth/login/", {
            "organization_code": "ALPHA", "email": email, "password": EMPLOYEE_PASSWORD,
        }, format="json")
        if response.status_code == 200:
            self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response

    # -- dealer manages employees ----------------------------------------------

    def test_dealer_adds_employee_who_can_sign_in(self):
        self.as_dealer()
        row = self.add_employee(can_collect_payments=True, can_recharge=False)
        self.assertEqual(row["full_name"], "Ali Collector")
        self.assertTrue(row["rights"]["can_collect_payments"])
        self.assertFalse(row["rights"]["can_recharge"])
        login = self.employee_login()
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data["role"], "DEALER")
        me = self.client.get("/api/v1/dealer-portal/summary/").data["me"]
        self.assertFalse(me["is_dealer"])
        self.assertEqual(me["name"], "Ali Collector")

    def test_employee_is_not_isp_staff(self):
        self.as_dealer()
        self.add_employee()
        employee = DealerEmployee.objects.get()
        self.assertEqual(employee.membership.role, OrganizationMembership.Role.DEALER)
        self.employee_login()
        self.assertEqual(self.client.get("/api/v1/customers/").status_code, 403)

    def test_employee_cannot_manage_employees(self):
        self.as_dealer()
        self.add_employee()
        self.employee_login()
        self.assertEqual(self.client.get("/api/v1/dealer-portal/employees/").status_code, 403)
        response = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "X", "email": "x@dealer.test", "password": EMPLOYEE_PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 403)

    def test_existing_email_is_refused(self):
        self.as_dealer()
        response = self.client.post("/api/v1/dealer-portal/employees/", {
            "first_name": "Ali", "email": "owner@alpha.test", "password": EMPLOYEE_PASSWORD,
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_dealer_cannot_touch_another_dealers_employee(self):
        self.as_dealer()
        self.add_employee()
        employee = DealerEmployee.objects.get()
        self.assertEqual(self.grant(email="kashif@dealer.test", dealer=self.other_dealer).status_code, 200)
        self.dealer_login("kashif@dealer.test")
        self.assertEqual(self.client.get("/api/v1/dealer-portal/employees/").data["results"], [])
        response = self.client.patch(f"/api/v1/dealer-portal/employees/{employee.id}/", {"is_active": False},
                                     format="json")
        self.assertEqual(response.status_code, 404)

    # -- rights ------------------------------------------------------------------

    def test_rights_decide_what_an_employee_can_do(self):
        self.as_dealer()
        self.add_employee(can_view_customers=True, can_view_all_customers=True, can_collect_payments=True, can_recharge=False,
                          can_request_customers=False, can_view_collections=False)
        self.employee_login()

        customers = self.client.get("/api/v1/dealer-portal/customers/")
        self.assertEqual(customers.status_code, 200)
        self.assertEqual(
            sorted(row["customer_name"] for row in customers.data["results"]), ["Ahmed", "Sana"],
        )
        pay = self.client.post(f"/api/v1/dealer-portal/services/{self.ahmed.id}/payments/",
                               {"amount": "1000", "payment_method": "CASH"}, format="json")
        self.assertEqual(pay.status_code, 201, pay.data)

        refused = [
            self.client.post(f"/api/v1/dealer-portal/services/{self.sana.id}/recharge/",
                             {"months": 1, "payment_method": "CASH"}, format="json"),
            self.client.get("/api/v1/dealer-portal/requests/"),
            self.client.get("/api/v1/dealer-portal/collections/"),
        ]
        self.assertEqual([r.status_code for r in refused], [403, 403, 403])

        summary = self.client.get("/api/v1/dealer-portal/summary/").data
        self.assertNotIn("commission_this_month", summary)
        self.assertNotIn("collected_this_month", summary)
        self.assertFalse(summary["me"]["rights"]["can_recharge"])

    def test_dealer_changes_rights_and_they_apply_at_once(self):
        self.as_dealer()
        row = self.add_employee(can_view_all_customers=True, can_recharge=False)
        self.client.patch(f"/api/v1/dealer-portal/employees/{row['id']}/",
                          {"rights": {"can_recharge": True}}, format="json")
        self.employee_login()
        response = self.client.post(f"/api/v1/dealer-portal/services/{self.sana.id}/recharge/",
                                    {"months": 1, "payment_method": "CASH"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)

    def test_employee_still_limited_to_own_dealers_customers(self):
        self.as_dealer()
        self.add_employee(can_collect_payments=True)
        self.employee_login()
        response = self.client.post(f"/api/v1/dealer-portal/services/{self.imran.id}/payments/",
                                    {"amount": "500", "payment_method": "CASH"}, format="json")
        self.assertEqual(response.status_code, 404)

    # -- switching off -----------------------------------------------------------

    def test_disabled_employee_cannot_sign_in(self):
        self.as_dealer()
        row = self.add_employee()
        self.client.patch(f"/api/v1/dealer-portal/employees/{row['id']}/", {"is_active": False}, format="json")
        self.assertNotEqual(self.employee_login().status_code, 200)

    def test_turning_off_dealer_login_locks_out_employees(self):
        self.as_dealer()
        self.add_employee(can_view_all_customers=True)
        self.employee_login()
        self.assertEqual(self.client.get("/api/v1/dealer-portal/customers/").status_code, 200)
        self.grant()  # owner signs in again
        self.client.delete(f"/api/v1/customers/dealers/{self.dealer.id}/portal-access/")
        self.employee_login()
        self.assertEqual(self.client.get("/api/v1/dealer-portal/customers/").status_code, 403)

    def test_dealer_resets_employee_password(self):
        self.as_dealer()
        row = self.add_employee()
        response = self.client.post(f"/api/v1/dealer-portal/employees/{row['id']}/password/",
                                    {"password": "Fresh!Gate5521"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.employee_login().status_code, 200)
        employee = DealerEmployee.objects.get()
        self.assertTrue(employee.membership.user.check_password("Fresh!Gate5521"))

    # -- who collected what --------------------------------------------------------

    def test_collections_show_who_collected(self):
        self.as_dealer()
        self.add_employee(can_view_all_customers=True, can_collect_payments=True, can_view_collections=True)
        self.client.post(f"/api/v1/dealer-portal/services/{self.ahmed.id}/payments/",
                         {"amount": "700", "payment_method": "CASH"}, format="json")
        self.employee_login()
        self.client.post(f"/api/v1/dealer-portal/services/{self.ahmed.id}/payments/",
                         {"amount": "300", "payment_method": "CASH"}, format="json")

        own = self.client.get("/api/v1/dealer-portal/collections/").data
        self.assertEqual([r["amount"] for r in own["results"]], ["300.00"])
        self.assertNotIn("commission", own)

        self.dealer_login()
        everything = self.client.get("/api/v1/dealer-portal/collections/").data
        self.assertEqual(everything["total_collected"], "1000.00")
        totals = {row["name"]: row["total"] for row in everything["by_person"]}
        self.assertEqual(totals["Ali Collector"], "300.00")
        self.assertEqual(sum(Decimal(v) for v in totals.values()), Decimal("1000.00"))
        payment = Payment.objects.get(amount=Decimal("300.00"))
        self.assertIn("Ali Collector for dealer DL-1", payment.notes)

    # -- Phase 1: grouped rights, web login, employee manager ------------------

    def test_right_groups_match_model_rights_and_exclude_discount(self):
        grouped_keys = [r["key"] for group in DealerEmployee.right_groups_schema() for r in group["rights"]]
        self.assertEqual(len(grouped_keys), 32)
        self.assertEqual(tuple(grouped_keys), DealerEmployee.RIGHTS)
        self.assertFalse(any("discount" in key for key in grouped_keys))
        self.assertEqual(
            [group["label"] for group in DealerEmployee.right_groups_schema()],
            ["Customer", "Collection", "System", "Admin", "Messaging", "Accounts"],
        )

    def test_can_web_login_false_blocks_sign_in_refresh_and_portal(self):
        self.as_dealer()
        row = self.add_employee(can_web_login=True)
        login = self.employee_login()
        self.assertEqual(login.status_code, 200)
        refresh_token = login.data["refresh"]
        access_token = login.data["access"]

        self.dealer_login()
        self.client.patch(
            f"/api/v1/dealer-portal/employees/{row['id']}/",
            {"rights": {"can_web_login": False}},
            format="json",
        )

        # Sign-in fails with a clear message.
        blocked = self.employee_login()
        self.assertEqual(blocked.status_code, 400)
        self.assertIn("Web login is disabled", str(blocked.data["detail"]))

        # Token refresh fails.
        self.client.credentials()
        refreshed = self.client.post("/api/v1/auth/token/refresh/", {"refresh": refresh_token}, format="json")
        self.assertEqual(refreshed.status_code, 400)

        # Existing access token is also refused on dealer portal.
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        summary = self.client.get("/api/v1/dealer-portal/summary/")
        self.assertEqual(summary.status_code, 403)

    def test_can_view_dashboard_false_hides_dashboard_metrics(self):
        self.as_dealer()
        self.add_employee(can_view_dashboard=False, can_view_customers=True)
        self.employee_login()
        summary = self.client.get("/api/v1/dealer-portal/summary/")
        self.assertEqual(summary.status_code, 200)
        self.assertFalse(summary.data["show_dashboard"])
        self.assertNotIn("total_customers", summary.data)
        self.assertNotIn("collected_by_me_this_month", summary.data)

    def test_employee_with_can_manage_employees_cannot_exceed_own_rights_or_edit_self(self):
        self.as_dealer()
        manager = self.add_employee(
            email="mgr@dealer.test",
            can_manage_employees=True,
            can_view_customers=True,
            can_collect_payments=False,
            can_recharge=False,
            can_web_login=True,
            can_view_dashboard=True,
        )
        other = self.add_employee(email="clerk@dealer.test", can_view_customers=True, can_collect_payments=False)
        self.employee_login("mgr@dealer.test")

        # Cannot change own rights or deactivate self.
        self.assertEqual(
            self.client.patch(
                f"/api/v1/dealer-portal/employees/{manager['id']}/",
                {"rights": {"can_recharge": True}},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/dealer-portal/employees/{manager['id']}/",
                {"is_active": False},
                format="json",
            ).status_code,
            403,
        )

        # Cannot grant a right they lack on create or update.
        self.assertEqual(
            self.client.post(
                "/api/v1/dealer-portal/employees/",
                {
                    "first_name": "Bad",
                    "email": "bad@dealer.test",
                    "password": EMPLOYEE_PASSWORD,
                    "rights": {"can_recharge": True},
                },
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f"/api/v1/dealer-portal/employees/{other['id']}/",
                {"rights": {"can_collect_payments": True}},
                format="json",
            ).status_code,
            403,
        )

        # Creating with omitted rights never grants a model-default right that the manager lacks.
        created = self.client.post(
            "/api/v1/dealer-portal/employees/",
            {
                "first_name": "Junior",
                "email": "junior@dealer.test",
                "password": EMPLOYEE_PASSWORD,
                "rights": {"can_view_customers": True},
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertTrue(created.data["rights"]["can_view_customers"])
        self.assertFalse(created.data["rights"]["can_collect_payments"])

        # Can edit another employee of the same dealer within own rights.
        updated = self.client.patch(
            f"/api/v1/dealer-portal/employees/{other['id']}/",
            {"phone": "03007778899", "rights": {"can_view_customers": False}},
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["phone"], "03007778899")
        self.assertFalse(updated.data["rights"]["can_view_customers"])

        # Cannot touch another dealer's employee.
        self.assertEqual(self.grant(email="kashif@dealer.test", dealer=self.other_dealer).status_code, 200)
        self.dealer_login("kashif@dealer.test")
        foreign = self.add_employee(email="foreign@dealer.test")
        self.employee_login("mgr@dealer.test")
        self.assertEqual(
            self.client.patch(
                f"/api/v1/dealer-portal/employees/{foreign['id']}/",
                {"phone": "03000000000"},
                format="json",
            ).status_code,
            404,
        )


class DealerEmployeeRightsMigrationTests(TransactionTestCase):
    def test_existing_employees_keep_powers_and_get_web_login_and_dashboard(self):
        executor = MigrationExecutor(connection)
        all_leaves = executor.loader.graph.leaf_nodes()
        other_leaves = [
            ("communications", "0007_whatsapp_meta_templates") if node[0] == "communications" else node
            for node in all_leaves
            if node[0] != "customers"
        ]
        migrate_from = [*other_leaves, ("customers", "0012_dealer_slabs_and_sub_dealers")]
        migrate_to = [*other_leaves, ("customers", "0013_dealer_employee_rights")]

        try:
            executor.migrate(migrate_from)
            old_apps = executor.loader.project_state(migrate_from).apps

            OldOrg = old_apps.get_model("tenancy", "Organization")
            OldUser = old_apps.get_model("accounts", "User")
            OldMembership = old_apps.get_model("tenancy", "OrganizationMembership")
            OldDealer = old_apps.get_model("customers", "Dealer")
            OldDealerEmployee = old_apps.get_model("customers", "DealerEmployee")

            org = OldOrg.objects.create(name="Mig ISP", code="MIGISP", city="Lahore")
            dealer = OldDealer.objects.create(
                organization=org,
                dealer_code="DLR-MIG",
                name="Dealer Mig",
                phone="03001112233",
                joining_date=date(2025, 1, 1),
            )
            user = OldUser.objects.create(username="oldemp@mig.test", email="oldemp@mig.test", password="x")
            membership = OldMembership.objects.create(
                organization=org, user=user, role="DEALER", is_active=True
            )
            emp = OldDealerEmployee.objects.create(
                organization=org,
                dealer=dealer,
                membership=membership,
                can_view_customers=False,
                can_collect_payments=True,
                can_recharge=True,
                can_request_customers=False,
                can_view_collections=True,
            )

            executor.loader.build_graph()
            executor.migrate(migrate_to)
            new_apps = executor.loader.project_state(migrate_to).apps
            NewDealerEmployee = new_apps.get_model("customers", "DealerEmployee")
            migrated = NewDealerEmployee.objects.get(pk=emp.pk)

            self.assertFalse(migrated.can_view_customers)
            self.assertTrue(migrated.can_collect_payments)
            self.assertTrue(migrated.can_recharge)
            self.assertFalse(migrated.can_request_customers)
            self.assertTrue(migrated.can_view_collections)
            self.assertTrue(migrated.can_web_login)
            self.assertTrue(migrated.can_view_dashboard)
            for field in (
                "can_view_all_customers",
                "can_import_customers",
                "can_export_customers",
                "can_edit_customers",
                "can_deactivate_customers",
                "can_view_ledger",
                "can_manage_complaints",
                "can_mobile_login",
                "can_view_packages",
                "can_manage_sms_templates",
                "can_view_sms_log",
                "can_view_areas",
                "can_manage_areas",
                "can_manage_employees",
                "can_change_payment_date",
                "can_reverse_payments",
                "can_view_all_collections",
                "can_edit_company_info",
                "can_send_sms",
                "can_broadcast_sms",
                "can_cancel_sms",
                "can_view_accounts",
                "can_view_journal",
                "can_add_journal_entries",
                "can_void_journal_entries",
            ):
                self.assertFalse(getattr(migrated, field), field)
        finally:
            executor.loader.build_graph()
            executor.migrate(all_leaves)
