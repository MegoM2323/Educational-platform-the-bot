"""Test bootstrap: alias modules so imports like 'backend.applications' map to real apps.

Python automatically imports sitecustomize if present, before test collection.
This ensures tests that import 'backend.*' work with INSTALLED_APPS entries
without the 'backend.' prefix.
"""
import importlib
import sys

for _mod in (
    "accounts",
    "applications",
    "materials",
    "assignments",
    "chat",
    "reports",
    "notifications",
    "payments",
    "core",
):
    try:
        sys.modules.setdefault(f"backend.{_mod}", importlib.import_module(_mod))
        sys.modules.setdefault(f"backend.{_mod}.models", importlib.import_module(f"{_mod}.models"))
    except Exception:
        # Non-fatal during early import; Django may not be configured yet
        pass


