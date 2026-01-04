import importlib
import sys
import types

pkg = importlib.import_module('backend.materials')
sys.modules[__name__] = pkg
try:
    sys.modules[f"{__name__}.models"] = importlib.import_module('backend.materials.models')
except Exception:
    pass


def _make_lazy_module(backend_module_name):
    """Create a lazy-loading module proxy"""
    class _LazyModule(types.ModuleType):
        def __init__(self, name, backend_name):
            super().__init__(name)
            self._backend_name = backend_name
            self._loaded = None

        def __getattr__(self, name):
            if name in ('_backend_name', '_loaded'):
                return super().__getattribute__(name)
            if self._loaded is None:
                self._loaded = importlib.import_module(self._backend_name)
            return getattr(self._loaded, name)

        def __dir__(self):
            if self._loaded is None:
                self._loaded = importlib.import_module(self._backend_name)
            return dir(self._loaded)

    return _LazyModule(backend_module_name.split('.')[-1], backend_module_name)


# Register URL modules as lazy loaders
sys.modules['materials.urls'] = _make_lazy_module('backend.materials.urls')
sys.modules['materials.student_urls'] = _make_lazy_module('backend.materials.student_urls')
sys.modules['materials.teacher_urls'] = _make_lazy_module('backend.materials.teacher_urls')


