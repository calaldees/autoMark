import json
from functools import partial
from types import MappingProxyType
from typing import Mapping, Iterable
import datetime


def addClass(obj, cls):
    # https://stackoverflow.com/a/11050571/3356840
    _cls = obj.__class__
    obj.__class__ = _cls.__class__(_cls.__name__ + cls.__name__, (_cls, cls), {})

def _add_methods(obj, *methods):
    for method in methods:
        setattr(obj, method.__name__, partial(method, obj))
    return obj



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


class JSONObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        """
        Used with json lib to serialize json output
        e.g
        text = json.dumps(result, cls=JSONObjectEncoder)
        """
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, datetime.timedelta):
            return obj.total_seconds()
        if isinstance(obj, set):
            return tuple(obj)
        if isinstance(obj, MappingProxyType):
            return dict(obj)
        # Let the base class default method raise the TypeError
        return super().default(obj)
