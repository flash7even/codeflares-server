from datetime import timedelta

import os
from flask import Blueprint
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_restplus import Api

from extensions.flask_redis import redis_store
from config import Config, instances

from .auth_controller import api as auth_ns
from .category_controller import api as cat_ns
from .problem_controller import api as prob_ns
from .onlinejudge_controller import api as oj_ns
from .user_controller import api as user_ns
from .training_controller import api as train_ns
from .team_controller import api as team_ns
from .classroom_class_controller import api as classroom_class_ns
from .classroom_task_controller import api as classroom_task_ns
from .problem_status_controller import api as problem_status_ns
from .notification_controller import api as notify_ns
from .contest_controller import api as contest_ns
from .blog_controller import api as blog_ns
from .comment_controller import api as comment_ns
from .vote_controller import api as vote_ns
from .resource_controller import api as resource_ns
from .follower_controller import api as follower_ns
from .contact_us_controller import api as contact_us_ns
from .job_controller import api as job_ns
from .rating_controller import api as rating_ns
from .classroom_controller import api as classroom_ns

blueprint = Blueprint('api', Config.APPNAME, url_prefix='/api')

api = Api(blueprint,
          title=Config.APPNAME,
          version=Config.VERSION,
          description='RESTful API for Minio Applications')

api.add_namespace(auth_ns, path='/auth')
api.add_namespace(user_ns, path='/user')
api.add_namespace(prob_ns, path='/problem')
api.add_namespace(cat_ns, path='/category')
api.add_namespace(oj_ns, path='/oj')
api.add_namespace(train_ns, path='/training')
api.add_namespace(team_ns, path='/team')
api.add_namespace(classroom_ns, path='/classroom')
api.add_namespace(classroom_class_ns, path='/classroom/class')
api.add_namespace(classroom_task_ns, path='/classroom/task')
api.add_namespace(problem_status_ns, path='/problem/status')
api.add_namespace(notify_ns, path='/notification')
api.add_namespace(contest_ns, path='/contest')
api.add_namespace(blog_ns, path='/blog')
api.add_namespace(comment_ns, path='/comment')
api.add_namespace(vote_ns, path='/vote')
api.add_namespace(resource_ns, path='/resource')
api.add_namespace(follower_ns, path='/follower')
api.add_namespace(contact_us_ns, path='/contact/us')
api.add_namespace(job_ns, path='/job')
api.add_namespace(rating_ns, path='/rating')


def create_app(instance_name):
    app = Flask(__name__)
    app.config['PROPAGATE_EXCEPTIONS'] = True
    print('ENVIRONMENT NAME: ', instance_name)
    app.config.from_object(instances[instance_name])
    app.config.from_pyfile(f'{Config.BASEDIR}/config-{instance_name}.cfg', silent=True)
    redis_store.init_app(app)
    CORS(app)

    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 100000
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 100000

    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
    app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASSWORD')
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = True

    app.config['LIGHTOJ_USERNAME'] = os.getenv('LIGHTOJ_USERNAME')
    app.config['LIGHTOJ_PASSWORD'] = os.getenv('LIGHTOJ_PASSWORD')

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
