from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.views import APIView

from billing.models import Invoice, PromiseToPay, RecoveryAllocation
from billing.recovery_serializers import (
    RecoveryAllocationCreateSerializer,
    RecoveryAllocationReassignSerializer,
    RecoveryAllocationSerializer,
    RecoveryStatusTransitionSerializer,
)
from billing.recovery_services import (
    allocate_defaulter,
    get_defaulters_data,
    get_recovery_dashboard_metrics,
    reassign_recovery_allocation,
    transition_recovery_status,
)
from customers.models import Customer, ServiceAccount
from tenancy.models import OrganizationMembership
from tenancy.permissions import IsOrganizationOwner, IsOrganizationStaffOrOwner


User = get_user_model()


class DefaulterListView(APIView):
    """
    List real overdue accounts calculated directly from unpaid invoices.
    """
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        search = request.query_params.get("search", "").strip() or None
        city = request.query_params.get("city", "").strip() or None
        area = request.query_params.get("area", "").strip() or None
        aging_bucket = request.query_params.get("aging_bucket", "").strip() or None
        min_amount = request.query_params.get("min_amount", "").strip() or None
        has_alloc_param = request.query_params.get("has_active_allocation", "").strip().lower()

        has_active_alloc = None
        if has_alloc_param in ["true", "1"]:
            has_active_alloc = True
        elif has_alloc_param in ["false", "0"]:
            has_active_alloc = False

        data = get_defaulters_data(
            request.organization,
            search=search,
            city=city,
            area=area,
            aging_bucket=aging_bucket,
            min_amount=min_amount,
            has_active_allocation=has_active_alloc,
        )

        return Response(data, status=HTTP_200_OK)


class RecoveryAllocationListCreateView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        status_param = request.query_params.get("status", "").strip()
        operator_id = request.query_params.get("operator_id", "").strip()
        customer_id = request.query_params.get("customer_id", "").strip()
        priority = request.query_params.get("priority", "").strip()
        area = request.query_params.get("area", "").strip()
        search = request.query_params.get("search", "").strip()

        allocations = (
            RecoveryAllocation.objects.for_organization(request.organization)
            .select_related(
                "customer",
                "service_account",
                "invoice",
                "assigned_staff",
                "assigned_by",
                "reassigned_from",
                "linked_promise",
            )
            .order_by("-created_at")
        )

        if status_param:
            allocations = allocations.filter(status__iexact=status_param)

        if operator_id:
            allocations = allocations.filter(assigned_staff_id=operator_id)

        if customer_id:
            allocations = allocations.filter(customer_id=customer_id)

        if priority:
            allocations = allocations.filter(priority__iexact=priority)

        if area:
            allocations = allocations.filter(customer__area__iexact=area)

        if search:
            allocations = allocations.filter(
                Q(allocation_number__icontains=search)
                | Q(customer__full_name__icontains=search)
                | Q(customer__customer_number__icontains=search)
                | Q(customer__phone__icontains=search)
                | Q(service_account__service_number__icontains=search)
            )

        serializer = RecoveryAllocationSerializer(allocations, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    def post(self, request):
        serializer = RecoveryAllocationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        customer = Customer.objects.for_organization(request.organization).filter(
            id=serializer.validated_data["customer_id"]
        ).first()
        if not customer:
            raise NotFound({"customer": "Customer not found."})

        service_account = None
        sa_id = serializer.validated_data.get("service_account_id")
        if sa_id:
            service_account = ServiceAccount.objects.for_organization(request.organization).filter(id=sa_id).first()

        invoice = None
        inv_id = serializer.validated_data.get("invoice_id")
        if inv_id:
            invoice = Invoice.objects.for_organization(request.organization).filter(id=inv_id).first()

        assigned_staff = User.objects.filter(id=serializer.validated_data["assigned_staff_id"]).first()
        if not assigned_staff:
            raise NotFound({"assigned_staff": "Assigned staff not found."})

        allocation = allocate_defaulter(
            organization=request.organization,
            actor=request.user,
            customer=customer,
            assigned_staff=assigned_staff,
            service_account=service_account,
            invoice=invoice,
            outstanding_amount=serializer.validated_data.get("outstanding_amount"),
            due_date=serializer.validated_data.get("due_date"),
            priority=serializer.validated_data.get("priority", RecoveryAllocation.Priority.NORMAL),
            notes=serializer.validated_data.get("notes", ""),
        )

        return Response(RecoveryAllocationSerializer(allocation).data, status=HTTP_201_CREATED)


class RecoveryAllocationDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get_allocation(self, request, allocation_id):
        allocation = (
            RecoveryAllocation.objects.for_organization(request.organization)
            .filter(id=allocation_id)
            .select_related(
                "customer",
                "service_account",
                "invoice",
                "assigned_staff",
                "assigned_by",
                "reassigned_from",
                "linked_promise",
            )
            .first()
        )
        if not allocation:
            raise NotFound({"detail": "Recovery allocation not found."})
        return allocation

    def get(self, request, allocation_id):
        allocation = self.get_allocation(request, allocation_id)
        return Response(RecoveryAllocationSerializer(allocation).data, status=HTTP_200_OK)


class RecoveryAllocationReassignView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, allocation_id):
        allocation = (
            RecoveryAllocation.objects.for_organization(request.organization)
            .filter(id=allocation_id)
            .first()
        )
        if not allocation:
            raise NotFound({"detail": "Recovery allocation not found."})

        serializer = RecoveryAllocationReassignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_staff = User.objects.filter(id=serializer.validated_data["new_assigned_staff_id"]).first()
        if not new_staff:
            raise NotFound({"new_assigned_staff": "New assigned staff not found."})

        new_allocation = reassign_recovery_allocation(
            organization=request.organization,
            actor=request.user,
            allocation=allocation,
            new_assigned_staff=new_staff,
            reassignment_reason=serializer.validated_data["reassignment_reason"],
            due_date=serializer.validated_data.get("due_date"),
            priority=serializer.validated_data.get("priority"),
            notes=serializer.validated_data.get("notes"),
        )

        return Response(RecoveryAllocationSerializer(new_allocation).data, status=HTTP_201_CREATED)


class RecoveryAllocationStatusTransitionView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, allocation_id):
        allocation = (
            RecoveryAllocation.objects.for_organization(request.organization)
            .filter(id=allocation_id)
            .first()
        )
        if not allocation:
            raise NotFound({"detail": "Recovery allocation not found."})

        serializer = RecoveryStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        linked_promise = None
        lp_id = serializer.validated_data.get("linked_promise_id")
        if lp_id:
            linked_promise = PromiseToPay.objects.for_organization(request.organization).filter(id=lp_id).first()

        updated_allocation = transition_recovery_status(
            organization=request.organization,
            actor=request.user,
            allocation=allocation,
            new_status=serializer.validated_data["new_status"],
            notes=serializer.validated_data.get("notes"),
            linked_promise=linked_promise,
        )

        return Response(RecoveryAllocationSerializer(updated_allocation).data, status=HTTP_200_OK)


class RecoveryDashboardView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        is_manager = request.organization_role in [
            OrganizationMembership.Role.OWNER,
            OrganizationMembership.Role.STAFF,
        ]
        metrics = get_recovery_dashboard_metrics(
            request.organization,
            user=request.user,
            is_manager=is_manager,
        )
        return Response(metrics, status=HTTP_200_OK)
