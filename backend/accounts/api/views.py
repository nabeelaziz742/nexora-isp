from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.api.serializers import TenantLoginSerializer


class TenantLoginAPIView(APIView):
    permission_classes = [AllowAny]

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