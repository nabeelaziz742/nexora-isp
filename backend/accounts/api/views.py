from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.api.serializers import TenantLoginSerializer


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

        response = Response(
            serializer.validated_data,
            status=status.HTTP_200_OK,
        )

        # A successful login proves the credentials are valid. Reset only
        # this request's throttle bucket so previous failed attempts do not
        # penalize the legitimate user on subsequent logins.
        throttle = ScopedRateThrottle()
        throttle.scope = self.throttle_scope
        cache_key = throttle.get_cache_key(request, self)
        if cache_key:
            throttle.cache.delete(cache_key)

        return response


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
