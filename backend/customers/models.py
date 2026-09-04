import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models

from tenancy.base_models import TenantScopedModel



class Country(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
    )

    code = models.CharField(
        max_length=10,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_country"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_country_code_per_org",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"


class City(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cities",
    )

    name = models.CharField(
        max_length=150,
    )

    code = models.CharField(
        max_length=50,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_city"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                name="unique_city_name_per_org",
            ),
        ]

    def __str__(self):
        return self.name


class Area(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="areas",
    )

    name = models.CharField(
        max_length=150,
    )

    code = models.CharField(
        max_length=50,
        blank=True,
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_area"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "city", "name"],
                name="unique_area_name_per_city_org",
            ),
        ]

    def __str__(self):
        return f"{self.name} - {self.city.name if self.city else ''}"


class Dealer(TenantScopedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        SUSPENDED = "SUSPENDED", "Suspended"
        TERMINATED = "TERMINATED", "Terminated"

    class CommissionType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "Percentage of Revenue"
        FLAT_PER_USER = "FLAT_PER_USER", "Flat Rate Per Subscriber"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    dealer_code = models.CharField(
        max_length=50,
    )

    name = models.CharField(
        max_length=150,
    )

    company_name = models.CharField(
        max_length=200,
        blank=True,
    )

    cnic = models.CharField(
        max_length=50,
        blank=True,
    )

    phone = models.CharField(
        max_length=30,
    )

    alternate_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    address_line = models.TextField(
        blank=True,
    )

    country = models.ForeignKey(
        Country,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    city = models.CharField(
        max_length=150,
        blank=True,
    )

    area = models.CharField(
        max_length=150,
        blank=True,
    )

    assigned_area = models.ForeignKey(
        Area,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dealers",
    )

    commission_rate_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
    )

    commission_type = models.CharField(
        max_length=30,
        choices=CommissionType.choices,
        default=CommissionType.PERCENTAGE,
    )

    joining_date = models.DateField()

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    notes = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_dealers",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_dealer"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "dealer_code"],
                name="unique_dealer_code_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="dealer_org_status_idx",
            ),
            models.Index(
                fields=["organization", "phone"],
                name="dealer_org_phone_idx",
            ),
        ]

    def __str__(self):
        return f"{self.dealer_code} - {self.name}"


class Customer(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    customer_number = models.CharField(
        max_length=50,
    )

    dealer = models.ForeignKey(
        Dealer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="customers",
    )

    first_name = models.CharField(
        max_length=150,
    )

    last_name = models.CharField(
        max_length=150,
        blank=True,
    )

    phone = models.CharField(
        max_length=30,
    )

    alternate_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    address_line = models.CharField(
        max_length=255,
    )

    area = models.CharField(
        max_length=150,
        blank=True,
    )

    city = models.CharField(
        max_length=150,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    class Meta:
        db_table = "customers_customer"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "customer_number"],
                name="unique_customer_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "phone"],
                name="customer_org_phone_idx",
            ),
            models.Index(
                fields=["organization", "is_active"],
                name="customer_org_active_idx",
            ),
        ]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def __str__(self):
        return (
            f"{self.customer_number} - "
            f"{self.full_name}"
        )


class InternetPackage(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    name = models.CharField(
        max_length=150,
    )

    code = models.CharField(
        max_length=50,
    )

    description = models.TextField(
        blank=True,
    )

    download_speed_mbps = models.PositiveIntegerField()

    upload_speed_mbps = models.PositiveIntegerField()

    monthly_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_internet_package"
        ordering = ["monthly_price", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_package_code_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "is_active"],
                name="package_org_active_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.name} - "
            f"{self.download_speed_mbps} Mbps"
        )


class ServiceAccount(TenantScopedModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        GRACE_PERIOD = "GRACE_PERIOD", "Grace Period"
        SUSPENSION_PENDING = (
            "SUSPENSION_PENDING",
            "Suspension Pending",
        )
        SUSPENDED_NON_PAYMENT = (
            "SUSPENDED_NON_PAYMENT",
            "Suspended Non-Payment",
        )
        RESTORE_PENDING = (
            "RESTORE_PENDING",
            "Restore Pending",
        )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    service_number = models.CharField(
        max_length=50,
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name="service_accounts",
    )

    internet_package = models.ForeignKey(
        InternetPackage,
        on_delete=models.PROTECT,
        related_name="service_accounts",
    )

    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    activated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_service_account"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "service_number"],
                name="unique_service_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="service_org_status_idx",
            ),
            models.Index(
                fields=["organization", "customer"],
                name="service_org_customer_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.service_number} - "
            f"{self.customer.full_name}"
        )


