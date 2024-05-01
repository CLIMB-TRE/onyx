from rest_framework import serializers
from internal.models import Request


class RequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Request
        fields = [
            "date",
            "address",
            "endpoint",
            "method",
            "status",
            "exec_time",
            "error_messages",
        ]
