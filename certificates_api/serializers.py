from rest_framework import serializers


class RecipientSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, trim_whitespace=True)
    email = serializers.EmailField()
    course = serializers.CharField(max_length=255, required=False, allow_blank=True, default="Certificate of Completion")
    trigger_failure = serializers.BooleanField(required=False, default=False)

    def validate_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Recipient name cannot be empty.")
        return value.strip()


class GenerateCertificateJobSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False, allow_blank=True, default="Certificate Generation Job")
    recipients = serializers.ListField(child=RecipientSerializer(), min_length=1)

    def validate_title(self, value):
        return value.strip() if value else "Certificate Generation Job"

    def validate_recipients(self, value):
        if not value:
            raise serializers.ValidationError("At least one recipient is required.")
        return value
