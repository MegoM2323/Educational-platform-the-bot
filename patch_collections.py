# Monkey patch для Python 3.13 совместимости
import collections
import collections.abc

if not hasattr(collections, 'MutableSet'):
    collections.MutableSet = collections.abc.MutableSet

if not hasattr(collections, 'Mapping'):
    collections.Mapping = collections.abc.Mapping
    
if not hasattr(collections, 'Iterable'):
    collections.Iterable = collections.abc.Iterable
    
if not hasattr(collections, 'Callable'):
    collections.Callable = collections.abc.Callable

print("Collections compatibility patch applied")
