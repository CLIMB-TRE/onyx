import time
from rest_framework import status
from .models import RequestHistory


# Credit to Felix Eklöf for this middleware
# https://stackoverflow.com/a/63176786/16088113
class SaveRequest:
    def __init__(self, get_response):
        self.get_response = get_response
        self.prefixes = ["/accounts", "/projects"]

    def __call__(self, request):
        # Get response from view function, and calculate the execution time (in ms)
        _t = time.time()
        response = self.get_response(request)
        _t = int((time.time() - _t) * 1000)

        # If the url does not start with a correct prefix, don't log the request
        if not any(request.path.startswith(prefix) for prefix in self.prefixes):
            return response

        # If the request was not successful, log the response content
        error_messages = ""
        if not status.is_success(response.status_code):
            error_messages = response.content

        # Store the first 100 characters of the path
        # Any path beyond that is likely to be rubbish
        path = request.path[:100]

        # Record the user who made the request (if not anonymous)
        if not request.user.is_anonymous:
            user = request.user
        else:
            user = None

        # Record the client's ip address
        # TODO: This can be spoofed, check nginx is passing correct address
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            address = x_forwarded_for.split(",")[0]
        else:
            address = request.META.get("REMOTE_ADDR")

        # Store the first 20 characters of the address
        # Any address beyond that is likely to be rubbish
        address = address[:20]

        # Log the request
        RequestHistory.objects.create(
            endpoint=path,
            method=request.method,
            status=response.status_code,
            user=user,
            address=address,
            exec_time=_t,
            error_messages=error_messages,
        )

        return response
