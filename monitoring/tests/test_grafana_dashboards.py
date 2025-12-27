"""
Grafana Dashboards Tests

Tests to verify:
1. All dashboard JSON files are valid
2. Dashboard structure is correct
3. Queries use valid metrics
4. Panels are properly configured
5. Datasources are referenced correctly
"""

import json
import os
import pytest
from pathlib import Path


DASHBOARDS_DIR = Path(__file__).parent.parent / "grafana" / "dashboards"

# List of required dashboard files
REQUIRED_DASHBOARDS = [
    "system-overview.json",
    "backend-metrics.json",
    "database-metrics.json",
    "redis-cache.json",
    "frontend-nginx.json",
    "celery-tasks.json",
]

# Valid panel types
VALID_PANEL_TYPES = {
    "timeseries",
    "gauge",
    "stat",
    "piechart",
    "table",
    "graph",
    "row",
}

# Valid datasources
VALID_DATASOURCES = {
    "Prometheus",
    "-- Grafana --",
    "Loki",
    "Alertmanager",
}


class TestDashboardExistence:
    """Test that all required dashboard files exist."""

    def test_dashboards_directory_exists(self):
        """Test that dashboards directory exists."""
        assert DASHBOARDS_DIR.exists(), f"Dashboards directory not found: {DASHBOARDS_DIR}"
        assert DASHBOARDS_DIR.is_dir(), f"Dashboards path is not a directory: {DASHBOARDS_DIR}"

    @pytest.mark.parametrize("dashboard_file", REQUIRED_DASHBOARDS)
    def test_dashboard_file_exists(self, dashboard_file):
        """Test that each required dashboard file exists."""
        dashboard_path = DASHBOARDS_DIR / dashboard_file
        assert dashboard_path.exists(), f"Dashboard file not found: {dashboard_file}"
        assert dashboard_path.is_file(), f"Dashboard is not a file: {dashboard_file}"

    def test_all_dashboards_are_valid_json(self):
        """Test that all dashboard files are valid JSON."""
        for dashboard_file in REQUIRED_DASHBOARDS:
            dashboard_path = DASHBOARDS_DIR / dashboard_file
            try:
                with open(dashboard_path, "r") as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {dashboard_file}: {str(e)}")


class TestDashboardStructure:
    """Test dashboard structure and required fields."""

    @pytest.fixture
    def dashboards(self):
        """Load all dashboards."""
        dashboards = {}
        for dashboard_file in REQUIRED_DASHBOARDS:
            dashboard_path = DASHBOARDS_DIR / dashboard_file
            with open(dashboard_path, "r") as f:
                dashboards[dashboard_file] = json.load(f)
        return dashboards

    @pytest.mark.parametrize("dashboard_file", REQUIRED_DASHBOARDS)
    def test_dashboard_has_required_fields(self, dashboards, dashboard_file):
        """Test that each dashboard has required top-level fields."""
        dashboard = dashboards[dashboard_file]

        required_fields = ["title", "panels", "refresh", "schemaVersion", "time", "tags"]
        for field in required_fields:
            assert field in dashboard, f"{dashboard_file} missing required field: {field}"

    @pytest.mark.parametrize("dashboard_file", REQUIRED_DASHBOARDS)
    def test_dashboard_has_title(self, dashboards, dashboard_file):
        """Test that each dashboard has a title."""
        dashboard = dashboards[dashboard_file]
        assert dashboard.get("title"), f"{dashboard_file} has empty title"
        assert isinstance(dashboard["title"], str), f"{dashboard_file} title is not a string"

    @pytest.mark.parametrize("dashboard_file", REQUIRED_DASHBOARDS)
    def test_dashboard_has_uid(self, dashboards, dashboard_file):
        """Test that each dashboard has a unique ID."""
        dashboard = dashboards[dashboard_file]
        assert "uid" in dashboard, f"{dashboard_file} missing uid"
        assert dashboard["uid"], f"{dashboard_file} has empty uid"

    @pytest.mark.parametrize("dashboard_file", REQUIRED_DASHBOARDS)
    def test_dashboard_has_panels(self, dashboards, dashboard_file):
        """Test that each dashboard has at least one panel."""
        dashboard = dashboards[dashboard_file]
        assert isinstance(dashboard["panels"], list), f"{dashboard_file} panels is not a list"
        assert len(dashboard["panels"]) > 0, f"{dashboard_file} has no panels"

    @pytest.mark.parametrize("dashboard_file", REQUIRED_DASHBOARDS)
    def test_dashboard_refresh_is_valid(self, dashboards, dashboard_file):
        """Test that dashboard refresh interval is valid."""
        dashboard = dashboards[dashboard_file]
        refresh = dashboard.get("refresh", "")
        # Valid formats: "30s", "1m", "5m", "10m", "30m", "1h"
        valid_refreshes = ["30s", "1m", "5m", "10m", "30m", "1h"]
        assert refresh in valid_refreshes, f"{dashboard_file} has invalid refresh: {refresh}"

    @pytest.mark.parametrize("dashboard_file", REQUIRED_DASHBOARDS)
    def test_dashboard_has_tags(self, dashboards, dashboard_file):
        """Test that each dashboard has tags."""
        dashboard = dashboards[dashboard_file]
        assert isinstance(dashboard.get("tags"), list), f"{dashboard_file} tags is not a list"
        assert len(dashboard["tags"]) > 0, f"{dashboard_file} has no tags"
        assert "thebot" in dashboard["tags"], f"{dashboard_file} missing 'thebot' tag"


