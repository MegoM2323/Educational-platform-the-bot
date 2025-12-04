"""
Monkey patch для hyperframe compatibility с Python 3.13+

Python 3.13 удалил collections.MutableSet в пользу collections.abc.MutableSet.
Этот патч восстанавливает совместимость для старых библиотек.
"""
import collections.abc
import sys

# Добавляем обратную совместимость для collections.MutableSet
if sys.version_info >= (3, 13):
    collections.MutableSet = collections.abc.MutableSet
    collections.MutableMapping = collections.abc.MutableMapping
    collections.MutableSequence = collections.abc.MutableSequence
