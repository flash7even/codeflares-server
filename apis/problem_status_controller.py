import time
import json
import requests
from flask import current_app as app
from flask import request
from flask_restplus import Namespace, Resource
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended.exceptions import *
from flask_jwt_extended import jwt_required
from jwt.exceptions import *
from commons.jwt_helpers import access_required

api = Namespace('user_problem', description='Namespace for user_problem service')

from core.problem_services import find_problems_for_user_by_status_filtered, add_user_problem_status

_http_headers = {'Content-Type': 'application/json'}

_es_user_user_problem = 'cfs_user_user_problem_edges'
_es_type = '_doc'
_es_size = 500


@api.errorhandler(NoAuthorizationError)
def handle_auth_error(e):
    return {'message': str(e)}, 401


@api.errorhandler(CSRFError)
def handle_auth_error(e):
    return {'message': str(e)}, 401


@api.errorhandler(ExpiredSignatureError)
def handle_expired_error(e):
    return {'message': 'Token has expired'}, 401


@api.errorhandler(InvalidHeaderError)
def handle_invalid_header_error(e):
    return {'message': str(e)}, 422


@api.errorhandler(InvalidTokenError)
def handle_invalid_token_error(e):
    return {'message': str(e)}, 422


@api.errorhandler(JWTDecodeError)
def handle_jwt_decode_error(e):
    return {'message': str(e)}, 422


@api.errorhandler(WrongTokenError)
def handle_wrong_token_error(e):
    return {'message': str(e)}, 422


@api.errorhandler(RevokedTokenError)
def handle_revoked_token_error(e):
    return {'message': 'Token has been revoked'}, 401


@api.errorhandler(FreshTokenRequired)
def handle_fresh_token_required(e):
    return {'message': 'Fresh token required'}, 401


@api.errorhandler(UserLoadError)
def handler_user_load_error(e):
    identity = get_jwt_identity().get('id')
    return {'message': "Error loading the user {}".format(identity)}, 401


@api.errorhandler(UserClaimsVerificationError)
def handle_failed_user_claims_verification(e):
    return {'message': 'User claims verification failed'}, 400


@api.route('/')
class CreateUserProblem(Resource):

    #@access_required(access="ALL")
    @api.doc('create user_problem')
    def post(self):
        try:
            app.logger.info('Create user_problem api called')
            data = request.get_json()
            print('data: ', data)
            if 'user_id' not in data or 'problem_id' not in data:
                return {'message': 'bad request'}, 409
            add_user_problem_status(data['user_id'], data['problem_id'], data)
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/<string:user_id>')
class SearchUserProblem(Resource):

    @api.doc('search user_problem based on post parameters')
    def post(self, user_id):
        try:
            app.logger.info('UserProblem search api called')
            param = request.get_json()
            print('param: ', param)
            status_list = param.get('status_list', ['SOLVED'])
            result = find_problems_for_user_by_status_filtered(status_list, user_id, heavy=True)
            app.logger.info('UserProblem search api completed')
            return {
                "problem_list": result
            }
        except Exception as e:
            return {'message': str(e)}, 500