class BillingProfile(TenantScopedModel):
    class BillingCycle(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    service_account = models.OneToOneField(
        ServiceAccount,
        on_delete=models.CASCADE,
        related_name="billing_profile",
    )

    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )

    billing_day = models.PositiveSmallIntegerField()

    due_day = models.PositiveSmallIntegerField()

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_billing_profile"

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    billing_day__gte=1,
                    billing_day__lte=28,
                ),
                name="billing_day_between_1_and_28",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    due_day__gte=1,
                    due_day__lte=28,
                ),
                name="due_day_between_1_and_28",
            ),
        ]

    def __str__(self):
        return (
            f"{self.service_account.service_number} - "
            f"{self.billing_cycle}"
        )


class NotificationPreference(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    customer = models.OneToOneField(
        Customer,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )

    sms_enabled = models.BooleanField(
        default=True,
    )

    whatsapp_enabled = models.BooleanField(
        default=True,
    )

    email_enabled = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_notification_preference"

    def __str__(self):
        return (
            f"{self.customer.customer_number} - "
            f"SMS={self.sms_enabled} - "
            f"WHATSAPP={self.whatsapp_enabled}"
        )


class Inquiry(TenantScopedModel):
    class Status(models.TextChoices):
        NEW = "NEW", "New"
        CONTACTED = "CONTACTED", "Contacted"
        FEASIBILITY_PENDING = "FEASIBILITY_PENDING", "Feasibility Pending"
        FEASIBLE = "FEASIBLE", "Feasible"
        NOT_FEASIBLE = "NOT_FEASIBLE", "Not Feasible"
        FOLLOW_UP = "FOLLOW_UP", "Follow-up"
        CONVERTED = "CONVERTED", "Converted"
        LOST = "LOST", "Lost"
        CANCELLED = "CANCELLED", "Cancelled"

    class ConnectionType(models.TextChoices):
        FIBER = "FIBER", "Fiber to the Home (FTTH)"
        WIRELESS = "WIRELESS", "Wireless Broadband"
        COPPER = "COPPER", "Copper DSL"
        OTHER = "OTHER", "Other"

    class Source(models.TextChoices):
        WALK_IN = "WALK_IN", "Walk-in"
        PHONE_CALL = "PHONE_CALL", "Phone Call"
        WEBSITE = "WEBSITE", "Website Lead"
        SOCIAL_MEDIA = "SOCIAL_MEDIA", "Social Media"
        DEALER = "DEALER", "Dealer / Sub-ISP"
        REFERRAL = "REFERRAL", "Customer Referral"
        OTHER = "OTHER", "Other"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    inquiry_number = models.CharField(
        max_length=50,
    )

    full_name = models.CharField(
        max_length=150,
    )

    phone = models.CharField(
        max_length=30,
    )

    alternate_phone = models.CharField(
        max_length=30,
        blank=True,
    )

    email = models.EmailField(
        blank=True,
    )

    cnic = models.CharField(
        max_length=50,
        blank=True,
    )

    address_line = models.TextField()

    country = models.ForeignKey(
        Country,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    city = models.CharField(
        max_length=150,
    )

    area = models.CharField(
        max_length=150,
        blank=True,
    )

    preferred_package = models.ForeignKey(
        InternetPackage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inquiries",
    )

    connection_type = models.CharField(
        max_length=30,
        choices=ConnectionType.choices,
        default=ConnectionType.FIBER,
    )

    source = models.CharField(
        max_length=30,
        choices=Source.choices,
        default=Source.WALK_IN,
    )

    assigned_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_inquiries",
    )

    dealer = models.ForeignKey(
        Dealer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inquiries",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.NEW,
    )

    notes = models.TextField(
        blank=True,
    )

    follow_up_date = models.DateField(
        null=True,
        blank=True,
    )

    converted_customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="converted_from_inquiry",
    )

    converted_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_inquiries",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_inquiry"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "inquiry_number"],
                name="unique_inquiry_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="inquiry_org_status_idx",
            ),
            models.Index(
                fields=["organization", "phone"],
                name="inquiry_org_phone_idx",
            ),
            models.Index(
                fields=["organization", "follow_up_date"],
                name="inquiry_org_follow_up_idx",
            ),
        ]

    def __str__(self):
        return f"{self.inquiry_number} - {self.full_name}"


