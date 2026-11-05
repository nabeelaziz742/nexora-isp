from django.http import HttpResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from customers.import_services import (
    CustomerImportError,
    build_import_template,
    import_customers,
    parse_import_file,
    validate_import_rows,
)
from customers.models import CustomerImportBatch
from tenancy.permissions import CanImportCustomers

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _batch_data(batch):
    actor = batch.created_by
    return {
        "id": str(batch.id),
        "file_name": batch.file_name,
        "total_rows": batch.total_rows,
        "imported_count": batch.imported_count,
        "skipped_count": batch.skipped_count,
        "create_on_router": batch.create_on_router,
        "errors": batch.errors,
        "created_by_name": (actor.get_full_name() or actor.email) if actor else "",
        "created_at": batch.created_at,
    }


class CustomerImportTemplateView(APIView):
    permission_classes = [CanImportCustomers]

    def get(self, request):
        content = build_import_template(organization=request.organization)
        response = HttpResponse(content, content_type=XLSX_CONTENT_TYPE)
        response["Content-Disposition"] = 'attachment; filename="nexora_customer_import_template.xlsx"'
        return response


class CustomerImportPreviewView(APIView):
    """Check a file without saving anything."""

    permission_classes = [CanImportCustomers]
    parser_classes = [MultiPartParser]

    def post(self, request):
        try:
            rows = parse_import_file(request.FILES.get("file"))
        except CustomerImportError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        validated = validate_import_rows(organization=request.organization, rows=rows)
        valid_count = sum(1 for item in validated if item.is_valid)

        return Response({
            "total_rows": len(validated),
            "valid_count": valid_count,
            "invalid_count": len(validated) - valid_count,
            "rows": [
                {
                    "row": item.row,
                    "valid": item.is_valid,
                    "errors": item.errors,
                    "values": item.values,
                }
                for item in validated
            ],
        })


class CustomerImportView(APIView):
    """Import the valid rows of a file; invalid rows are skipped and reported."""

    permission_classes = [CanImportCustomers]
    parser_classes = [MultiPartParser]

    def post(self, request):
        create_on_router = str(request.data.get("create_on_router", "")).lower() in {"1", "true", "yes", "on"}
        try:
            result = import_customers(
                organization=request.organization,
                actor=request.user,
                uploaded_file=request.FILES.get("file"),
                create_on_router=create_on_router,
            )
        except CustomerImportError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(_batch_data(result.batch), status=status.HTTP_201_CREATED)


class CustomerImportHistoryView(APIView):
    permission_classes = [CanImportCustomers]

    def get(self, request):
        batches = (
            CustomerImportBatch.objects
            .for_organization(request.organization)
            .select_related("created_by")[:50]
        )
        return Response([_batch_data(batch) for batch in batches])
