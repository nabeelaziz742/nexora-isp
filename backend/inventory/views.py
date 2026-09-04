from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Prefetch, Q
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import (
    DeviceAssignment,
    InventoryDevice,
    InventoryItem,
    PosSale,
    PosSaleItem,
    StockMovement,
)
from inventory.serializers import (
    AssignDeviceSerializer,
    CancelPosSaleSerializer,
    CreatePosSaleSerializer,
    DamageStockSerializer,
    DeviceAssignmentSerializer,
    DisposeStockSerializer,
    InventoryDeviceSerializer,
    InventoryItemSerializer,
    PosSaleSerializer,
    RestockSerializer,
    ReturnDeviceSerializer,
    StockAdjustmentSerializer,
    StockMovementSerializer,
)
from inventory.services import (
    InventoryCustodyError,
    InventoryDomainError,
    PosSaleError,
    assign_device_to_service,
    cancel_pos_sale,
    create_pos_sale,
    dispose_damaged_stock,
    mark_stock_as_damaged,
    record_stock_adjustment,
    record_stock_restock,
    return_device_from_service,
)
from tenancy.permissions import (
    CanAdjustInventory,
    CanCancelPosSale,
    CanManageInventory,
    CanManagePos,
    HasActiveTenantContext,
    IsOrganizationStaffOrOwner,
)


# ==============================================================================
# SERIALIZED CPE DEVICE VIEWS (PRESERVED)
# ==============================================================================

def _device_queryset_for_organization(organization):
    active_assignments = (
        DeviceAssignment.objects
        .for_organization(organization)
        .filter(returned_at__isnull=True)
        .select_related(
            "service_account",
            "service_account__customer",
        )
    )

    return (
        InventoryDevice.objects
        .for_organization(organization)
        .prefetch_related(
            Prefetch(
                "assignments",
                queryset=active_assignments,
                to_attr="active_assignments",
            )
        )
    )


class InventoryDeviceListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        devices = _device_queryset_for_organization(request.organization)

        device_status = request.query_params.get("status", "").strip()
        device_type = request.query_params.get("type", "").strip()
        search = request.query_params.get("search", "").strip()

        if device_status:
            devices = devices.filter(status=device_status)

        if device_type:
            devices = devices.filter(device_type=device_type)

        if search:
            devices = devices.filter(
                Q(asset_tag__icontains=search)
                | Q(manufacturer__icontains=search)
                | Q(model_name__icontains=search)
                | Q(serial_number__icontains=search)
                | Q(mac_address__icontains=search)
            )

        devices = devices.order_by("asset_tag")
        serializer = InventoryDeviceSerializer(devices, many=True)
        return Response(serializer.data)


class InventoryDeviceDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, device_id):
        try:
            device = (
                _device_queryset_for_organization(request.organization)
                .get(id=device_id)
            )
        except InventoryDevice.DoesNotExist as exc:
            raise NotFound("Device was not found for this organization.") from exc

        serializer = InventoryDeviceSerializer(device)
        return Response(serializer.data)


class DeviceAssignmentListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        assignments = (
            DeviceAssignment.objects
            .for_organization(request.organization)
            .select_related(
                "device",
                "service_account",
                "service_account__customer",
                "assigned_by",
                "returned_by",
            )
        )

        is_active = request.query_params.get("active", "").strip().lower()
        search = request.query_params.get("search", "").strip()

        if is_active == "true":
            assignments = assignments.filter(returned_at__isnull=True)
        elif is_active == "false":
            assignments = assignments.filter(returned_at__isnull=False)

        if search:
            assignments = assignments.filter(
                Q(device__asset_tag__icontains=search)
                | Q(device__serial_number__icontains=search)
                | Q(device__mac_address__icontains=search)
                | Q(service_account__service_number__icontains=search)
                | Q(service_account__customer__full_name__icontains=search)
                | Q(service_account__customer__customer_number__icontains=search)
            )

        assignments = assignments.order_by("-assigned_at")
        serializer = DeviceAssignmentSerializer(assignments, many=True)
        return Response(serializer.data)


