from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.models import Customer, InternetPackage
from customers.serializers import (
    CustomerActivationSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    InternetPackageSerializer,
)
from customers.services import (
    CustomerActivationError,
    activate_customer_service,
)
from tenancy.permissions import IsOrganizationStaffOrOwner


class CustomerListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        customers = (
            Customer.objects
            .for_organization(request.organization)
            .prefetch_related(
                "service_accounts__internet_package"
            )
        )

        search = request.query_params.get("search", "").strip()
        service_status = request.query_params.get(
            "status",
            "",
        ).strip()

        if search:
            customers = customers.filter(
                Q(customer_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
            )

        if service_status:
            customers = customers.filter(
                service_accounts__status=service_status
            )

        customers = customers.distinct().order_by(
            "-created_at"
        )

        serializer = CustomerListSerializer(
            customers,
            many=True,
        )

        return Response(serializer.data)


class CustomerDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, customer_id):
        try:
            customer = (
                Customer.objects
                .for_organization(request.organization)
                .prefetch_related(
                    "service_accounts__internet_package",
                    "service_accounts__billing_profile",
                    "service_accounts__network_assignment__network_node",
                    "service_accounts__device_assignments__device",
                )
                .select_related(
                    "notification_preference"
                )
                .get(id=customer_id)
            )
        except Customer.DoesNotExist as exc:
            raise NotFound(
                "Customer was not found in this organization."
            ) from exc

        serializer = CustomerDetailSerializer(customer)

        return Response(serializer.data)


class CustomerActivationView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request):
        serializer = CustomerActivationSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            result = activate_customer_service(
                organization=request.organization,
                actor=request.user,
                **serializer.validated_data,
            )
        except CustomerActivationError as exc:
            return Response(
                {
                    "detail": str(exc),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        device_assignment = None

        if result.device_assignment is not None:
            device_assignment = {
                "id": str(result.device_assignment.id),
                "device_id": str(
                    result.device_assignment.device_id
                ),
                "asset_tag": (
                    result.device_assignment.device.asset_tag
                ),
                "device_type": (
                    result.device_assignment.device.device_type
                ),
                "device_status": (
                    result.device_assignment.device.status
                ),
            }

        return Response(
            {
                "detail": "CUSTOMER SERVICE ACTIVATION REQUESTED",
                "customer": {
                    "id": str(result.customer.id),
                    "customer_number": (
                        result.customer.customer_number
                    ),
                    "full_name": result.customer.full_name,
                    "phone": result.customer.phone,
                },
                "service_account": {
                    "id": str(result.service_account.id),
                    "service_number": (
                        result.service_account.service_number
                    ),
                    "status": result.service_account.status,
                    "internet_package_id": str(
                        result.service_account.internet_package_id
                    ),
                },
                "network_assignment": {
                    "id": str(result.network_assignment.id),
                    "network_node_id": str(
                        result.network_assignment.network_node_id
                    ),
                    "username": (
                        result.network_assignment.username
                    ),
                    "ip_address": (
                        result.network_assignment.ip_address
                    ),
                },
                "provisioning_request": {
                    "id": str(result.provisioning_request.id),
                    "action": result.provisioning_request.action,
                    "status": result.provisioning_request.status,
                },
                "device_assignment": device_assignment,
            },
            status=status.HTTP_201_CREATED,
        )


class InternetPackageListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        packages = (
            InternetPackage.objects
            .for_organization(request.organization)
            .filter(is_active=True)
            .order_by("monthly_price", "name")
        )

        serializer = InternetPackageSerializer(
            packages,
            many=True,
        )

        return Response(serializer.data)