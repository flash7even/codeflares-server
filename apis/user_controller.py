from hashlib import md5
import time
import requests, json
from flask import current_app as app, request
from flask_restplus import Resource, Namespace
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended.exceptions import *
from jwt.exceptions import *
from commons.jwt_helpers import access_required

from core.user_services import search_user, get_user_details, get_user_rating_history, dtsearch_user
from core.rating_services import add_user_ratings
from core.sync_services import user_problem_data_sync, user_training_model_sync
from core.job_services import add_pending_job

api = Namespace('user', description='user related services')

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cfs_users'
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

    @api.doc('get user by id')
    def get(self, user_id):
        try:
            app.logger.info('Get user API called, id: ' + str(user_id))
            data = get_user_details(user_id)
            data['rating_history'] = get_user_rating_history(user_id)
            return data
        except Exception as e:
            return {'message': str(e)}, 500

    @access_required(access="ALL")
    @api.doc('update user by id')
    def put(self, user_id):
        try:
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

        except Exception as e:
            return {'message': str(e)}, 500

    @access_required(access='ALL')
    @api.doc('delete user by id')
    def delete(self, user_id):
        try:
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

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/')
class CreateUser(Resource):

    @staticmethod
    def __validate_json(json_data):
        mandatory_fields = ['username', 'password', 'email', 'full_name', 'user_role']
        for key, value in json_data.items():
            if key in mandatory_fields and not value:
                raise KeyError('Mandatory field missing')
        return json_data

    @api.doc('create new user')
    def post(self):
        app.logger.info('Create user API called')
        rs = requests.session()
        data = request.get_json()
        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        try:
            user_data = self.__validate_json(data)
            user_data['password'] = md5(user_data['password'].encode(encoding='utf-8')).hexdigest()
        except (IOError, KeyError):
            app.logger.warning('Bad request')
            return 'bad request', 400

        try:
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
                    add_user_ratings(response['_id'], 0, 0)
                    return response['_id'], 201
            return response, 500

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchUser(Resource):

    @api.doc('search users based on post parameters')
    def post(self, page=0):
        app.logger.info('Search user API called')
        try:
            param = request.get_json()
            user_list = search_user(param, page*_es_size, _es_size)
            return {
                'user_list': user_list
            }

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/skilled', defaults={'page': 0})
@api.route('/search/skilled/<int:page>')
class SearchUser(Resource):

    @api.doc('search users based on post parameters')
    def post(self, page=0):
        app.logger.info('Search user API called')
        try:
            param = request.get_json()
            size = param.get('size', _es_size)
            param.pop('size', None)
            user_list = search_user(param, page*size, size, sort_by='skill_value', sort_order='desc')
            return {
                'user_list': user_list
            }

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/dtsearch')
class SearchUser(Resource):

    @api.doc('search users based on post parameters')
    def post(self):
        try:
            app.logger.info('User dtsearch api called')
            param = request.get_json()
            draw = param['draw']
            start = param['start']
            length = param['length']
            search = param['search']['value']

            print(json.dumps(param))
            print('search: ', search)

            param_body = {}
            if len(search) > 0:
                param_body['filter'] = search

            sort_by = 'skill_value'
            sort_order = 'asc'

            if 'sort_by' in param:
                sort_by = param['sort_by']
                sort_order = param['sort_order']

            user_stat = dtsearch_user(param_body, start, length, sort_by, sort_order)
            resp = {
                'draw': draw,
                'recordsTotal': user_stat['total'],
                'recordsFiltered': user_stat['total'],
                'data': user_stat['user_list'],
            }
            print(resp)
            return resp
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/solved-count', defaults={'page': 0})
@api.route('/search/solved-count/<int:page>')
class SearchUser(Resource):

    @api.doc('search users based on post parameters')
    def post(self, page=0):
        app.logger.info('Search user API called')
        try:
            param = request.get_json()
            size = param.get('size', _es_size)
            param.pop('size', None)
            user_list = search_user(param, page*size, size, sort_by='solve_count', sort_order='desc')
            return {
                'user_list': user_list
            }

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/contributor', defaults={'page': 0})
@api.route('/search/contributor/<int:page>')
class SearchUser(Resource):

    @api.doc('search users based on post parameters')
    def post(self, page=0):
        app.logger.info('Search user API called')
        try:
            param = request.get_json()
            size = param.get('size', _es_size)
            param.pop('size', None)
            user_list = search_user(param, page*size, size, sort_by='contribution', sort_order='desc')
            return {
                'user_list': user_list
            }

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/sync/<string:user_id>')
class Sync(Resource):

    @access_required(access="ALL")
    @api.doc('Sync user by id')
    def put(self, user_id):
        app.logger.info('Sync user API called, id: ' + str(user_id))
        try:
            add_pending_job(user_id, 'USER_SYNC')
            return {'message': 'success'}, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/sync/problem-data/<string:user_id>')
class SyncProblemData(Resource):

    @access_required(access="ALL")
    @api.doc('Sync user problem data by id')
    def put(self, user_id):
        app.logger.info('Sync user problem data API called, id: ' + str(user_id))
        try:
            user_problem_data_sync(user_id)
            app.logger.info('user_problem_data_sync done')
            return {'message': 'success'}, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/sync/training-model/<string:user_id>')
class SyncTrainingModel(Resource):

    @access_required(access="ALL")
    @api.doc('Sync user training model by id')
    def put(self, user_id):
        app.logger.info('Sync user training model API called, id: ' + str(user_id))
        try:
            user_training_model_sync(user_id)
            app.logger.info('user_training_model_sync done')
            return {'message': 'success'}, 200
        except Exception as e:
            return {'message': str(e)}, 500

