import importlib
import sys

pkg = importlib.import_module('backend.reports')
sys.modules[__name__] = pkg
try:
    sys.modules[f"{__name__}.models"] = importlib.import_module('backend.reports.models')
except Exception:
    pass
try:
    sys.modules[f"{__name__}.urls"] = importlib.import_module('backend.reports.urls')
except Exception:
    pass


