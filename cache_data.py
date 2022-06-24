import time
from functools import wraps
from threading import Thread, Lock

_cache = {}
_mutex = Lock()
_no_data = object()


class _ArgsCache:
	def __init__(self, args=(), kwargs={}):
		self.args = tuple(args)
		self.kwargs = tuple(kwargs.items())

	def __eq__(self, value, /):
		if not isinstance(value, type(self)):
			return False
		return self.args == value.args and self.kwargs == value.kwargs

	def __hash__(self):
		return hash((self.args, self.kwargs))


def _remove_value_later(func, argscache, cache_max):
	time.sleep(cache_max)
	try:
		_mutex.acquire()
		del (_cache[func][argscache])
		if not _cache[func]:
			del (_cache[func])
	except KeyError:
		pass
	finally:
		_mutex.release()


def cache_return(cache_max):
	def deco(func):
		@wraps(func)
		def overwrite(*args, **kwargs):
			argscache = _ArgsCache(args, kwargs)
			try:
				_mutex.acquire()
				_cache.setdefault(func, {})
				_cache[func].setdefault(argscache, _no_data)
				if _cache[func][argscache] is not _no_data:
					return _cache[func][argscache]
			finally:
				_mutex.release()
			ret = func(*args, **kwargs)
			try:
				_mutex.acquire()
				_cache[func][argscache] = ret
				if cache_max is not None:
					Thread(target=_remove_value_later, args=(func, argscache, cache_max), daemon=True).start()
			finally:
				_mutex.release()
			return ret

		return overwrite

	return deco


def empty_cache():
	_cache.clear()


def empty_function_cache(function):
	try:
		del(_cache[function])
	except KeyError:
		pass
