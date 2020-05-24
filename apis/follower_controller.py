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

api = Namespace('user_follower', description='Namespace for user_follower service')


_http_headers = {'Content-Type': 'application/json'}

_es_index_followers = 'cfs_followers'
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


@api.route('/follow/<string:user_id>')
class UserFollow(Resource):

    @access_required(access="ALL")
    @api.doc('update user_follower')
    def put(self, user_id):
        current_user = get_jwt_identity().get('id')
        rs = requests.session()
        data = {
            'user_id': user_id,
            'followed_by': current_user
        }
        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_followers, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        print('response: ', response)

        if 'result' in response and response['result'] == 'created':
            app.logger.info('Create comment method completed')
            return response['_id'], 201
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500


@api.route('/unfollow/<string:user_id>')
class UserUnfollow(Resource):

    @access_required(access="ALL")
    @api.doc('update user_follower')
    def put(self, user_id):
        current_user = get_jwt_identity().get('id')
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'followed_by': current_user}},
        ]
        query_json = {'query': {'bool': {'must': must}}}
        url = 'http://{}/{}/{}/_delete_by_query'.format(app.config['ES_HOST'], _es_index_followers, _es_type)
        response = rs.post(url=url, json=query_json, headers=_http_headers).json()
        return response, 200


@api.route('/status/<string:user_id>')
class FollowStatus(Resource):

    @access_required(access="ALL")
    @api.doc('Get user_follower')
    def get(self, user_id):
        current_user = get_jwt_identity().get('id')
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'followed_by': current_user}},
        ]
        query_json = {'query': {'bool': {'must': must}}}
        url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_followers, _es_type)
        response = rs.post(url=url, json=query_json, headers=_http_headers).json()

        if 'hits' in response:
            if response['hits']['total']['value'] > 0:
                return {
                    'status': 'following'
                }
            return {
                'status': 'unknown'
            }

        return response, 500

