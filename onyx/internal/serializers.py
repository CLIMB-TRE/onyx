from rest_framework import serializers
from internal.models import RequestHistory


class RequestHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestHistory
        fields = [
            "date",
            "address",
            "endpoint",
            "method",
            "status",
            "exec_time",
            "error_messages",
        ]