class TestPanels:
    """Test panel configuration."""

    @pytest.fixture
    def dashboards(self):
        """Load all dashboards."""
        dashboards = {}
        for dashboard_file in REQUIRED_DASHBOARDS:
            dashboard_path = DASHBOARDS_DIR / dashboard_file
            with open(dashboard_path, "r") as f:
                dashboards[dashboard_file] = json.load(f)
        return dashboards

    def test_all_panels_have_required_fields(self, dashboards):
        """Test that all panels have required fields."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                required_fields = ["type", "title"]
                for field in required_fields:
                    assert field in panel, (
                        f"{dashboard_file} panel {i} missing required field: {field}"
                    )

    def test_all_panels_have_valid_type(self, dashboards):
        """Test that all panels have valid type."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                panel_type = panel.get("type")
                assert panel_type in VALID_PANEL_TYPES, (
                    f"{dashboard_file} panel {i} has invalid type: {panel_type}"
                )

    def test_panels_with_datasource_reference_valid_source(self, dashboards):
        """Test that panels reference valid datasources."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                datasource = panel.get("datasource")
                if datasource:
                    assert datasource in VALID_DATASOURCES, (
                        f"{dashboard_file} panel {i} references invalid datasource: {datasource}"
                    )

    def test_all_panels_have_gridpos(self, dashboards):
        """Test that all panels have grid position."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                assert "gridPos" in panel, f"{dashboard_file} panel {i} missing gridPos"
                gridpos = panel["gridPos"]
                required_gridpos_fields = ["h", "w", "x", "y"]
                for field in required_gridpos_fields:
                    assert field in gridpos, (
                        f"{dashboard_file} panel {i} gridPos missing {field}"
                    )

    def test_timeseries_panels_have_targets(self, dashboards):
        """Test that timeseries panels have targets."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                if panel.get("type") == "timeseries":
                    assert "targets" in panel, (
                        f"{dashboard_file} timeseries panel {i} missing targets"
                    )
                    assert len(panel["targets"]) > 0, (
                        f"{dashboard_file} timeseries panel {i} has no targets"
                    )

    def test_stat_panels_have_targets(self, dashboards):
        """Test that stat panels have targets."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                if panel.get("type") == "stat":
                    assert "targets" in panel, (
                        f"{dashboard_file} stat panel {i} missing targets"
                    )
                    assert len(panel["targets"]) > 0, (
                        f"{dashboard_file} stat panel {i} has no targets"
                    )

    def test_gauge_panels_have_targets(self, dashboards):
        """Test that gauge panels have targets."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                if panel.get("type") == "gauge":
                    assert "targets" in panel, (
                        f"{dashboard_file} gauge panel {i} missing targets"
                    )
                    assert len(panel["targets"]) > 0, (
                        f"{dashboard_file} gauge panel {i} has no targets"
                    )


class TestQueries:
    """Test PromQL queries."""

    @pytest.fixture
    def dashboards(self):
        """Load all dashboards."""
        dashboards = {}
        for dashboard_file in REQUIRED_DASHBOARDS:
            dashboard_path = DASHBOARDS_DIR / dashboard_file
            with open(dashboard_path, "r") as f:
                dashboards[dashboard_file] = json.load(f)
        return dashboards

    def test_all_queries_have_expr(self, dashboards):
        """Test that all queries have expr field."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                for j, target in enumerate(panel.get("targets", [])):
                    assert "expr" in target or "query" in target, (
                        f"{dashboard_file} panel {i} target {j} missing expr/query"
                    )

    def test_query_format_is_valid(self, dashboards):
        """Test that queries are non-empty strings."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                for j, target in enumerate(panel.get("targets", [])):
                    expr = target.get("expr", target.get("query", ""))
                    assert isinstance(expr, str), (
                        f"{dashboard_file} panel {i} target {j} expr is not a string"
                    )
                    assert expr, (
                        f"{dashboard_file} panel {i} target {j} has empty expr"
                    )

    def test_no_hardcoded_values(self, dashboards):
        """Test that queries don't have obviously hardcoded values."""
        for dashboard_file, dashboard in dashboards.items():
            for i, panel in enumerate(dashboard.get("panels", [])):
                for j, target in enumerate(panel.get("targets", [])):
                    expr = target.get("expr", target.get("query", ""))
                    # Should not be pure numbers (metric IDs)
                    # but can contain numbers in formulas
                    assert not expr.isdigit(), (
                        f"{dashboard_file} panel {i} target {j} has numeric-only expression"
                    )


