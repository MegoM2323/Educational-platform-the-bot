import importlib
import sys

pkg = importlib.import_module('backend.chat')
sys.modules[__name__] = pkg
try:
    sys.modules[f"{__name__}.models"] = importlib.import_module('backend.chat.models')
except Exception:
    pass


