from rest_framework import serializers


class FileUploadSerializer(serializers.Serializer):
    """
    Serializer for file upload ETL.
    - file: uploaded file (CSV / JSON / XML / Excel)
    - table_name: optional MySQL table name
    """
    file = serializers.FileField()
    table_name = serializers.CharField(required=False, allow_blank=True)


class CarFetchSerializer(serializers.Serializer):
    """
    Serializer for external API ETL.
    - make: car make (e.g., Audi)
    - model: car model (e.g., A4)
    - table_name: optional MySQL table name
    """
    make = serializers.CharField()
    model = serializers.CharField()
