from django.db import models


class TenantScopedQuerySet(models.QuerySet):
    def for_organization(self, organization):
        return self.filter(organization=organization)


class TenantScopedManager(models.Manager):
    def get_queryset(self):
        return TenantScopedQuerySet(
            self.model,
            using=self._db,
        )

    def for_organization(self, organization):
        return self.get_queryset().for_organization(organization)


class TenantScopedModel(models.Model):
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s_records",
    )

    objects = TenantScopedManager()

    class Meta:
        abstract = True