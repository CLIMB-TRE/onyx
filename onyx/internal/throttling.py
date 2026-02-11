from rest_framework.throttling import UserRateThrottle


class BurstRateThrottle(UserRateThrottle):
    scope = "burst"

    def allow_request(self, request, view):
        if request.user.is_staff:
            return True
        else:
            return super().allow_request(request, view)


class SustainedRateThrottle(UserRateThrottle):
    scope = "sustained"

    def allow_request(self, request, view):
        if request.user.is_staff:
            return True
        else:
            return super().allow_request(request, view)
