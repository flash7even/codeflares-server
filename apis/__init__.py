from datetime import timedelta

from flask import Blueprint
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_restplus import Api

from config import Config, instances
from externel.flask_redis import redis_store
from .auth_controller import api as auth_ns
from .category_controller import api as cat_ns

blueprint = Blueprint('api', Config.APPNAME, url_prefix='/training')

api = Api(blueprint,
          title=Config.APPNAME,
          version=Config.VERSION,
          description='RESTful API for Minio Applications')

api.add_namespace(auth_ns, path='/auth')
api.add_namespace(cat_ns, path='/category')


def create_app(instance_name):
    app = Flask(__name__)
    app.config['PROPAGATE_EXCEPTIONS'] = True
    print('ENVIRONMENT NAME: ', instance_name)
    app.config.from_object(instances[instance_name])
    app.config.from_pyfile(f'{Config.BASEDIR}/redis-{instance_name}.cfg', silent=True)
    app.config.from_pyfile(f'{Config.BASEDIR}/jwt-{instance_name}.cfg', silent=True)
    app.config.from_pyfile(f'{Config.BASEDIR}/elastic-{instance_name}.cfg', silent=True)
    redis_store.init_app(app)
    CORS(app)

    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=app.config['JWT_ACCESS_TOKEN_EXPIRES_MINUTES'])
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(minutes=app.config['JWT_REFRESH_TOKEN_EXPIRES_MINUTES'])

    jwt = JWTManager()

    @jwt.token_in_blacklist_loader
    def check_if_token_is_revoked(decrypted_token):
        jti = decrypted_token['jti']
        jti = redis_store.redis_prefix_jwt_token + jti
        if redis_store.connection.exists(jti):
            return True
        return False

    jwt.init_app(app)
    app.register_blueprint(blueprint)

    return app