class AssignDeviceView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request):
        input_serializer = AssignDeviceSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        try:
            result = assign_device_to_service(
                organization=request.organization,
                actor=request.user,
                device_id=input_serializer.validated_data["device_id"],
                service_account_id=input_serializer.validated_data["service_account_id"],
                assignment_notes=input_serializer.validated_data["assignment_notes"],
            )
        except InventoryCustodyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        assignment = (
            DeviceAssignment.objects
            .for_organization(request.organization)
            .select_related(
                "device",
                "service_account",
                "service_account__customer",
                "assigned_by",
                "returned_by",
            )
            .get(id=result.assignment.id)
        )

        serializer = DeviceAssignmentSerializer(assignment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ReturnDeviceView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, assignment_id):
        input_serializer = ReturnDeviceSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        try:
            result = return_device_from_service(
                organization=request.organization,
                actor=request.user,
                assignment_id=assignment_id,
                return_condition=input_serializer.validated_data["return_condition"],
                return_notes=input_serializer.validated_data["return_notes"],
            )
        except InventoryCustodyError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        assignment = (
            DeviceAssignment.objects
            .for_organization(request.organization)
            .select_related(
                "device",
                "service_account",
                "service_account__customer",
                "assigned_by",
                "returned_by",
            )
            .get(id=result.assignment.id)
        )

        serializer = DeviceAssignmentSerializer(assignment)
        return Response(serializer.data)


# ==============================================================================
# INVENTORY ITEM & STOCK VIEWS
# ==============================================================================

