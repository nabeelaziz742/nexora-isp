from decimal import Decimal

from django.db.models import Count, Q, Sum
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from billing.models import Invoice, Payment
from customers.models import (
    Customer,
    Dealer,
    FeasibilityAssessment,
    Inquiry,
    InternetPackage,
    ServiceAccount,
)
from customers.serializers import (
    CustomerActivationSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    CustomerUpdateSerializer,
    DealerSerializer,
    FeasibilityAssessmentCreateUpdateSerializer,
    FeasibilityAssessmentSerializer,
    InquiryConversionSerializer,
    InquiryCreateUpdateSerializer,
    InquirySerializer,
    InquiryStatusTransitionSerializer,
    InternetPackageSerializer,
)
from customers.services import (
    CustomerActivationError,
    DealerDomainError,
    FeasibilityDomainError,
    InquiryDomainError,
    activate_customer_service,
    convert_inquiry_to_customer,
    generate_dealer_code,
    generate_feasibility_number,
    generate_inquiry_number,
)
from tenancy.permissions import IsOrganizationStaffOrOwner
from tenancy.services import record_audit_log


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
        city = request.query_params.get("city", "").strip()
        area = request.query_params.get("area", "").strip()
        package_id = request.query_params.get("package_id", "").strip()
        is_active = request.query_params.get("is_active", "").strip()

        if search:
            customers = customers.filter(
                Q(customer_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
                | Q(address_line__icontains=search)
                | Q(service_accounts__service_number__icontains=search)
            )

        if service_status:
            customers = customers.filter(
                service_accounts__status=service_status
            )

        if city:
            customers = customers.filter(city__icontains=city)

        if area:
            customers = customers.filter(area__icontains=area)

        if package_id:
            customers = customers.filter(
                service_accounts__internet_package_id=package_id
            )

        if is_active.lower() == "true":
            customers = customers.filter(is_active=True)
        elif is_active.lower() == "false":
            customers = customers.filter(is_active=False)

        customers = customers.distinct().order_by(
            "-created_at"
        )

        from tenancy.pagination import StandardResultsSetPagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(customers, request)
        if page is not None:
            serializer = CustomerListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = CustomerListSerializer(
            customers,
            many=True,
        )

        return Response(serializer.data)


class CustomerDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def _get_customer(self, request, customer_id):
        try:
            return (
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

    def get(self, request, customer_id):
        customer = self._get_customer(request, customer_id)
        serializer = CustomerDetailSerializer(customer)
        return Response(serializer.data)

    def put(self, request, customer_id):
        customer = self._get_customer(request, customer_id)
        serializer = CustomerUpdateSerializer(
            customer,
            data=request.data,
            partial=False,
            context={"organization": request.organization},
        )
        serializer.is_valid(raise_exception=True)
        updated_customer = serializer.save()

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="CUSTOMER_UPDATED",
            resource_type="Customer",
            resource_id=updated_customer.id,
            metadata={
                "customer_number": updated_customer.customer_number,
                "updated_fields": list(serializer.validated_data.keys()),
            },
        )

        refreshed = self._get_customer(request, customer_id)
        return Response(CustomerDetailSerializer(refreshed).data)

    def patch(self, request, customer_id):
        customer = self._get_customer(request, customer_id)
        serializer = CustomerUpdateSerializer(
            customer,
            data=request.data,
            partial=True,
            context={"organization": request.organization},
        )
        serializer.is_valid(raise_exception=True)
        updated_customer = serializer.save()

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="CUSTOMER_UPDATED",
            resource_type="Customer",
            resource_id=updated_customer.id,
            metadata={
                "customer_number": updated_customer.customer_number,
                "updated_fields": list(serializer.validated_data.keys()),
            },
        )

        refreshed = self._get_customer(request, customer_id)
        return Response(CustomerDetailSerializer(refreshed).data)


