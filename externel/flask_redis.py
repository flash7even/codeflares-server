import redis
from flask import current_app, g


class FlaskRedis:

    def __init__(self, app=None):
        self.app = app
        self.redis_prefix_mqtt = None
        self.redis_prefix_jwt_token = None
        self.redis_port = None
        self.redis_host = None
        self.redis_client = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.redis_prefix_mqtt = app.config['REDIS_PREFIX_MQTT'] + ':'
        self.redis_prefix_jwt_token = app.config['REDIS_PREFIX_JWT_TOKEN'] + ':'
        self.redis_host = app.config['REDIS_HOST']
        self.redis_port = app.config['REDIS_PORT']
        self.redis_client = redis.Redis(host = self.redis_host, port=self.redis_port, decode_responses=True,  db=0)

        @app.teardown_appcontext
        def _teardown(response_or_exception):
            print(response_or_exception)
            db = g.pop('db', None)
            if db:
                print("redis disconnected")
                del db

    def _get_app(self):
        if self.app:
            return self.app
        if current_app:
            return current_app
        raise RuntimeError('No application found.')

    def _connect(self):
        redis_client = redis.Redis(host=self.redis_host, port=self.redis_port, decode_responses=True, db=0)
        print("---------------------Connected to Redis----------------------")
        return redis_client

    @property
    def connection(self):
        print('Inside redis connection')
        if 'db' not in g:
            g.db = self._connect()
        return g.db


redis_store = FlaskRedis()