import re
import uuid
from django.utils.deprecation import MiddlewareMixin
from tenancy.logging import set_current_request_id

SAFE_REQUEST_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class RequestIDMiddleware(MiddlewareMixin):
    """
    Extracts or generates a unique Request ID for every incoming HTTP request.
    Attaches the request ID to the request object, thread-local logging context,
    and the X-Request-ID response header.
    """

    def process_request(self, request):
        incoming_id = (
            request.META.get("HTTP_X_REQUEST_ID")
            or request.headers.get("X-Request-ID")
            or ""
        ).strip()

        if incoming_id and SAFE_REQUEST_ID_REGEX.match(incoming_id):
            request_id = incoming_id
        else:
            request_id = str(uuid.uuid4())

        request.request_id = request_id
        set_current_request_id(request_id)

    def process_response(self, request, response):
        request_id = getattr(request, "request_id", None)
        if request_id:
            response["X-Request-ID"] = request_id
        set_current_request_id(None)
        return response
