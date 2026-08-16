# Generated manually for the initial payment-gated onboarding models.
import uuid

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenancy", "0002_auditlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="PaymentSettings",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("bank_name", models.CharField(max_length=150)),
                ("account_title", models.CharField(max_length=255)),
                ("account_number", models.CharField(max_length=100)),
                ("iban", models.CharField(blank=True, max_length=100)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(0)])),
                ("instructions", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "onboarding_payment_settings"},
        ),
        migrations.CreateModel(
            name="ISPRegistration",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("PENDING_PAYMENT", "Pending Payment"), ("PENDING_VERIFICATION", "Pending Verification"), ("ACTIVE", "Active"), ("REJECTED", "Rejected")], db_index=True, default="PENDING_PAYMENT", max_length=30)),
                ("amount_due", models.DecimalField(decimal_places=2, max_digits=12)),
                ("receipt", models.ImageField(blank=True, null=True, upload_to="payment_receipts/%Y/%m/")),
                ("rejection_reason", models.TextField(blank=True)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("verified_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="registration", to="tenancy.organization")),
                ("owner", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="isp_registration", to=settings.AUTH_USER_MODEL)),
                ("verified_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="verified_isp_registrations", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "db_table": "onboarding_isp_registration",
                "ordering": ["-created_at"],
                "indexes": [models.Index(fields=["status", "created_at"], name="onboard_status_created_idx")],
            },
        ),
    ]
