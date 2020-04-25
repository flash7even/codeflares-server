from datetime import timedelta
from hashlib import md5

import requests
from flask import request, current_app as app
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_refresh_token_required, get_jwt_identity, \
    jwt_required, get_raw_jwt
from flask_jwt_extended.exceptions import *
from flask_restplus import Resource, Namespace
from jwt.exceptions import *

from extensions.flask_redis import redis_store

api = Namespace('auth', description='auth related services')
_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cp_training_users'
_es_type = '_doc'

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


@api.route('/login')
class Login(Resource):

    def post(self):
        rs = requests.session()
        auth_data = request.get_json()
        app.logger.info("Authorization called")
        if 'username' in auth_data and 'password' in auth_data:
            username = auth_data['username']
            password = md5(auth_data['password'].encode(encoding='utf-8')).hexdigest()
        else:
            app.logger.info("Bad request, authorization failed")
            return "bad request", 400

        auth_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index, _es_type)
        auth_query = {
            'query': {'bool': {'must': [{'match': {'username': username}}, {'match': {'password': password}}]}}}
        response = rs.post(url=auth_url, json=auth_query, headers=_http_headers).json()

        if 'hits' in response:
            if response['hits']['total']['value'] == 1:
                data = response['hits']['hits'][0]['_source']
                print("DATA         ", data)
                data['id'] = response['hits']['hits'][0]['_id']
                jwt_data = {'id': data['id'], 'username': data['username'], 'full_name': data['full_name'],
                            'user_role': data['user_role']}
                data['access_token'] = create_access_token(identity=jwt_data)
                data['refresh_token'] = create_refresh_token(identity=jwt_data)
                app.logger.info("login successful")
                return data, 200
            else:
                app.logger.info("Unauthorized")
                return {"message": "unauthorized"}, 401
        return response, 500


@api.route('/refresh')
class Refresh(Resource):

    @jwt_refresh_token_required
    def post(self):
        rs = requests.session()
        app.logger.info("refresh called")
        current_user = get_jwt_identity().get('id')
        auth_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, current_user)
        response = rs.get(url=auth_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                jwt_data = {'id': data['id'], 'username': data['username'], 'full_name': data['full_name'],
                            'user_role': data['user_role']}
                data['access_token'] = create_access_token(identity=jwt_data)
                data['refresh_token'] = create_refresh_token(identity=jwt_data)
                app.logger.info("refresh successful")
                return data, 200
            else:
                app.logger.info("Unauthorized")
                return {"message": "unauthorized"}, 401
        return response, 500


@api.route('/logout/at')
class Logout(Resource):

    @jwt_required
    def post(self):
        app.logger.info("logout at called")
        jti = get_raw_jwt()['jti']
        jti = redis_store.redis_prefix_jwt_token + jti
        redis_store.connection.set(jti, 1 , timedelta(minutes=app.config['JWT_ACCESS_TOKEN_EXPIRES_MINUTES']))
        app.logger.info("logout access successful")
        return {"message": "Access token revoked"}, 200


@api.route('/logout/rt')
class Logout(Resource):

    @jwt_refresh_token_required
    def post(self):
        app.logger.info("logout rt called")
        jti = get_raw_jwt()['jti']
        jti = redis_store.redis_prefix_jwt_token + jti
        redis_store.connection.set(jti, 1 , timedelta(minutes=app.config['JWT_REFRESH_TOKEN_EXPIRES_MINUTES']))
        app.logger.info("logout refresh successful")
        return {"msg": "Refresh token revoked"}, 200


