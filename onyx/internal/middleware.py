import time
import logging
import json
from rest_framework import status
from rest_framework.response import Response
from django.core.handlers.wsgi import WSGIRequest
from django.template.defaultfilters import filesizeformat
from .models import RequestHistory


logger = logging.getLogger(__name__)


# Credit to Felix Eklöf for this middleware
# https://stackoverflow.com/a/63176786/16088113
class SaveRequest:
    def __init__(self, get_response):
        self.get_response = get_response
        self.prefixes = ["/accounts", "/projects"]

    def __call__(self, request: WSGIRequest):
        # Get response from view function, and calculate the execution time (in ms)
        start_time = time.time()
        response: Response = self.get_response(request)
        exec_time = int((time.time() - start_time) * 1000)

        # If the url does not start with a correct prefix, don't log the request
        if not any(request.path.startswith(prefix) for prefix in self.prefixes):
            return response

        # If the request was not successful, log the response content
        error_messages = ""
        if not status.is_success(response.status_code):
            error_messages = response.content.decode("utf-8")

        # Store the first 100 characters of the path
        # Any path beyond that is likely to be rubbish
        path = request.path[:100]

        # Record the user who made the request (if not anonymous)
        if not request.user.is_anonymous:
            user = request.user
        else:
            user = None

        # Record the client's address
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            address = x_forwarded_for.split(",")[0]
        else:
            address = request.META.get("REMOTE_ADDR", "Unknown")

        # Store the first 20 characters of the address
        # Any address beyond that is likely to be rubbish
        address = address[:20]

        # Record the request
        RequestHistory.objects.create(
            endpoint=path,
            method=request.method,
            status=response.status_code,
            user=user,
            address=address,
            exec_time=exec_time,
            error_messages=error_messages,
        )

        # Log the request
        log = f"{address} {user} {response.status_code} {filesizeformat(len(response.content))} {exec_time}ms {request.get_full_path()}"
        if status.is_server_error(response.status_code):
            errors = json.loads(error_messages).get("messages", {})
            logger.error(f"{log} {errors}")
        elif status.is_client_error(response.status_code):
            errors = json.loads(error_messages).get("messages", {})
            logger.warning(f"{log} {errors}")
        else:
            logger.info(log)

        return response
