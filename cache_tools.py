import datetime
from pathlib import Path
import pickle
import hashlib
from functools import wraps

import logging
log = logging.getLogger(__name__)


class DoNotPersistCacheException(Exception):
    pass


def cache_disk(original_function=None, cache_path=Path('__cache'), ttl=datetime.timedelta(days=1), cache_only=False, args_to_bytes_func=lambda *args, **kwargs: pickle.dumps((args, kwargs))):
    """
    TODO: doctests with tempfile.tempdir
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
                log.info(f'loading from cache {args=} {kwargs=}')
                return pickle.load(cache.open(mode='rb'))
            if cache_only:
                log.debug(f'cache_only - refusing to run original function')
                return

            try:
                _return = function(*args, **kwargs)  # Wrapped function
            except DoNotPersistCacheException as ex:
                return

            log.info(f'persisting to cache {args=} {kwargs=}')
            pickle.dump(_return, cache.open(mode='wb'))
            return _return
        return wrapped_function
    return _decorate(original_function) if callable(original_function) else _decorate
