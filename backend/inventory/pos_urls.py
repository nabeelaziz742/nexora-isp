from django.urls import path

from inventory.views import (
    PosCatalogListView,
    PosSaleCancelView,
    PosSaleDetailView,
    PosSaleListView,
)


urlpatterns = [
    path(
        "catalog/",
        PosCatalogListView.as_view(),
        name="pos-catalog-list",
    ),
    path(
        "sales/",
        PosSaleListView.as_view(),
        name="pos-sale-list",
    ),
    path(
        "sales/<uuid:sale_id>/",
        PosSaleDetailView.as_view(),
        name="pos-sale-detail",
    ),
    path(
        "sales/<uuid:sale_id>/cancel/",
        PosSaleCancelView.as_view(),
        name="pos-sale-cancel",
    ),
]
