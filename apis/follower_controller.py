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

from core.user_services import get_user_details

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
        try:
            app.logger.info('Follow api called')
            print('user_id: ', user_id)
            current_user = get_jwt_identity().get('id')
            rs = requests.session()
            data = {
                'user_id': user_id,
                'followed_by': current_user
            }

            print('data: ', data)

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

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/unfollow/<string:user_id>')
class UserUnfollow(Resource):

    @access_required(access="ALL")
    @api.doc('update user_follower')
    def put(self, user_id):
        try:
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

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/status/<string:user_id>')
class FollowStatus(Resource):

    @access_required(access="ALL")
    @api.doc('Get user_follower')
    def get(self, user_id):
        try:
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

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/follower/<string:user_id>')
class FollowerList(Resource):

    @api.doc('Get user follower list')
    def get(self, user_id):
        try:
            rs = requests.session()
            must = [
                {'term': {'user_id': user_id}}
            ]
            query_json = {'query': {'bool': {'must': must}}}
            url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_followers, _es_type)
            response = rs.post(url=url, json=query_json, headers=_http_headers).json()

            if 'hits' in response:
                item_list = []
                for hit in response['hits']['hits']:
                    data = hit['_source']
                    user_id = data['followed_by']
                    try:
                        user_details = get_user_details(user_id)
                    except Exception as e:
                        app.logger.error(f'User not found {user_id}')
                        continue
                    user_data = {
                        'user_id': user_id,
                        'user_handle': user_details['username'],
                        'user_skill_color': user_details['skill_color'],
                    }
                    item_list.append(user_data)
                return item_list
            return response, 500

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/following/<string:user_id>')
class FollowingList(Resource):

    @api.doc('Get user following list')
    def get(self, user_id):
        try:
            rs = requests.session()
            must = [
                {'term': {'followed_by': user_id}}
            ]
            query_json = {'query': {'bool': {'must': must}}}
            url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_followers, _es_type)
            response = rs.post(url=url, json=query_json, headers=_http_headers).json()

            if 'hits' in response:
                item_list = []
                for hit in response['hits']['hits']:
                    data = hit['_source']
                    user_id = data['user_id']
                    print('Find User: ', user_id)
                    try:
                        user_details = get_user_details(user_id)
                    except Exception as e:
                        app.logger.error(f'User not found {user_id}')
                        continue
                    print('user_details: ', user_details)
                    user_data = {
                        'user_id': user_id,
                        'user_handle': user_details['username'],
                        'user_skill_color': user_details['skill_color'],
                    }
                    item_list.append(user_data)
                return item_list
            return response, 500

        except Exception as e:
            return {'message': str(e)}, 500