class TestDashboardIntegration:
    """Integration tests for dashboard completeness."""

    def test_system_overview_completeness(self):
        """Test that system overview dashboard is complete."""
        dashboard_path = DASHBOARDS_DIR / "system-overview.json"
        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        # Should have health overview metrics
        panel_titles = [p.get("title") for p in dashboard["panels"]]
        assert any("Services" in t for t in panel_titles), "Missing services health panel"
        assert any("Memory" in t for t in panel_titles), "Missing memory panel"
        assert any("CPU" in t for t in panel_titles), "Missing CPU panel"

    def test_backend_metrics_completeness(self):
        """Test that backend metrics dashboard is complete."""
        dashboard_path = DASHBOARDS_DIR / "backend-metrics.json"
        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        panel_titles = [p.get("title") for p in dashboard["panels"]]
        assert any("Request" in t for t in panel_titles), "Missing request panel"
        assert any("Error" in t for t in panel_titles), "Missing error panel"
        assert any("Latency" in t for t in panel_titles), "Missing latency panel"

    def test_database_metrics_completeness(self):
        """Test that database metrics dashboard is complete."""
        dashboard_path = DASHBOARDS_DIR / "database-metrics.json"
        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        panel_titles = [p.get("title") for p in dashboard["panels"]]
        assert any("Query" in t for t in panel_titles), "Missing query panel"
        assert any("Connection" in t for t in panel_titles), "Missing connection panel"

    def test_redis_dashboard_completeness(self):
        """Test that Redis dashboard is complete."""
        dashboard_path = DASHBOARDS_DIR / "redis-cache.json"
        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        panel_titles = [p.get("title") for p in dashboard["panels"]]
        assert any("Cache" in t or "Hit" in t for t in panel_titles), "Missing cache panel"
        assert any("Memory" in t for t in panel_titles), "Missing memory panel"

    def test_frontend_dashboard_completeness(self):
        """Test that frontend dashboard is complete."""
        dashboard_path = DASHBOARDS_DIR / "frontend-nginx.json"
        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        panel_titles = [p.get("title") for p in dashboard["panels"]]
        assert any("Request" in t for t in panel_titles), "Missing request panel"
        assert any("Status" in t for t in panel_titles), "Missing status panel"

    def test_celery_dashboard_completeness(self):
        """Test that Celery dashboard is complete."""
        dashboard_path = DASHBOARDS_DIR / "celery-tasks.json"
        with open(dashboard_path, "r") as f:
            dashboard = json.load(f)

        panel_titles = [p.get("title") for p in dashboard["panels"]]
        assert any("Task" in t for t in panel_titles), "Missing task panel"
        assert any("Queue" in t for t in panel_titles), "Missing queue panel"

    def test_dashboard_uids_are_unique(self):
        """Test that all dashboard UIDs are unique."""
        uids = []
        for dashboard_file in REQUIRED_DASHBOARDS:
            dashboard_path = DASHBOARDS_DIR / dashboard_file
            with open(dashboard_path, "r") as f:
                dashboard = json.load(f)
            uid = dashboard.get("uid")
            assert uid not in uids, f"Duplicate UID: {uid}"
            uids.append(uid)


class TestDashboardProvisioning:
    """Test Grafana provisioning configuration."""

    def test_provisioning_config_exists(self):
        """Test that provisioning config exists."""
        config_path = Path(DASHBOARDS_DIR).parent / "provisioning" / "dashboards" / "dashboard-provider.yml"
        assert config_path.exists(), f"Provisioning config not found: {config_path}"

    def test_datasource_config_exists(self):
        """Test that datasource config exists."""
        config_path = Path(DASHBOARDS_DIR).parent / "provisioning" / "datasources" / "prometheus.yml"
        assert config_path.exists(), f"Datasource config not found: {config_path}"

    def test_prometheus_datasource_configured(self):
        """Test that Prometheus datasource is configured."""
        config_path = Path(DASHBOARDS_DIR).parent / "provisioning" / "datasources" / "prometheus.yml"
        with open(config_path, "r") as f:
            config = f.read()
        assert "Prometheus" in config, "Prometheus datasource not configured"
        assert "prometheus:9090" in config or "localhost:9090" in config, (
            "Prometheus URL not configured"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
