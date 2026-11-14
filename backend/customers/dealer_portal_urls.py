from django.urls import path

from customers.dealer_cash import DealerCashView, DealerEmployeeCashReceivedView
from customers.dealer_employees import (
    DealerEmployeeDetailView,
    DealerEmployeeListView,
    DealerEmployeePasswordView,
)

from customers.dealer_portal import (
    DealerCollectionsView,
    DealerCollectPaymentView,
    DealerCustomerListView,
    DealerCustomerRequestView,
    DealerRechargeView,
    DealerSummaryView,
)

urlpatterns = [
    path("summary/", DealerSummaryView.as_view(), name="dealer-portal-summary"),
    path("customers/", DealerCustomerListView.as_view(), name="dealer-portal-customers"),
    path("services/<uuid:service_id>/payments/", DealerCollectPaymentView.as_view(), name="dealer-portal-payment"),
    path("services/<uuid:service_id>/recharge/", DealerRechargeView.as_view(), name="dealer-portal-recharge"),
    path("requests/", DealerCustomerRequestView.as_view(), name="dealer-portal-requests"),
    path("collections/", DealerCollectionsView.as_view(), name="dealer-portal-collections"),
    path("employees/", DealerEmployeeListView.as_view(), name="dealer-portal-employees"),
    path("employees/<uuid:employee_id>/", DealerEmployeeDetailView.as_view(), name="dealer-portal-employee"),
    path(
        "employees/<uuid:employee_id>/password/",
        DealerEmployeePasswordView.as_view(),
        name="dealer-portal-employee-password",
    ),
    path(
        "employees/<uuid:employee_id>/cash-received/",
        DealerEmployeeCashReceivedView.as_view(),
        name="dealer-portal-employee-cash-received",
    ),
    path("cash/", DealerCashView.as_view(), name="dealer-portal-cash"),
]
