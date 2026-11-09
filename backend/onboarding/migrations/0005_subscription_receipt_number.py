from django.db import migrations, models


def number_existing_payments(apps, schema_editor):
    Payment = apps.get_model("onboarding", "ISPSubscriptionPayment")
    for index, payment in enumerate(Payment.objects.order_by("created_at", "id"), start=1):
        payment.receipt_number = f"NXR-{index:06d}"
        payment.save(update_fields=["receipt_number"])


class Migration(migrations.Migration):

    dependencies = [
        ('onboarding', '0004_subscription_reminders'),
    ]

    operations = [
        migrations.AddField(
            model_name='ispsubscriptionpayment',
            name='receipt_number',
            field=models.CharField(blank=True, max_length=20, null=True, unique=True),
        ),
        migrations.RunPython(number_existing_payments, migrations.RunPython.noop),
    ]
