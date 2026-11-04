from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from customers.models import Inquiry, InternetPackage
from customers.services import InquiryDomainError, create_public_inquiry
from tenancy.models import Organization


class PublicInquiryThrottle(ScopedRateThrottle):
    """Limit public connection requests per IP; reading the form is not limited."""

    scope = "public_inquiry"

    def __init__(self):
        super().__init__()
        self.scope = "public_inquiry"

    def allow_request(self, request, view):
        if request.method != "POST":
            return True
        return super().allow_request(request, view)


class PublicInquirySerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    phone = serializers.RegexField(r"^\+?[0-9\- ]{10,15}$", max_length=30)
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    address_line = serializers.CharField(max_length=500)
    city = serializers.CharField(max_length=100)
    area = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    preferred_package = serializers.UUIDField(required=False, allow_null=True, default=None)
    connection_type = serializers.ChoiceField(
        choices=Inquiry.ConnectionType.choices,
        required=False,
        default=Inquiry.ConnectionType.FIBER,
    )
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    # Honeypot: hidden in the form, so only bots fill it in.
    website = serializers.CharField(required=False, allow_blank=True, default="")


def _get_public_organization(organization_code):
    return Organization.objects.filter(code__iexact=organization_code, is_active=True).first()


class PublicInquiryView(APIView):
    """Public 'apply for a connection' form for one ISP, reachable without login."""

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [PublicInquiryThrottle]
    throttle_scope = "public_inquiry"

    def get(self, request, organization_code):
        organization = _get_public_organization(organization_code)
        if organization is None:
            return Response({"detail": "ISP not found."}, status=status.HTTP_404_NOT_FOUND)

        packages = (
            InternetPackage.objects
            .for_organization(organization)
            .filter(is_active=True)
            .order_by("monthly_price", "name")
        )

        return Response({
            "organization": {
                "name": organization.name,
                "city": organization.city,
                "phone": organization.phone,
            },
            "packages": [
                {
                    "id": str(package.id),
                    "name": package.name,
                    "download_speed_mbps": package.download_speed_mbps,
                    "upload_speed_mbps": package.upload_speed_mbps,
                    "monthly_price": str(package.monthly_price),
                }
                for package in packages
            ],
            "connection_types": [
                {"value": value, "label": label}
                for value, label in Inquiry.ConnectionType.choices
            ],
        })

    def post(self, request, organization_code):
        organization = _get_public_organization(organization_code)
        if organization is None:
            return Response({"detail": "ISP not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = PublicInquirySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        success = {
            "detail": "Thank you. We have received your request and will contact you shortly.",
        }

        if data["website"].strip():
            # Pretend success so bots get no signal.
            return Response(success, status=status.HTTP_201_CREATED)

        try:
            result = create_public_inquiry(
                organization=organization,
                full_name=data["full_name"],
                phone=data["phone"],
                email=data["email"],
                address_line=data["address_line"],
                city=data["city"],
                area=data["area"],
                preferred_package_id=data["preferred_package"],
                connection_type=data["connection_type"],
                notes=data["notes"],
            )
        except InquiryDomainError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {**success, "reference": result.inquiry.inquiry_number},
            status=status.HTTP_201_CREATED,
        )
