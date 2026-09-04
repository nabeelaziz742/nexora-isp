from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.api.serializers import TenantLoginSerializer
from tenancy.services import record_audit_log


class TenantLoginAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        serializer = TenantLoginSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True,
        )

        if hasattr(serializer, "user") and hasattr(serializer, "membership"):
            user = serializer.user
            membership = serializer.membership
            record_audit_log(
                organization=membership.organization,
                actor=user,
                action="USER_LOGIN_SUCCESS",
                resource_type="User",
                resource_id=str(user.id),
                metadata={
                    "email": user.email,
                    "role": membership.role,
                },
            )

        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class CurrentSessionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        organization = request.organization

        return Response(
            {
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
                "organization": {
                    "id": str(organization.id),
                    "name": organization.name,
                    "code": organization.code,
                },
                "role": request.organization_role,
            },
            status=status.HTTP_200_OK,
        )


class TenantTokenRefreshAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        from accounts.api.serializers import TenantTokenRefreshSerializer

        serializer = TenantTokenRefreshSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        if hasattr(serializer, "user") and hasattr(serializer, "membership"):
            record_audit_log(
                organization=serializer.membership.organization,
                actor=serializer.user,
                action="TOKEN_REFRESH_SUCCESS",
                resource_type="User",
                resource_id=str(serializer.user.id),
                metadata={
                    "email": serializer.user.email,
                    "role": serializer.effective_role,
                },
            )

        return Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )


class LogoutAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        from accounts.api.serializers import LogoutSerializer

        serializer = LogoutSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Record audit log if authenticated tenant context exists
        user = getattr(request, "user", None)
        organization = getattr(request, "organization", None)
        if user and user.is_authenticated and organization:
            record_audit_log(
                organization=organization,
                actor=user,
                action="USER_LOGOUT_SUCCESS",
                resource_type="User",
                resource_id=str(user.id),
                metadata={
                    "email": user.email,
                },
            )

        return Response(
            {"detail": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )

