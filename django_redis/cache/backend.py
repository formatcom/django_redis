import pickle
import redis
from redis import sentinel
from django.core.cache.backends.base import DEFAULT_TIMEOUT, BaseCache
from django.utils import six


class Sentinel(sentinel.Sentinel):

    def __init__(self, *args, **kwargs):
        self._master_name = kwargs.pop('master_name', 'mymaster')
        super().__init__(*args, **kwargs)

    def use_master(f):
        def _wrapped_use_master(self, *args, **kwargs):
            self._client = self.master_for(self._master_name)
            return f(self, *args, **kwargs)
        return _wrapped_use_master

    def use_slave(f):
        def _wrapped_use_slave(self, *args, **kwargs):
            self._client = self.slave_for(self._master_name)
            return f(self, *args, **kwargs)
        return _wrapped_use_slave

    @use_slave
    def get(self, *args, **kwargs):
        return self._client.get(*args, **kwargs)

    @use_master
    def set(self, *args, **kwargs):
        return self._client.set(*args, **kwargs)

    @use_master
    def decr(self, *args, **kwargs):
        return self._client.decr(*args, **kwargs)

    @use_master
    def incr(self, *args, **kwargs):
        return self._client.incr(*args, **kwargs)


class BaseRedisCache(BaseCache):

    def __init__(self, server, params):
        super().__init__(params)

        if isinstance(server, str):
            self._servers = server.split(':')
        else:
            _servers = []
            for i in server:
                if isinstance(i, str):
                    _servers.append(i.split(':'))
            self._servers = _servers

        self._options = params.get('OPTIONS') or {}

        _options = {}
        for k, v in self._options.items():
            _options[k.lower()] = v

        self._options = _options
        self._master_host = self._options.pop('master_host', None)

    @property
    def _cache(self):
        raise NotImplementedError('`_cache` must be implemented.')

    def get_backend_timeout(self, timeout=DEFAULT_TIMEOUT):

        if timeout == DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        if timeout <= 0:
            timeout = None

        return None if timeout is None else int(timeout)

    def encode(self, value):
        if isinstance(value, bool) or not isinstance(value, six.integer_types):
            value = pickle.dumps(value)
        return value

    def decode(self, value):
        if isinstance(value, six.binary_type):
            try:
                value = pickle.loads(value)
            except:
                pass
        return value

    def add(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version)
        return self._cache.set(key, self.encode(value),
                nx=True, ex=self.get_backend_timeout(timeout))

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version)
        if not self._cache.set(key, self.encode(value),
                ex=self.get_backend_timeout(timeout)):
            self._cache.delete(key)

    def incr(self, key, delta=1, version=None):
        key = self.make_key(key, version)
        return self._cache.incr(key, delta)

    def decr(self, key, delta=1, version=None):
        key = self.make_key(key, version)
        return self._cache.decr(key, delta)

    def get(self, key, default=None, version=None):
        key = self.make_key(key, version)
        value = self._cache.get(key)
        if not value:
            value = default
        else:
            value = self.decode(value)
        return value

    def delete(self, key, version=None):
        key = self.make_key(key, version)
        self._cache.delete(key)

    def touch(self, key, timeout=DEFAULT_TIMEOUT, version=None):
        key = self.make_key(key, version)
        return self._cache.expire(key, self.get_backend_timeout(timeout))

    def clear(self):
        self._cache.flushdb()

    def close(self, **kwargs):
        self._cache.close()


class RedisCache(BaseRedisCache):

    @property
    def _cache(self):
        if getattr(self, '_client', None) is None:
            host, port = self._servers
            self._client = redis.Redis(host=host, port=port, **self._options)
        return self._client


class SentinelCache(BaseRedisCache):

    @property
    def _cache(self):
        if getattr(self, '_client', None) is None:
            self._client = Sentinel(self._servers, **self._options)
        return self._client

