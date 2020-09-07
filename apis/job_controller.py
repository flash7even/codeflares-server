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

api = Namespace('user_job', description='Namespace for user_job service')

from core.job_services import search_jobs, update_pending_job

_http_headers = {'Content-Type': 'application/json'}

_es_user_user_job = 'cfs_jobs'
_es_type = '_doc'
_es_size = 50


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


@api.route('/<string:job_id>')
class UpdateJob(Resource):

    @access_required(access="admin")
    @api.doc('update job_id based on post parameters')
    def put(self, job_id):
        try:
            app.logger.info('job update api called')
            param = request.get_json()
            update_pending_job(job_id, param['status'])
            return 'successful'
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchJob(Resource):

    @api.doc('search job based on post parameters')
    def post(self, page = 0):
        try:
            app.logger.info('UserJob search api called')
            param = request.get_json()
            print('param; ', param)
            job_list = search_jobs(param, page, _es_size)
            return {
                'job_list': job_list
            }
        except Exception as e:
            return {'message': str(e)}, 500
