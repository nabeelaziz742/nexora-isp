import re

from django.db import migrations


def _next_staff_code(StaffProfile, organization):
    """Mirror tenancy.staff_services.generate_staff_code using historical models."""
    prefix = f"{organization.code.upper()}-STF-"
    last_profile = (
        StaffProfile.objects.filter(
            organization=organization,
            staff_code__startswith=prefix,
        )
        .order_by("-staff_code")
        .first()
    )

    if not last_profile:
        return f"{prefix}0001"

    match = re.search(r"(\d+)$", last_profile.staff_code)
    if match:
        return f"{prefix}{int(match.group(1)) + 1:04d}"

    count = StaffProfile.objects.filter(organization=organization).count() + 1
    return f"{prefix}{count:04d}"


def backfill_missing_staff_profiles(apps, schema_editor):
    """
    Memberships created before HR (notably onboarded ISP owners) have no StaffProfile,
    which blocks them from attendance and leave APIs.
    """
    OrganizationMembership = apps.get_model("tenancy", "OrganizationMembership")
    StaffProfile = apps.get_model("tenancy", "StaffProfile")

    memberships = (
        OrganizationMembership.objects.filter(profile__isnull=True)
        .select_related("organization", "user")
        .order_by("created_at")
    )

    for membership in memberships:
        if membership.role == "OWNER":
            role = "OWNER"
        elif membership.role == "TECHNICIAN":
            role = "TECHNICIAN"
        else:
            role = "STAFF"

        StaffProfile.objects.create(
            organization=membership.organization,
            membership=membership,
            user=membership.user,
            staff_code=_next_staff_code(StaffProfile, membership.organization),
            role=role,
            status="ACTIVE" if membership.is_active else "INACTIVE",
        )


class Migration(migrations.Migration):

    dependencies = [
        ("hr", "0001_initial"),
        ("tenancy", "0004_staffprofile"),
    ]

    operations = [
        migrations.RunPython(
            backfill_missing_staff_profiles,
            migrations.RunPython.noop,
        ),
    ]
