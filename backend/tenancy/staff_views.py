from rest_framework.response import Response
from rest_framework.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
)
from rest_framework.views import APIView

from tenancy.models import OrganizationMembership
from tenancy.permissions import IsOrganizationOwner
from tenancy.staff_serializers import (
    CreateOrganizationStaffSerializer,
    OrganizationStaffSerializer,
    StaffActiveStateSerializer,
    UpdateOrganizationStaffSerializer,
)
from tenancy.staff_services import (
    create_organization_staff,
    set_organization_staff_active_state,
    update_organization_staff,
)


class OrganizationStaffListCreateView(APIView):
    permission_classes = [IsOrganizationOwner]

    def get(self, request):
        memberships = (
            OrganizationMembership.objects
            .filter(
                organization=request.organization,
            )
            .select_related("user")
            .order_by(
                "role",
                "user__first_name",
                "user__last_name",
            )
        )

        serializer = OrganizationStaffSerializer(
            memberships,
            many=True,
        )

        return Response(
            serializer.data,
            status=HTTP_200_OK,
        )

    def post(self, request):
        serializer = CreateOrganizationStaffSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        membership = create_organization_staff(
            organization=request.organization,
            actor=request.user,
            **serializer.validated_data,
        )

        response_serializer = OrganizationStaffSerializer(
            membership,
        )

        return Response(
            response_serializer.data,
            status=HTTP_201_CREATED,
        )


class OrganizationStaffDetailView(APIView):
    permission_classes = [IsOrganizationOwner]

    def get_membership(self, request, membership_id):
        return (
            OrganizationMembership.objects
            .filter(
                organization=request.organization,
                id=membership_id,
            )
            .select_related("user")
            .get()
        )

    def get(self, request, membership_id):
        membership = self.get_membership(
            request,
            membership_id,
        )

        serializer = OrganizationStaffSerializer(
            membership,
        )

        return Response(
            serializer.data,
            status=HTTP_200_OK,
        )

    def patch(self, request, membership_id):
        membership = self.get_membership(
            request,
            membership_id,
        )

        serializer = UpdateOrganizationStaffSerializer(
            data=request.data,
            partial=True,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        membership = update_organization_staff(
            organization=request.organization,
            actor=request.user,
            membership=membership,
            **serializer.validated_data,
        )

        response_serializer = OrganizationStaffSerializer(
            membership,
        )

        return Response(
            response_serializer.data,
            status=HTTP_200_OK,
        )


class OrganizationStaffActiveStateView(APIView):
    permission_classes = [IsOrganizationOwner]

    def patch(self, request, membership_id):
        membership = (
            OrganizationMembership.objects
            .filter(
                organization=request.organization,
                id=membership_id,
            )
            .select_related("user")
            .get()
        )

        serializer = StaffActiveStateSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        membership = set_organization_staff_active_state(
            organization=request.organization,
            actor=request.user,
            membership=membership,
            is_active=serializer.validated_data["is_active"],
        )

        response_serializer = OrganizationStaffSerializer(
            membership,
        )

        return Response(
            response_serializer.data,
            status=HTTP_200_OK,
        )