import datetime
from pathlib import Path
import pickle
import hashlib
from functools import wraps


def cache_disk(original_function=None, cache_path=Path('__cache'), ttl=datetime.timedelta(days=1), cache_only=False, args_to_bytes_func=lambda *args, **kwargs: pickle.dumps((args, kwargs))):
    """
    """
    assert isinstance(cache_path, Path)
    assert isinstance(ttl, datetime.timedelta)
    cache_path.mkdir(exist_ok=True)

    def _decorate(function):
        @wraps(function)
        def wrapped_function(*args, **kwargs):
            cache = cache_path.joinpath(hashlib.sha1(args_to_bytes_func(*args, **kwargs)).hexdigest())
            if cache.is_file() and (
                datetime.datetime.fromtimestamp(cache.stat().st_mtime) > datetime.datetime.now() - ttl
            ):
                return pickle.load(cache.open(mode='rb'))
            if cache_only:
                return

            _return = function(*args, **kwargs)  # Wrapped function

            pickle.dump(_return, cache.open(mode='wb'))
            return _return
        return wrapped_function
    return _decorate(original_function) if callable(original_function) else _decorate
