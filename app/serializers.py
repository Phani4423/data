from rest_framework import serializers


class FileUploadSerializer(serializers.Serializer):
    """
    Serializer for file upload ETL.
    - file: uploaded file (CSV / JSON / XML / Excel)
    - table_name: optional MySQL table name
    """
    file = serializers.FileField()
    table_name = serializers.CharField(required=False, allow_blank=True)




class RandomUserFetchSerializer(serializers.Serializer):
    """
    Serializer for random user fetch API ETL.
    - count: number of random users to fetch (default: 2)
    """
    count = serializers.IntegerField(required=False, default=2, min_value=1, max_value=100)
