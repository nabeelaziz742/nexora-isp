from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.http import FileResponse
from rest_framework import permissions, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from onboarding.models import ISPRegistration, PaymentSettings
from onboarding.serializers import (
    ISPRegistrationSerializer,
    PaymentSettingsSerializer,
    ReceiptUploadSerializer,
    RegistrationListSerializer,
    RejectRegistrationSerializer,
)
from onboarding.services import approve_registration, create_registration, reject_registration, submit_receipt


User = get_user_model()


class IsSuperAdmin(permissions.BasePermission):
    message = "Super administrator access is required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_superuser)


class ISPRegistrationAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = ISPRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration, settings = create_registration(validated_data=serializer.validated_data)
        return Response({
            "registration_id": str(registration.id),
            "access_token": str(registration.access_token),
            "status": registration.status,
            "organization_code": registration.organization.code,
            "amount_due": registration.amount_due,
            "payment": PaymentSettingsSerializer(settings).data,
        }, status=status.HTTP_201_CREATED)


class RegistrationStatusAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, access_token):
        registration = ISPRegistration.objects.select_related("organization", "owner").filter(access_token=access_token).first()
        if registration is None:
            return Response({"detail": "Registration not found."}, status=status.HTTP_404_NOT_FOUND)
        payment = PaymentSettings.objects.filter(is_active=True).order_by("-updated_at").first()
        payload = RegistrationListSerializer(registration, context={"request": request}).data
        payload["payment"] = PaymentSettingsSerializer(payment).data if payment else None
        return Response(payload)


class RegistrationReceiptAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, access_token):
        registration = ISPRegistration.objects.filter(access_token=access_token).first()
        if registration is None:
            return Response({"detail": "Registration not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ReceiptUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = submit_receipt(registration=registration, receipt=serializer.validated_data["receipt"])
        return Response({"status": registration.status}, status=status.HTTP_200_OK)


class SuperAdminLoginAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = str(request.data.get("email", "")).strip().lower()
        password = request.data.get("password", "")
        user = authenticate(request=request, email=email, password=password)
        if user is None or not user.is_active or not user.is_superuser:
            return Response({"detail": "Invalid administrator credentials."}, status=status.HTTP_401_UNAUTHORIZED)
        refresh = RefreshToken.for_user(user)
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {"id": str(user.id), "email": user.email, "first_name": user.first_name, "last_name": user.last_name},
        })


class SuperAdminPaymentSettingsAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        settings = PaymentSettings.objects.filter(is_active=True).order_by("-updated_at").first()
        return Response(PaymentSettingsSerializer(settings).data if settings else None)

    def put(self, request):
        settings = PaymentSettings.objects.filter(is_active=True).order_by("-updated_at").first()
        serializer = PaymentSettingsSerializer(instance=settings, data=request.data) if settings else PaymentSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        settings = serializer.save(is_active=True)
        return Response(PaymentSettingsSerializer(settings).data)


class SuperAdminRegistrationListAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        status_filter = request.query_params.get("status")
        queryset = ISPRegistration.objects.select_related("organization", "owner", "verified_by")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return Response(RegistrationListSerializer(queryset, many=True, context={"request": request}).data)


class SuperAdminReceiptAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    def get(self, request, registration_id):
        registration = ISPRegistration.objects.filter(id=registration_id).first()
        if registration is None or not registration.receipt:
            return Response({"detail": "Receipt not found."}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(registration.receipt.open("rb"), content_type="image/*")


class SuperAdminRegistrationDetailAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperAdmin]

    @transaction.atomic
    def post(self, request, registration_id, action):
        registration = ISPRegistration.objects.select_related("organization", "owner", "verified_by").filter(id=registration_id).first()
        if registration is None:
            return Response({"detail": "Registration not found."}, status=status.HTTP_404_NOT_FOUND)
        if action == "approve":
            registration = approve_registration(registration=registration, admin_user=request.user)
            send_mail(
                subject="Nexora ISP account activated",
                message=(f"Your Nexora ISP account for {registration.organization.name} has been activated. "
                         f"Your organization code is {registration.organization.code}."),
                from_email=None,
                recipient_list=[registration.owner.email],
                fail_silently=True,
            )
        elif action == "reject":
            serializer = RejectRegistrationSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            registration = reject_registration(registration=registration, reason=serializer.validated_data.get("reason", ""))
        else:
            return Response({"detail": "Unsupported action."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(RegistrationListSerializer(registration, context={"request": request}).data)