class InventoryItemListView(APIView):
    permission_classes = [CanManageInventory]

    def get(self, request):
        items = InventoryItem.objects.for_organization(request.organization)

        category = request.query_params.get("category", "").strip()
        search = request.query_params.get("search", "").strip()
        low_stock = request.query_params.get("low_stock", "").strip().lower()
        is_active = request.query_params.get("is_active", "").strip().lower()

        if category:
            items = items.filter(category=category)

        if is_active == "true":
            items = items.filter(is_active=True)
        elif is_active == "false":
            items = items.filter(is_active=False)

        if low_stock == "true":
            items = items.filter(quantity_on_hand__lte=F("reorder_threshold"))

        if search:
            items = items.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(notes__icontains=search)
            )

        items = items.order_by("name")

        page_num = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        paginator = Paginator(items, page_size)
        page_obj = paginator.get_page(page_num)

        serializer = InventoryItemSerializer(page_obj.object_list, many=True)
        return Response({
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "results": serializer.data,
        })

    def post(self, request):
        serializer = InventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"].strip().upper()
        if InventoryItem.objects.for_organization(request.organization).filter(code=code).exists():
            return Response(
                {"detail": f"An item with SKU code '{code}' already exists in this organization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = serializer.save(
            organization=request.organization,
            code=code,
        )

        return Response(
            InventoryItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class InventoryItemDetailView(APIView):
    permission_classes = [CanManageInventory]

    def get(self, request, item_id):
        try:
            item = InventoryItem.objects.for_organization(request.organization).get(id=item_id)
        except InventoryItem.DoesNotExist as exc:
            raise NotFound("Inventory item was not found.") from exc

        return Response(InventoryItemSerializer(item).data)

    def patch(self, request, item_id):
        try:
            item = InventoryItem.objects.for_organization(request.organization).get(id=item_id)
        except InventoryItem.DoesNotExist as exc:
            raise NotFound("Inventory item was not found.") from exc

        serializer = InventoryItemSerializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if "code" in serializer.validated_data:
            code = serializer.validated_data["code"].strip().upper()
            if (
                InventoryItem.objects.for_organization(request.organization)
                .filter(code=code)
                .exclude(id=item.id)
                .exists()
            ):
                return Response(
                    {"detail": f"An item with SKU code '{code}' already exists in this organization."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.validated_data["code"] = code

        updated_item = serializer.save()
        return Response(InventoryItemSerializer(updated_item).data)


class InventoryItemRestockView(APIView):
    permission_classes = [CanManageInventory]

    def post(self, request, item_id):
        serializer = RestockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = record_stock_restock(
                organization=request.organization,
                actor=request.user,
                item_id=item_id,
                quantity=serializer.validated_data["quantity"],
                unit_cost=serializer.validated_data.get("unit_cost"),
                notes=serializer.validated_data.get("notes", ""),
            )
        except InventoryDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InventoryItemSerializer(item).data)


class InventoryItemAdjustmentView(APIView):
    permission_classes = [CanAdjustInventory]

    def post(self, request, item_id):
        serializer = StockAdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = record_stock_adjustment(
                organization=request.organization,
                actor=request.user,
                item_id=item_id,
                new_quantity=serializer.validated_data["new_quantity"],
                reason=serializer.validated_data.get("reason", "Manual Adjustment"),
                notes=serializer.validated_data.get("notes", ""),
            )
        except InventoryDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InventoryItemSerializer(item).data)


class InventoryItemDamageView(APIView):
    permission_classes = [CanAdjustInventory]

    def post(self, request, item_id):
        serializer = DamageStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = mark_stock_as_damaged(
                organization=request.organization,
                actor=request.user,
                item_id=item_id,
                quantity=serializer.validated_data["quantity"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except InventoryDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InventoryItemSerializer(item).data)


class InventoryItemDisposeView(APIView):
    permission_classes = [CanAdjustInventory]

    def post(self, request, item_id):
        serializer = DisposeStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = dispose_damaged_stock(
                organization=request.organization,
                actor=request.user,
                item_id=item_id,
                quantity=serializer.validated_data["quantity"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except InventoryDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(InventoryItemSerializer(item).data)


class StockMovementListView(APIView):
    permission_classes = [CanManageInventory]

    def get(self, request):
        movements = (
            StockMovement.objects
            .for_organization(request.organization)
            .select_related("item", "created_by")
        )

        item_id = request.query_params.get("item_id", "").strip()
        movement_type = request.query_params.get("movement_type", "").strip()
        search = request.query_params.get("search", "").strip()

        if item_id:
            movements = movements.filter(item_id=item_id)

        if movement_type:
            movements = movements.filter(movement_type=movement_type)

        if search:
            movements = movements.filter(
                Q(item__name__icontains=search)
                | Q(item__code__icontains=search)
                | Q(reference_id__icontains=search)
                | Q(notes__icontains=search)
            )

        movements = movements.order_by("-created_at")

        page_num = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        paginator = Paginator(movements, page_size)
        page_obj = paginator.get_page(page_num)

        serializer = StockMovementSerializer(page_obj.object_list, many=True)
        return Response({
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "results": serializer.data,
        })


# ==============================================================================
# POS & HARDWARE SALES VIEWS
# ==============================================================================

class PosCatalogListView(APIView):
    permission_classes = [CanManagePos]

    def get(self, request):
        items = (
            InventoryItem.objects
            .for_organization(request.organization)
            .filter(is_active=True)
            .order_by("name")
        )

        category = request.query_params.get("category", "").strip()
        search = request.query_params.get("search", "").strip()

        if category:
            items = items.filter(category=category)

        if search:
            items = items.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
            )

        serializer = InventoryItemSerializer(items, many=True)
        return Response(serializer.data)


class PosSaleListView(APIView):
    permission_classes = [CanManagePos]

    def get(self, request):
        sales = (
            PosSale.objects
            .for_organization(request.organization)
            .select_related("customer", "sold_by", "cancelled_by", "journal_entry")
            .prefetch_related("items", "items__item", "items__device")
        )

        customer_id = request.query_params.get("customer_id", "").strip()
        status_filter = request.query_params.get("status", "").strip()
        payment_method = request.query_params.get("payment_method", "").strip()
        start_date = request.query_params.get("start_date", "").strip()
        end_date = request.query_params.get("end_date", "").strip()
        search = request.query_params.get("search", "").strip()

        if customer_id:
            sales = sales.filter(customer_id=customer_id)

        if status_filter:
            sales = sales.filter(status=status_filter)

        if payment_method:
            sales = sales.filter(payment_method=payment_method)

        if start_date:
            sales = sales.filter(sale_date__gte=start_date)

        if end_date:
            sales = sales.filter(sale_date__lte=end_date)

        if search:
            sales = sales.filter(
                Q(sale_number__icontains=search)
                | Q(customer__full_name__icontains=search)
                | Q(customer__phone__icontains=search)
                | Q(walk_in_customer_name__icontains=search)
                | Q(walk_in_customer_phone__icontains=search)
                | Q(payment_reference__icontains=search)
            )

        sales = sales.order_by("-sale_date", "-created_at")

        page_num = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        paginator = Paginator(sales, page_size)
        page_obj = paginator.get_page(page_num)

        serializer = PosSaleSerializer(page_obj.object_list, many=True)
        return Response({
            "count": paginator.count,
            "total_pages": paginator.num_pages,
            "current_page": page_obj.number,
            "results": serializer.data,
        })

    def post(self, request):
        serializer = CreatePosSaleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sale = create_pos_sale(
                organization=request.organization,
                actor=request.user,
                customer_id=serializer.validated_data.get("customer_id"),
                walk_in_customer_name=serializer.validated_data.get("walk_in_customer_name", ""),
                walk_in_customer_phone=serializer.validated_data.get("walk_in_customer_phone", ""),
                sale_date=serializer.validated_data.get("sale_date"),
                items=serializer.validated_data["items"],
                payment_method=serializer.validated_data.get("payment_method", PosSale.PaymentMethod.CASH),
                payment_reference=serializer.validated_data.get("payment_reference", ""),
                discount_amount=serializer.validated_data.get("discount_amount", Decimal("0.00")),
                tax_amount=serializer.validated_data.get("tax_amount", Decimal("0.00")),
                notes=serializer.validated_data.get("notes", ""),
            )
        except PosSaleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # Reload with relationships
        reloaded = (
            PosSale.objects
            .for_organization(request.organization)
            .select_related("customer", "sold_by", "cancelled_by", "journal_entry")
            .prefetch_related("items", "items__item", "items__device")
            .get(id=sale.id)
        )

        return Response(PosSaleSerializer(reloaded).data, status=status.HTTP_201_CREATED)


class PosSaleDetailView(APIView):
    permission_classes = [CanManagePos]

    def get(self, request, sale_id):
        try:
            sale = (
                PosSale.objects
                .for_organization(request.organization)
                .select_related("customer", "sold_by", "cancelled_by", "journal_entry")
                .prefetch_related("items", "items__item", "items__device")
                .get(id=sale_id)
            )
        except PosSale.DoesNotExist as exc:
            raise NotFound("POS Sale was not found.") from exc

        return Response(PosSaleSerializer(sale).data)


class PosSaleCancelView(APIView):
    permission_classes = [CanCancelPosSale]

    def post(self, request, sale_id):
        serializer = CancelPosSaleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sale = cancel_pos_sale(
                organization=request.organization,
                actor=request.user,
                sale_id=sale_id,
                cancellation_reason=serializer.validated_data["cancellation_reason"],
            )
        except PosSaleError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        reloaded = (
            PosSale.objects
            .for_organization(request.organization)
            .select_related("customer", "sold_by", "cancelled_by", "journal_entry")
            .prefetch_related("items", "items__item", "items__device")
            .get(id=sale.id)
        )

        return Response(PosSaleSerializer(reloaded).data)