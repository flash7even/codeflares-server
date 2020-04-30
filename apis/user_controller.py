from hashlib import md5

import requests, json
from flask import current_app as app, request
from flask_restplus import Resource, Namespace
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended.exceptions import *
from jwt.exceptions import *
from commons.jwt_helpers import access_required

from core.user_services import synch_user_problem

api = Namespace('user', description='user related services')

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cp_training_users'
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


@api.route('/<string:user_id>')
class User(Resource):

    @access_required(access='ALL')
    @api.doc('get user by id')
    def get(self, user_id):
        app.logger.info('Get user API called, id: ' + str(user_id))
        rs = requests.session()

        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, user_id)
        app.logger.debug('Elasticsearch query : ' + str(search_url))
        response = rs.get(url=search_url, headers=_http_headers).json()
        app.logger.debug('Elasticsearch response :' + str(response))
        if 'found' in response:
            if response['found']:
                user = response['_source']
                user['id'] = response['_id']
                app.logger.info('Get user API completed')
                return user, 200
            app.logger.warning('User not found')
            return {'found': response['found']}, 404
        app.logger.error('Elasticsearch down')
        return response, 500

    @access_required(access='ALL')
    @api.doc('update user by id')
    def put(self, user_id):
        ignore_fields = ['username', 'password']

        app.logger.info('Update user API called, id: ' + str(user_id))
        rs = requests.session()
        user_data = request.get_json()

        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, user_id)
        app.logger.debug('Elasticsearch query : ' + str(search_url))
        response = rs.get(url=search_url, headers=_http_headers).json()
        app.logger.debug('Elasticsearch response :' + str(response))

        if 'found' in response:
            if response['found']:
                user = response['_source']
                for key in user_data:
                    if key not in ignore_fields and user_data[key]:
                        user[key] = user_data[key]

                app.logger.debug('Elasticsearch query : ' + str(search_url))
                response = rs.put(url=search_url, json=user, headers=_http_headers).json()
                app.logger.debug('Elasticsearch response :' + str(response))
                if 'result' in response:
                    app.logger.info('Update user API completed')
                    return response['result'], 200
            app.logger.info('User not found')
            return 'not found', 404
        app.logger.error('Elasticsearch down')
        return response, 500

    @access_required(access='ALL')
    @api.doc('delete user by id')
    def delete(self, user_id):
        app.logger.info('Delete user API called, id: ' + str(user_id))
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, user_id)
        app.logger.debug('Elasticsearch query : ' + str(search_url))
        response = rs.delete(url=search_url, headers=_http_headers).json()
        app.logger.debug('Elasticsearch response :' + str(response))
        if 'found' in response:
            app.logger.info('Delete user API completed')
            return response['result'], 200
        app.logger.error('Elasticsearch down')
        return response, 500


@api.route('/')
class CreateUser(Resource):

    @staticmethod
    def __validate_json(json_data):
        mandatory_fields = ['username', 'password', 'email', 'full_name', 'user_role']
        for key, value in json_data.items():
            if key in mandatory_fields and not value:
                raise KeyError('Mandatory field missing')
        return json_data

    #@access_required(access="ALL")
    @api.doc('create new user')
    def post(self):
        app.logger.info('Create user API called')
        rs = requests.session()
        data = request.get_json()

        try:
            user_data = self.__validate_json(data)
            user_data['password'] = md5(user_data['password'].encode(encoding='utf-8')).hexdigest()
        except (IOError, KeyError):
            app.logger.warning('Bad request')
            return 'bad request', 400

        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index, _es_type)
        should = [
            {'match': {'username': data['username']}},
            {'term': {'email': data['email']}}
        ]
        query_params = {'query': {'bool': {'should': should}}}

        response = rs.post(url=search_url, json=query_params, headers=_http_headers).json()

        if 'hits' in response:
            if response['hits']['total']['value'] == 1:
                app.logger.info('Username already exists')
                return 'Username already exists', 200

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type)
        response = rs.post(url=post_url, json=user_data, headers=_http_headers).json()

        if 'result' in response:
            if response['result'] == 'created':
                app.logger.info('Create user API completed')
                return response['_id'], 201
        return response, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchUser(Resource):

    @api.doc('search users based on post parameters')
    def post(self, page=0):
        app.logger.info('Search user API called')
        param = request.get_json()

        must = []

        text_fields = ['username', 'email', 'mobile']
        keyword_fields = ['user_role']

        for k in text_fields:
            if k in param:
                must.append({'match': {k: param[k]}})

        for k in keyword_fields:
            if k in param:
                must.append({'term': {k: param[k]}})

        query_json = {'query': {'bool': {'must': must}}}

        query_json['from'] = page * _es_size
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index, _es_type)

        response = requests.session().post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            data = []
            for hit in response['hits']['hits']:
                user = hit['_source']
                user['id'] = hit['_id']

                user['rating'] = 1988
                user['title'] = 'Candidate Master'
                user['max_rating'] = 1988
                user['solve_count'] = 890
                user['follower'] = 921
                user['following'] = 530

                data.append(user)
            app.logger.info('Search user API completed')
            return {
                'user_list': data
            }
        app.logger.error('Elasticsearch down, response : ' + str(response))
        return {'message': 'internal server error'}, 500


@api.route('/sync/<string:user_id>')
class Sync(Resource):

    @api.doc('Sync user by id')
    def put(self, user_id):
        app.logger.info('Get user API called, id: ' + str(user_id))
        try:
            synch_user_problem(user_id)
            return {'message': 'success'}, 200
        except Exception as e:
            return {'message': 'Internal server error'}, 500
