"""
API views for configuration management.

Endpoints:
- GET /api/admin/config/ - Get all configurations
- GET /api/admin/config/{key}/ - Get single config
- PUT /api/admin/config/{key}/ - Update config
- POST /api/admin/config/reset/ - Reset to defaults
- GET /api/admin/config/config_schema/ - Get schema
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from .config import ConfigurationService, DEFAULT_CONFIGURATIONS
from .config_serializers import (
    ConfigurationUpdateSerializer,
    ConfigurationBulkUpdateSerializer,
    ConfigurationResetSerializer,
)
from .models import Configuration


class ConfigurationViewSet(viewsets.GenericViewSet):
    """
    ViewSet for configuration management.

    Only admin users can access these endpoints.
    """

    permission_classes = [IsAdminUser]
    queryset = Configuration.objects.all()
    serializer_class = ConfigurationUpdateSerializer
    lookup_field = "key"

    def list(self, request):
        """
        Get all configurations.

        Returns both custom and default values with descriptions.
        """
        configs = ConfigurationService.get_all()
        items = []

        for key, value in configs.items():
            if key in DEFAULT_CONFIGURATIONS:
                default_config = DEFAULT_CONFIGURATIONS[key]
                items.append(
                    {
                        "key": key,
                        "value": value,
                        "value_type": default_config["type"],
                        "description": default_config.get("description", ""),
                        "group": default_config.get("group", ""),
                        "default": default_config["value"],
                    }
                )

        return Response(
            {
                "count": len(items),
                "results": items,
            }
        )

    def retrieve(self, request, pk=None):
        """
        Get single configuration by key.

        Args:
            pk: Configuration key
        """
        key = pk
        if key not in DEFAULT_CONFIGURATIONS:
            return Response(
                {"error": f"Unknown configuration key: {key}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        default_config = DEFAULT_CONFIGURATIONS[key]
        current_value = ConfigurationService.get(key)

        return Response(
            {
                "key": key,
                "value": current_value,
                "value_type": default_config["type"],
                "description": default_config.get("description", ""),
                "group": default_config.get("group", ""),
                "default": default_config["value"],
                "updated_at": None,
                "updated_by": None,
            }
        )

    def update(self, request, pk=None):
        """
        Update single configuration by key.

        Args:
            pk: Configuration key
        """
        key = pk
        if key not in DEFAULT_CONFIGURATIONS:
            return Response(
                {"error": f"Unknown configuration key: {key}"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ConfigurationUpdateSerializer(
            data=request.data, context={"request": request, "view": self}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        value = serializer.validated_data.get("value")

        try:
            config = ConfigurationService.set(key, value, user=request.user)
            return Response(
                {
                    "key": key,
                    "value": value,
                    "message": "Configuration updated successfully",
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def bulk_update(self, request):
        """
        Update multiple configurations at once.

        Request body:
        {
            "configurations": {
                "feature_flags.assignments_enabled": true,
                "rate_limit.api_requests_per_minute": 100
            }
        }
        """
        serializer = ConfigurationBulkUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        configs = serializer.validated_data.get("configurations", {})

        try:
            ConfigurationService.set_multiple(configs, user=request.user)
            return Response(
                {
                    "count": len(configs),
                    "message": "Configurations updated successfully",
                    "updated": list(configs.keys()),
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def reset(self, request):
        """
        Reset configurations to defaults.

        Optional body:
        {
            "reset_type": "all",  // or "group"
            "group": "feature_flags"  // required if reset_type is "group"
        }
        """
        serializer = ConfigurationResetSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        reset_type = serializer.validated_data.get("reset_type", "all")
        group = serializer.validated_data.get("group", "")

        try:
            if reset_type == "group" and group:
                # Reset specific group
                group_prefix = f"{group}."
                keys_to_reset = [
                    k
                    for k in DEFAULT_CONFIGURATIONS.keys()
                    if k.startswith(group_prefix)
                ]
                for key in keys_to_reset:
                    ConfigurationService.reset_key(key, user=request.user)
                message = f'Group "{group}" reset to defaults'
            else:
                # Reset all
                ConfigurationService.reset(user=request.user)
                message = "All configurations reset to defaults"

            return Response(
                {
                    "message": message,
                    "reset_type": reset_type,
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def config_schema(self, request):
        """
        Get configuration schema.

        Returns all available configuration keys with types and descriptions.
        """
        schema = ConfigurationService.get_schema()

        # Group by group name
        grouped = {}
        for key, info in schema.items():
            group = info.get("group", "other")
            if group not in grouped:
                grouped[group] = []
            grouped[group].append({"key": key, **info})

        return Response(
            {
                "total": len(schema),
                "groups": grouped,
                "schema": schema,
            }
        )

    @action(detail=False, methods=["get"])
    def group(self, request, group=None):
        """
        Get configurations by group.

        Query parameter: group=feature_flags
        """
        group = request.query_params.get("group")
        if not group:
            return Response(
                {"error": "group query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        configs = ConfigurationService.get_group(group)
        if not configs:
            return Response(
                {"error": f"Unknown group: {group}"}, status=status.HTTP_404_NOT_FOUND
            )

        items = []
        for key, value in configs.items():
            if key in DEFAULT_CONFIGURATIONS:
                default_config = DEFAULT_CONFIGURATIONS[key]
                items.append(
                    {
                        "key": key,
                        "value": value,
                        "value_type": default_config["type"],
                        "description": default_config.get("description", ""),
                        "group": default_config.get("group", ""),
                        "default": default_config["value"],
                    }
                )

        return Response(
            {
                "group": group,
                "count": len(items),
                "results": items,
            }
        )
