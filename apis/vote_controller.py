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

api = Namespace('vote', description='Namespace for vote service')

from core.vote_services import add_vote

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cfs_votes'
_es_type = '_doc'
_es_size = 100


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
class CreateVote(Resource):

    @access_required(access="ALL")
    @api.doc('create vote')
    def post(self):
        try:
            rs = requests.session()
            data = request.get_json()
            mandatory_fields = ['vote_ref_id', 'vote_type', 'voter_id']
            for f in mandatory_fields:
                if f not in data:
                    return {'message': 'bad request'}, 400
            for f in data:
                if f not in mandatory_fields:
                    return {'message': 'bad request'}, 400
            response = add_vote(data)
            app.logger.debug('VOTE DATA: ' + json.dumps(data))
            app.logger.debug('VOTE RESPONSE: ' + json.dumps(response))
            return response
        except Exception as e:
            raise e
