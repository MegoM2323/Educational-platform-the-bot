"""
Serializers for ElementFile model
T004: File Upload API Endpoints
"""
from rest_framework import serializers
from knowledge_graph.models import ElementFile


class ElementFileSerializer(serializers.ModelSerializer):
    """Serializer for element file attachments"""
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ElementFile
        fields = ['id', 'file', 'original_filename', 'file_size', 'uploaded_at', 'file_url']
        read_only_fields = ['id', 'original_filename', 'file_size', 'uploaded_at', 'file_url']

    def get_file_url(self, obj):
        """Generate absolute URL for file download"""
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None