class FeasibilityAssessment(TenantScopedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        FEASIBLE = "FEASIBLE", "Feasible"
        NOT_FEASIBLE = "NOT_FEASIBLE", "Not Feasible"
        CANCELLED = "CANCELLED", "Cancelled"

    class NotFeasibleReason(models.TextChoices):
        NO_COVERAGE = "NO_COVERAGE", "No Coverage in Area"
        NO_AVAILABLE_PORT = "NO_AVAILABLE_PORT", "No Available Port on DP / FAT"
        NO_SUITABLE_NODE = "NO_SUITABLE_NODE", "No Suitable Network Node"
        CAPACITY_UNAVAILABLE = "CAPACITY_UNAVAILABLE", "Backhaul Capacity Unavailable"
        INFRASTRUCTURE_UNAVAILABLE = "INFRASTRUCTURE_UNAVAILABLE", "Civil / Pole Infrastructure Unavailable"
        DISTANCE_LIMITATION = "DISTANCE_LIMITATION", "Exceeds Maximum Physical Distance"
        OTHER = "OTHER", "Other Technical Reason"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    feasibility_number = models.CharField(
        max_length=50,
    )

    inquiry = models.ForeignKey(
        Inquiry,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="feasibility_assessments",
    )

    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="feasibility_assessments",
    )

    address_line = models.TextField()

    city = models.CharField(
        max_length=150,
    )

    area = models.CharField(
        max_length=150,
        blank=True,
    )

    package = models.ForeignKey(
        InternetPackage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feasibilities",
    )

    connection_type = models.CharField(
        max_length=30,
        choices=Inquiry.ConnectionType.choices,
        default=Inquiry.ConnectionType.FIBER,
    )

    network_node = models.ForeignKey(
        "network.NetworkNode",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feasibility_checks",
    )

    assigned_technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_feasibilities",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    not_feasible_reason = models.CharField(
        max_length=50,
        choices=NotFeasibleReason.choices,
        blank=True,
    )

    not_feasible_details = models.TextField(
        blank=True,
    )

    assessment_date = models.DateField(
        null=True,
        blank=True,
    )

    completion_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    remarks = models.TextField(
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_feasibilities",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_feasibility_assessment"
        ordering = ["-created_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "feasibility_number"],
                name="unique_fsb_number_per_org",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "status"],
                name="fsb_org_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.feasibility_number} - {self.status}"


class SuspensionPolicy(TenantScopedModel):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    grace_period_days = models.PositiveSmallIntegerField(
        default=3,
        help_text="Grace period days after due date before overdue penalties/actions",
    )

    suspension_threshold_days = models.PositiveSmallIntegerField(
        default=5,
        help_text="Days past grace period before automated suspension is triggered",
    )

    minimum_outstanding_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Minimum outstanding debt required to qualify for automated suspension",
    )

    auto_suspension_enabled = models.BooleanField(
        default=True,
        help_text="Enable/disable automated batch suspension processing",
    )

    auto_restoration_enabled = models.BooleanField(
        default=True,
        help_text="Enable/disable automatic service restoration upon full verified payment",
    )

    restore_on_partial_payment = models.BooleanField(
        default=False,
        help_text="If True, restores service on partial payment; if False, requires full balance clearance",
    )

    ptp_exemption_enabled = models.BooleanField(
        default=True,
        help_text="If True, active and unbreached Promise-to-Pay exempts subscriber from suspension",
    )

    warning_days_before_suspension = models.PositiveSmallIntegerField(
        default=2,
        help_text="Days before suspension to dispatch pre-suspension warning notice",
    )

    send_suspension_warning = models.BooleanField(
        default=True,
        help_text="Enable/disable pre-suspension warning notifications",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "customers_suspension_policy"

        constraints = [
            models.UniqueConstraint(
                fields=["organization"],
                name="unique_suspension_policy_per_org",
            ),
        ]

    def __str__(self):
        return f"{self.organization.name} - Suspension Policy"


class ServiceSuspensionLog(TenantScopedModel):
    class EventType(models.TextChoices):
        WARNING = "WARNING", "Suspension Warning"
        SUSPENSION = "SUSPENSION", "Service Suspension"
        RESTORATION = "RESTORATION", "Service Restoration"

    class TriggerType(models.TextChoices):
        SYSTEM_AUTOMATED = "SYSTEM_AUTOMATED", "System Automated"
        MANUAL_STAFF = "MANUAL_STAFF", "Manual Staff Action"
        PAYMENT_TRIGGERED = "PAYMENT_TRIGGERED", "Payment Triggered"
        PTP_EXEMPTION = "PTP_EXEMPTION", "Promise-to-Pay Exemption"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    service_account = models.ForeignKey(
        ServiceAccount,
        on_delete=models.CASCADE,
        related_name="suspension_logs",
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="suspension_logs",
    )

    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
    )

    trigger_type = models.CharField(
        max_length=30,
        choices=TriggerType.choices,
        default=TriggerType.SYSTEM_AUTOMATED,
    )

    previous_status = models.CharField(
        max_length=40,
    )

    new_status = models.CharField(
        max_length=40,
    )

    outstanding_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )

    reason = models.TextField(
        blank=True,
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="performed_suspension_logs",
    )

    invoices_snapshot = models.JSONField(
        default=list,
        blank=True,
    )

    linked_payment_id = models.UUIDField(
        null=True,
        blank=True,
    )

    linked_promise_id = models.UUIDField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        db_table = "customers_service_suspension_log"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["organization", "event_type"],
                name="susp_log_org_event_idx",
            ),
            models.Index(
                fields=["organization", "service_account"],
                name="susp_log_org_svc_idx",
            ),
            models.Index(
                fields=["organization", "customer"],
                name="susp_log_org_cust_idx",
            ),
            models.Index(
                fields=["organization", "created_at"],
                name="susp_log_org_created_idx",
            ),
        ]

    def __str__(self):
        return f"{self.service_account.service_number} - {self.event_type} ({self.created_at})"