class CustomerStatusToggleView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def patch(self, request, customer_id):
        customer = (
            Customer.objects
            .for_organization(request.organization)
            .filter(id=customer_id)
            .first()
        )
        if not customer:
            raise NotFound("Customer was not found in this organization.")

        customer.is_active = not customer.is_active
        customer.save(update_fields=["is_active", "updated_at"])

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="CUSTOMER_STATUS_TOGGLED",
            resource_type="Customer",
            resource_id=customer.id,
            metadata={
                "customer_number": customer.customer_number,
                "is_active": customer.is_active,
            },
        )

        refreshed = (
            Customer.objects
            .for_organization(request.organization)
            .prefetch_related(
                "service_accounts__internet_package",
                "service_accounts__billing_profile",
                "service_accounts__network_assignment__network_node",
                "service_accounts__device_assignments__device",
            )
            .select_related("notification_preference")
            .get(id=customer_id)
        )
        return Response(CustomerDetailSerializer(refreshed).data)



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


from customers.models import (
    Area,
    City,
    Country,
    Customer,
    InternetPackage,
    ServiceAccount,
)
from customers.serializers import (
    AreaSerializer,
    CitySerializer,
    CountrySerializer,
    CustomerActivationSerializer,
    CustomerDetailSerializer,
    CustomerListSerializer,
    InternetPackageCreateUpdateSerializer,
    InternetPackageSerializer,
)


