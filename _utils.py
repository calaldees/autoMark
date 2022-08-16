from functools import partial
from types import MappingProxyType

def addClass(obj, cls):
    # https://stackoverflow.com/a/11050571/3356840
    _cls = obj.__class__
    obj.__class__ = _cls.__class__(_cls.__name__ + cls.__name__, (_cls, cls), {})

def _add_methods(obj, *methods):
    for method in methods:
        setattr(obj, method.__name__, partial(method, obj))
    return obj


from typing import Mapping, Iterable
def harden(data):
    """
    >>> harden({"a": [1,2,3]})
    mappingproxy({'a': (1, 2, 3)})
    >>> harden({"a": [1,2, {3}] })
    mappingproxy({'a': (1, 2, (3,))})
    >>> harden({"a": [1,2, {"b": 2}] })
    mappingproxy({'a': (1, 2, mappingproxy({'b': 2}))})
    >>> harden([1, {"c": True, "d": 3.14, "e": {"no", "no"}}])
    (1, mappingproxy({'c': True, 'd': 3.14, 'e': ('no',)}))
    """
    if isinstance(data, Mapping):
        return MappingProxyType({k: harden(v) for k, v in data.items()})
    if isinstance(data, Iterable) and not isinstance(data, str):
        return tuple((harden(i) for i in data))
    return data
