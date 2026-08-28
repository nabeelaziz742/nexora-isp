from rest_framework import serializers


class MaintenanceScheduleSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    maintenance_notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class MaintenanceCompletionSerializer(serializers.Serializer):
    completion_notes = serializers.CharField()