class CountryListCreateView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        countries = Country.objects.for_organization(request.organization)

        search = request.query_params.get("search", "").strip()
        status_param = request.query_params.get("status", "").strip()

        if search:
            countries = countries.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )

        if status_param == "active":
            countries = countries.filter(is_active=True)
        elif status_param == "inactive":
            countries = countries.filter(is_active=False)

        serializer = CountrySerializer(countries.order_by("name"), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CountrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        country = serializer.save(organization=request.organization)
        return Response(CountrySerializer(country).data, status=status.HTTP_201_CREATED)


class CountryDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def _get_country(self, request, country_id):
        try:
            return Country.objects.for_organization(request.organization).get(id=country_id)
        except Country.DoesNotExist as exc:
            raise NotFound("Country was not found.") from exc

    def get(self, request, country_id):
        country = self._get_country(request, country_id)
        return Response(CountrySerializer(country).data)

    def put(self, request, country_id):
        country = self._get_country(request, country_id)
        serializer = CountrySerializer(country, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CountrySerializer(country).data)

    def patch(self, request, country_id):
        return self.put(request, country_id)

    def delete(self, request, country_id):
        country = self._get_country(request, country_id)
        cities_count = country.cities.count()
        if cities_count > 0:
            return Response(
                {
                    "detail": f"Cannot delete country '{country.name}' because {cities_count} city/cities are attached to it. Please remove or reassign the cities first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        country.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CountryStatusToggleView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def patch(self, request, country_id):
        country = Country.objects.for_organization(request.organization).filter(id=country_id).first()
        if not country:
            raise NotFound("Country was not found.")
        country.is_active = not country.is_active
        country.save(update_fields=["is_active", "updated_at"])
        return Response(CountrySerializer(country).data)


class CityListCreateView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        cities = City.objects.for_organization(request.organization).select_related("country")

        search = request.query_params.get("search", "").strip()
        country_id = request.query_params.get("country", "").strip()
        status_param = request.query_params.get("status", "").strip()

        if search:
            cities = cities.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )

        if country_id:
            cities = cities.filter(country_id=country_id)

        if status_param == "active":
            cities = cities.filter(is_active=True)
        elif status_param == "inactive":
            cities = cities.filter(is_active=False)

        serializer = CitySerializer(cities.order_by("name"), many=True)
        return Response(serializer.data)

    def post(self, request):
        country_id = request.data.get("country")
        country = None
        if country_id:
            try:
                country = Country.objects.for_organization(request.organization).get(id=country_id)
            except Country.DoesNotExist as exc:
                raise NotFound("Specified country was not found.") from exc

        serializer = CitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        city = serializer.save(organization=request.organization, country=country)
        return Response(CitySerializer(city).data, status=status.HTTP_201_CREATED)


class CityDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def _get_city(self, request, city_id):
        try:
            return City.objects.for_organization(request.organization).select_related("country").get(id=city_id)
        except City.DoesNotExist as exc:
            raise NotFound("City was not found.") from exc

    def get(self, request, city_id):
        city = self._get_city(request, city_id)
        return Response(CitySerializer(city).data)

    def put(self, request, city_id):
        city = self._get_city(request, city_id)
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        country = city.country
        if "country" in data:
            country_id = data.pop("country", None)
            if country_id:
                try:
                    country = Country.objects.for_organization(request.organization).get(id=country_id)
                except Country.DoesNotExist as exc:
                    raise NotFound("Specified country was not found.") from exc
            else:
                country = None

        serializer = CitySerializer(city, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(country=country)
        return Response(CitySerializer(city).data)

    def patch(self, request, city_id):
        return self.put(request, city_id)

    def delete(self, request, city_id):
        city = self._get_city(request, city_id)
        areas_count = city.areas.count()
        if areas_count > 0:
            return Response(
                {
                    "detail": f"Cannot delete city '{city.name}' because {areas_count} area(s) are attached to it. Please remove or reassign the areas first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        city.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CityStatusToggleView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def patch(self, request, city_id):
        city = City.objects.for_organization(request.organization).filter(id=city_id).first()
        if not city:
            raise NotFound("City was not found.")
        city.is_active = not city.is_active
        city.save(update_fields=["is_active", "updated_at"])
        return Response(CitySerializer(city).data)


class AreaListCreateView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        areas = Area.objects.for_organization(request.organization).select_related("city", "city__country")

        search = request.query_params.get("search", "").strip()
        city_id = request.query_params.get("city", "").strip()
        status_param = request.query_params.get("status", "").strip()

        if search:
            areas = areas.filter(
                Q(name__icontains=search) | Q(code__icontains=search) | Q(postal_code__icontains=search)
            )

        if city_id:
            areas = areas.filter(city_id=city_id)

        if status_param == "active":
            areas = areas.filter(is_active=True)
        elif status_param == "inactive":
            areas = areas.filter(is_active=False)

        serializer = AreaSerializer(areas.order_by("name"), many=True)
        return Response(serializer.data)

    def post(self, request):
        city_id = request.data.get("city")
        city = None
        if city_id:
            try:
                city = City.objects.for_organization(request.organization).get(id=city_id)
            except City.DoesNotExist as exc:
                raise NotFound("Specified city was not found.") from exc

        serializer = AreaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        area = serializer.save(organization=request.organization, city=city)
        return Response(AreaSerializer(area).data, status=status.HTTP_201_CREATED)


class AreaDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def _get_area(self, request, area_id):
        try:
            return Area.objects.for_organization(request.organization).select_related("city", "city__country").get(id=area_id)
        except Area.DoesNotExist as exc:
            raise NotFound("Area was not found.") from exc

    def get(self, request, area_id):
        area = self._get_area(request, area_id)
        return Response(AreaSerializer(area).data)

    def put(self, request, area_id):
        area = self._get_area(request, area_id)
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        city = area.city
        if "city" in data:
            city_id = data.pop("city", None)
            if city_id:
                try:
                    city = City.objects.for_organization(request.organization).get(id=city_id)
                except City.DoesNotExist as exc:
                    raise NotFound("Specified city was not found.") from exc
            else:
                city = None

        serializer = AreaSerializer(area, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(city=city)
        return Response(AreaSerializer(area).data)

    def patch(self, request, area_id):
        return self.put(request, area_id)

    def delete(self, request, area_id):
        area = self._get_area(request, area_id)
        area.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AreaStatusToggleView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def patch(self, request, area_id):
        area = Area.objects.for_organization(request.organization).filter(id=area_id).first()
        if not area:
            raise NotFound("Area was not found.")
        area.is_active = not area.is_active
        area.save(update_fields=["is_active", "updated_at"])
        return Response(AreaSerializer(area).data)


class InternetPackageListView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        packages = (
            InternetPackage.objects
            .for_organization(request.organization)
            .order_by("monthly_price", "name")
        )

        search = request.query_params.get("search", "").strip()
        status_param = request.query_params.get("status", "").strip()

        if search:
            packages = packages.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )

        if status_param == "active":
            packages = packages.filter(is_active=True)
        elif status_param == "inactive":
            packages = packages.filter(is_active=False)

        serializer = InternetPackageSerializer(
            packages,
            many=True,
        )

        return Response(serializer.data)

    def post(self, request):
        serializer = InternetPackageCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        package = serializer.save(organization=request.organization)
        return Response(
            InternetPackageSerializer(package).data,
            status=status.HTTP_201_CREATED,
        )


class InternetPackageDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def _get_package(self, request, package_id):
        try:
            return (
                InternetPackage.objects
                .for_organization(request.organization)
                .get(id=package_id)
            )
        except InternetPackage.DoesNotExist as exc:
            raise NotFound(
                "Internet package was not found in this organization."
            ) from exc

    def get(self, request, package_id):
        package = self._get_package(request, package_id)
        return Response(InternetPackageSerializer(package).data)

    def put(self, request, package_id):
        package = self._get_package(request, package_id)
        serializer = InternetPackageCreateUpdateSerializer(
            package,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(InternetPackageSerializer(package).data)

    def patch(self, request, package_id):
        return self.put(request, package_id)

    def delete(self, request, package_id):
        package = self._get_package(request, package_id)
        active_subscribers = (
            ServiceAccount.objects
            .for_organization(request.organization)
            .filter(internet_package=package)
            .count()
        )

        if active_subscribers > 0:
            return Response(
                {
                    "detail": (
                        f"Cannot delete package '{package.name}' because it is currently "
                        f"assigned to {active_subscribers} subscriber service account(s). "
                        "Please deactivate the package instead to prevent new assignments."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        package.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class InternetPackageStatusToggleView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def patch(self, request, package_id):
        package = (
            InternetPackage.objects
            .for_organization(request.organization)
            .filter(id=package_id)
            .first()
        )

        if not package:
            raise NotFound("Internet package was not found in this organization.")

        package.is_active = not package.is_active
        package.save(update_fields=["is_active", "updated_at"])

        return Response(InternetPackageSerializer(package).data)


class InquiryListCreateView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        qs = (
            Inquiry.objects.for_organization(request.organization)
            .select_related("preferred_package", "assigned_staff", "dealer", "converted_customer")
            .prefetch_related("feasibility_assessments")
        )

        search = request.query_params.get("search", "").strip()
        inq_status = request.query_params.get("status", "").strip()
        city = request.query_params.get("city", "").strip()
        area = request.query_params.get("area", "").strip()
        source = request.query_params.get("source", "").strip()
        package_id = request.query_params.get("package_id", "").strip()
        assigned_staff_id = request.query_params.get("assigned_staff_id", "").strip()
        dealer_id = request.query_params.get("dealer_id", "").strip()
        follow_up_due = request.query_params.get("follow_up_due", "").strip().lower()

        if search:
            qs = qs.filter(
                Q(inquiry_number__icontains=search)
                | Q(full_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(email__icontains=search)
                | Q(address_line__icontains=search)
            )

        if inq_status:
            qs = qs.filter(status=inq_status)

        if city:
            qs = qs.filter(city__iexact=city)

        if area:
            qs = qs.filter(area__iexact=area)

        if source:
            qs = qs.filter(source=source)

        if package_id:
            qs = qs.filter(preferred_package_id=package_id)

        if assigned_staff_id:
            qs = qs.filter(assigned_staff_id=assigned_staff_id)

        if dealer_id:
            qs = qs.filter(dealer_id=dealer_id)

        if follow_up_due == "true":
            from django.utils import timezone
            qs = qs.filter(follow_up_date__lte=timezone.now().date(), status__in=[Inquiry.Status.NEW, Inquiry.Status.CONTACTED, Inquiry.Status.FOLLOW_UP])

        serializer = InquirySerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = InquiryCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        inquiry = Inquiry.objects.create(
            organization=request.organization,
            inquiry_number=generate_inquiry_number(organization=request.organization),
            created_by=request.user,
            **serializer.validated_data,
        )

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="INQUIRY_CREATED",
            resource_type="Inquiry",
            resource_id=str(inquiry.id),
            metadata={
                "inquiry_number": inquiry.inquiry_number,
                "full_name": inquiry.full_name,
                "phone": inquiry.phone,
                "status": inquiry.status,
            },
        )

        return Response(InquirySerializer(inquiry).data, status=status.HTTP_201_CREATED)


class InquiryDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def _get_inquiry(self, request, inquiry_id):
        inquiry = (
            Inquiry.objects.for_organization(request.organization)
            .select_related("preferred_package", "assigned_staff", "dealer", "converted_customer")
            .filter(id=inquiry_id)
            .first()
        )
        if not inquiry:
            raise NotFound("Inquiry was not found in this organization.")
        return inquiry

    def get(self, request, inquiry_id):
        inquiry = self._get_inquiry(request, inquiry_id)
        return Response(InquirySerializer(inquiry).data)

    def put(self, request, inquiry_id):
        inquiry = self._get_inquiry(request, inquiry_id)
        serializer = InquiryCreateUpdateSerializer(inquiry, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="INQUIRY_UPDATED",
            resource_type="Inquiry",
            resource_id=str(inquiry.id),
            metadata={
                "inquiry_number": inquiry.inquiry_number,
                "updated_fields": list(serializer.validated_data.keys()),
            },
        )

        return Response(InquirySerializer(inquiry).data)

    def patch(self, request, inquiry_id):
        return self.put(request, inquiry_id)

    def delete(self, request, inquiry_id):
        inquiry = self._get_inquiry(request, inquiry_id)
        if inquiry.status == Inquiry.Status.CONVERTED:
            return Response(
                {"detail": "Cannot delete an inquiry that has already been converted to a customer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        inquiry.status = Inquiry.Status.CANCELLED
        inquiry.save(update_fields=["status", "updated_at"])

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="INQUIRY_CANCELLED",
            resource_type="Inquiry",
            resource_id=str(inquiry.id),
            metadata={"inquiry_number": inquiry.inquiry_number},
        )

        return Response(InquirySerializer(inquiry).data)


class InquiryStatusTransitionView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, inquiry_id):
        inquiry = (
            Inquiry.objects.for_organization(request.organization)
            .filter(id=inquiry_id)
            .first()
        )
        if not inquiry:
            raise NotFound("Inquiry was not found in this organization.")

        serializer = InquiryStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        notes = serializer.validated_data.get("notes", "")
        follow_up_date = serializer.validated_data.get("follow_up_date")

        old_status = inquiry.status
        inquiry.status = new_status
        if notes.strip():
            inquiry.notes = f"{inquiry.notes}\n{notes}".strip() if inquiry.notes else notes.strip()
        if follow_up_date is not None:
            inquiry.follow_up_date = follow_up_date

        inquiry.save(update_fields=["status", "notes", "follow_up_date", "updated_at"])

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="INQUIRY_STATUS_CHANGED",
            resource_type="Inquiry",
            resource_id=str(inquiry.id),
            metadata={
                "inquiry_number": inquiry.inquiry_number,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        return Response(InquirySerializer(inquiry).data)


class InquiryConvertView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def post(self, request, inquiry_id):
        serializer = InquiryConversionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = convert_inquiry_to_customer(
                inquiry_id=inquiry_id,
                organization=request.organization,
                actor=request.user,
                **serializer.validated_data,
            )
        except (InquiryDomainError, CustomerActivationError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "customer_id": str(result.customer.id),
                "customer_number": result.customer.customer_number,
                "service_account_id": str(result.service_account.id),
                "service_number": result.service_account.service_number,
                "billing_profile_id": str(result.billing_profile.id),
                "inquiry_id": str(inquiry_id),
                "status": "CONVERTED",
            },
            status=status.HTTP_201_CREATED,
        )


class FeasibilityAssessmentListCreateView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        qs = (
            FeasibilityAssessment.objects.for_organization(request.organization)
            .select_related("inquiry", "customer", "package", "network_node", "assigned_technician")
        )

        inquiry_id = request.query_params.get("inquiry_id", "").strip()
        customer_id = request.query_params.get("customer_id", "").strip()
        fsb_status = request.query_params.get("status", "").strip()
        technician_id = request.query_params.get("technician_id", "").strip()
        search = request.query_params.get("search", "").strip()

        if inquiry_id:
            qs = qs.filter(inquiry_id=inquiry_id)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)
        if fsb_status:
            qs = qs.filter(status=fsb_status)
        if technician_id:
            qs = qs.filter(assigned_technician_id=technician_id)
        if search:
            qs = qs.filter(
                Q(feasibility_number__icontains=search)
                | Q(address_line__icontains=search)
                | Q(city__icontains=search)
                | Q(area__icontains=search)
            )

        serializer = FeasibilityAssessmentSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = FeasibilityAssessmentCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assessment = FeasibilityAssessment.objects.create(
            organization=request.organization,
            feasibility_number=generate_feasibility_number(organization=request.organization),
            created_by=request.user,
            **serializer.validated_data,
        )

        # Synchronize inquiry status if linked
        if assessment.inquiry and assessment.inquiry.status in [Inquiry.Status.NEW, Inquiry.Status.CONTACTED]:
            assessment.inquiry.status = Inquiry.Status.FEASIBILITY_PENDING
            assessment.inquiry.save(update_fields=["status", "updated_at"])

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="FEASIBILITY_ASSESSMENT_CREATED",
            resource_type="FeasibilityAssessment",
            resource_id=str(assessment.id),
            metadata={
                "feasibility_number": assessment.feasibility_number,
                "status": assessment.status,
                "inquiry_id": str(assessment.inquiry_id) if assessment.inquiry_id else None,
            },
        )

        return Response(FeasibilityAssessmentSerializer(assessment).data, status=status.HTTP_201_CREATED)


class FeasibilityAssessmentDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def _get_assessment(self, request, assessment_id):
        assessment = (
            FeasibilityAssessment.objects.for_organization(request.organization)
            .select_related("inquiry", "customer", "package", "network_node", "assigned_technician")
            .filter(id=assessment_id)
            .first()
        )
        if not assessment:
            raise NotFound("Feasibility assessment was not found in this organization.")
        return assessment

    def get(self, request, assessment_id):
        assessment = self._get_assessment(request, assessment_id)
        return Response(FeasibilityAssessmentSerializer(assessment).data)

    def put(self, request, assessment_id):
        assessment = self._get_assessment(request, assessment_id)
        serializer = FeasibilityAssessmentCreateUpdateSerializer(assessment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Synchronize inquiry status if assessment became FEASIBLE or NOT_FEASIBLE
        if assessment.inquiry:
            if assessment.status == FeasibilityAssessment.Status.FEASIBLE and assessment.inquiry.status != Inquiry.Status.CONVERTED:
                assessment.inquiry.status = Inquiry.Status.FEASIBLE
                assessment.inquiry.save(update_fields=["status", "updated_at"])
            elif assessment.status == FeasibilityAssessment.Status.NOT_FEASIBLE and assessment.inquiry.status != Inquiry.Status.CONVERTED:
                assessment.inquiry.status = Inquiry.Status.NOT_FEASIBLE
                assessment.inquiry.save(update_fields=["status", "updated_at"])

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="FEASIBILITY_ASSESSMENT_UPDATED",
            resource_type="FeasibilityAssessment",
            resource_id=str(assessment.id),
            metadata={
                "feasibility_number": assessment.feasibility_number,
                "status": assessment.status,
                "not_feasible_reason": assessment.not_feasible_reason,
            },
        )

        return Response(FeasibilityAssessmentSerializer(assessment).data)

    def patch(self, request, assessment_id):
        return self.put(request, assessment_id)


class DealerListCreateView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request):
        dealers = (
            Dealer.objects.for_organization(request.organization)
            .select_related("assigned_area", "country")
            .annotate(_customers_count=Count("customers"))
        )

        search = request.query_params.get("search", "").strip()
        dealer_status = request.query_params.get("status", "").strip()
        area_id = request.query_params.get("area_id", "").strip()

        if search:
            dealers = dealers.filter(
                Q(dealer_code__icontains=search)
                | Q(name__icontains=search)
                | Q(company_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(city__icontains=search)
                | Q(area__icontains=search)
            )

        if dealer_status:
            dealers = dealers.filter(status=dealer_status)

        if area_id:
            dealers = dealers.filter(assigned_area_id=area_id)

        serializer = DealerSerializer(dealers, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DealerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        dealer = Dealer.objects.create(
            organization=request.organization,
            dealer_code=generate_dealer_code(organization=request.organization),
            created_by=request.user,
            **serializer.validated_data,
        )

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_CREATED",
            resource_type="Dealer",
            resource_id=str(dealer.id),
            metadata={
                "dealer_code": dealer.dealer_code,
                "name": dealer.name,
                "company_name": dealer.company_name,
            },
        )

        return Response(DealerSerializer(dealer).data, status=status.HTTP_201_CREATED)


class DealerDetailView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def _get_dealer(self, request, dealer_id):
        dealer = (
            Dealer.objects.for_organization(request.organization)
            .select_related("assigned_area", "country")
            .filter(id=dealer_id)
            .first()
        )
        if not dealer:
            raise NotFound("Dealer was not found in this organization.")
        return dealer

    def get(self, request, dealer_id):
        dealer = self._get_dealer(request, dealer_id)
        return Response(DealerSerializer(dealer).data)

    def put(self, request, dealer_id):
        dealer = self._get_dealer(request, dealer_id)
        serializer = DealerSerializer(dealer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_UPDATED",
            resource_type="Dealer",
            resource_id=str(dealer.id),
            metadata={
                "dealer_code": dealer.dealer_code,
                "name": dealer.name,
            },
        )

        return Response(DealerSerializer(dealer).data)

    def patch(self, request, dealer_id):
        return self.put(request, dealer_id)


class DealerStatusToggleView(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def patch(self, request, dealer_id):
        dealer = (
            Dealer.objects.for_organization(request.organization)
            .filter(id=dealer_id)
            .first()
        )
        if not dealer:
            raise NotFound("Dealer was not found in this organization.")

        target_status = request.data.get("status", "").strip().upper()
        if target_status in [s[0] for s in Dealer.Status.choices]:
            dealer.status = target_status
        else:
            dealer.status = Dealer.Status.INACTIVE if dealer.status == Dealer.Status.ACTIVE else Dealer.Status.ACTIVE

        dealer.save(update_fields=["status", "updated_at"])

        record_audit_log(
            organization=request.organization,
            actor=request.user,
            action="DEALER_STATUS_CHANGED",
            resource_type="Dealer",
            resource_id=str(dealer.id),
            metadata={
                "dealer_code": dealer.dealer_code,
                "status": dealer.status,
            },
        )

        return Response(DealerSerializer(dealer).data)


class Dealer360View(APIView):
    permission_classes = [IsOrganizationStaffOrOwner]

    def get(self, request, dealer_id):
        dealer = (
            Dealer.objects.for_organization(request.organization)
            .select_related("assigned_area", "country")
            .filter(id=dealer_id)
            .first()
        )
        if not dealer:
            raise NotFound("Dealer was not found in this organization.")

        customers_qs = (
            Customer.objects.for_organization(request.organization)
            .filter(dealer=dealer)
            .prefetch_related("service_accounts__internet_package")
        )

        total_customers = customers_qs.count()
        active_customers = customers_qs.filter(is_active=True).count()

        services_qs = ServiceAccount.objects.for_organization(request.organization).filter(
            customer__dealer=dealer
        )
        active_services = services_qs.filter(status=ServiceAccount.Status.ACTIVE).count()

        invoices_qs = Invoice.objects.for_organization(request.organization).filter(
            service_account__customer__dealer=dealer
        )
        total_invoiced = sum((inv.total_amount for inv in invoices_qs), Decimal("0.00"))

        payments_qs = Payment.objects.for_organization(request.organization).filter(
            service_account__customer__dealer=dealer
        ).select_related("service_account__customer")

        total_collected = payments_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Commission calculation
        if dealer.commission_type == Dealer.CommissionType.PERCENTAGE:
            commission_amount = (total_collected * (dealer.commission_rate_percentage / Decimal("100.00"))).quantize(Decimal("0.01"))
        else:
            commission_amount = (Decimal(str(active_customers)) * dealer.commission_rate_percentage).quantize(Decimal("0.01"))

        customer_list = [
            {
                "id": str(c.id),
                "customer_number": c.customer_number,
                "full_name": c.full_name,
                "phone": c.phone,
                "city": c.city,
                "area": c.area,
                "is_active": c.is_active,
                "service_count": c.service_accounts.count(),
                "created_at": c.created_at.isoformat(),
            }
            for c in customers_qs[:50]
        ]

        collection_list = [
            {
                "id": str(p.id),
                "payment_number": p.payment_number,
                "customer_name": p.service_account.customer.full_name,
                "customer_number": p.service_account.customer.customer_number,
                "service_number": p.service_account.service_number,
                "amount": str(p.amount),
                "payment_method": p.payment_method,
                "paid_at": p.paid_at.isoformat(),
            }
            for p in payments_qs.order_by("-paid_at")[:50]
        ]

        return Response(
            {
                "dealer": DealerSerializer(dealer).data,
                "metrics": {
                    "total_customers": total_customers,
                    "active_customers": active_customers,
                    "active_services": active_services,
                    "total_invoiced": str(total_invoiced),
                    "total_collected": str(total_collected),
                    "calculated_commission": str(commission_amount),
                    "commission_rate": str(dealer.commission_rate_percentage),
                    "commission_type": dealer.commission_type,
                },
                "customers": customer_list,
                "recent_collections": collection_list,
            }
        )
