import importlib
import sys

# Ensure both import styles work: `applications` and `backend.applications`
_apps = (
    "accounts",
    "applications",
    "materials",
    "assignments",
    "chat",
    "reports",
    "notifications",
    "payments",
    "core",
)

for _mod in _apps:
    try:
        pkg = importlib.import_module(_mod)
        sys.modules.setdefault(f"backend.{_mod}", pkg)
        try:
            sys.modules.setdefault(f"backend.{_mod}.models", importlib.import_module(f"{_mod}.models"))
        except Exception:
            pass
    except Exception:
        pass


