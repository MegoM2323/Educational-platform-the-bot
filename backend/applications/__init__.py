import importlib
import sys

# Redirect backend.applications* imports to top-level applications package
pkg = importlib.import_module('applications')
sys.modules[__name__] = pkg
try:
    sys.modules[f"{__name__}.models"] = importlib.import_module('applications.models')
except Exception:
    pass

