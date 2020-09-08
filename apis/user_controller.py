from hashlib import md5
import time
import random
from datetime import timedelta
import requests, json
from flask import current_app as app, request
from flask_restplus import Resource, Namespace
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended.exceptions import *
from jwt.exceptions import *
from commons.jwt_helpers import access_required

from core.user_services import search_user, get_user_details, dtsearch_user
from core.rating_services import add_user_ratings, get_user_rating_history
from core.sync_services import user_problem_data_sync, user_training_model_sync
from core.job_services import add_pending_job
from core.rating_sync_services import user_list_sync, team_list_sync
from commons.skillset import Skill
from core.mail_services import send_email
from extensions import flask_crypto
from extensions.flask_redis import redis_store
from core.mail_services import send_email
from core.redis_services import remove_pending_job

api = Namespace('user', description='user related services')

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cfs_users'
_es_type = '_doc'
_es_size = 2000


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


def create_random_token():
    token = str(int(time.time()))
    for i in range(0, 3):
        rnd_num = str(random.randint(100000, 999999))
        token = token + ':' + rnd_num
    token = md5(token.encode(encoding='utf-8')).hexdigest()
    return token


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
            ignore_fields = ['username', 'password', 'user_role', 'email', 'skill_value',
                             'skill_title', 'solve_count', 'total_score', 'target_score']

            app.logger.info('Update user API called, id: ' + str(user_id))
            current_user = get_jwt_identity().get('id')
            if user_id != current_user:
                return {'message': 'bad request'}, 400
            rs = requests.session()
            user_data = request.get_json()

            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, user_id)
            app.logger.info('Elasticsearch query : ' + str(search_url))
            response = rs.get(url=search_url, headers=_http_headers).json()
            app.logger.info('Elasticsearch response :' + str(response))

            if 'found' in response:
                if response['found']:
                    user = response['_source']
                    for key in user_data:
                        if key not in ignore_fields and user_data[key]:
                            user[key] = user_data[key]

                    app.logger.info('Elasticsearch query : ' + str(search_url))
                    response = rs.put(url=search_url, json=user, headers=_http_headers).json()
                    app.logger.info('Elasticsearch response :' + str(response))
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
            current_user = get_jwt_identity().get('id')
            if user_id != current_user:
                return {'message': 'bad request'}, 400
            rs = requests.session()
            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, user_id)
            app.logger.info('Elasticsearch query : ' + str(search_url))
            response = rs.delete(url=search_url, headers=_http_headers).json()
            app.logger.info('Elasticsearch response :' + str(response))
            if 'found' in response:
                app.logger.info('Delete user API completed')
                return response['result'], 200
            app.logger.error('Elasticsearch down')
            return response, 500

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/admin/action/<string:user_id>')
class AdminUserControl(Resource):

    @access_required(access="admin")
    @api.doc('update user by id')
    def put(self, user_id):
        try:
            app.logger.info('Update user API called, id: ' + str(user_id))
            allowed_fields = ['user_role', 'password', 'username', 'email']

            rs = requests.session()
            user_data = request.get_json()

            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, user_id)
            response = rs.get(url=search_url, headers=_http_headers).json()

            if 'found' in response:
                if response['found']:
                    user = response['_source']
                    for key in user_data:
                        if key in allowed_fields and user_data[key]:
                            user[key] = user_data[key]

                    app.logger.info('Elasticsearch query : ' + str(search_url))
                    response = rs.put(url=search_url, json=user, headers=_http_headers).json()
                    app.logger.info('Elasticsearch response :' + str(response))
                    if 'result' in response:
                        app.logger.info('Update user API completed')
                        return response['result'], 200
                app.logger.info('User not found')
                return 'not found', 404
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

    @access_required(access="admin")
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

            skill = Skill()
            user_data['created_at'] = int(time.time())
            user_data['updated_at'] = int(time.time())
            user_data['skill_value'] = 0
            user_data['skill_title'] = skill.get_skill_title(0)
            user_data['decreased_skill_value'] = 0
            user_data['total_score'] = 0
            user_data['target_score'] = 0
            user_data['solve_count'] = 0
            user_data['contribution'] = 0
            post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type)
            response = rs.post(url=post_url, json=user_data, headers=_http_headers).json()

            if 'result' in response:
                if response['result'] == 'created':
                    app.logger.info('Create user API completed')
                    # add_user_ratings(response['_id'], 0, 0)
                    return response['_id'], 201
            return response, 500

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/register')
class RegisterUser(Resource):

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
                    return 'Username or email already exists', 200

            app.logger.info('Check done')

            token_data = {
                'username': data['username'],
                'email': data['email'],
                'token': create_random_token()
            }
            app.logger.info(f'token_data: {token_data}')

            encrypted_token = flask_crypto.encrypt_json(token_data)
            app.logger.info(f'encrypted_token 1: {encrypted_token}')
            redis_key = app.config['REDIS_PREFIX_USER_ACTIVATE'] + ':' + encrypted_token
            redis_store.connection.set(redis_key, str(user_data), timedelta(minutes=app.config['USER_ACTIVATION_TIMEOUT']))
            activation_link = f'{app.config["WEB_HOST"]}/{app.config["WEB_HOST_USER_ACTIVATION_URL"]}/{encrypted_token}'
            message_body = f'Please click the below link to activate your account:\n\n{activation_link}\n\nRegards,\nCodeflares Team'
            app.logger.info(f'message_body: {message_body}')
            send_email([data['email']], 'Account Activation', message_body)
            return {
                'token': encrypted_token
            }

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/activate/<string:encrypted_token>')
class ActivateUser(Resource):

    @api.doc('Activate new user')
    def post(self, encrypted_token):
        app.logger.info('Activate user API called')
        rs = requests.session()
        try:
            app.logger.info(f'encrypted_token: {encrypted_token}')
            encrypted_token_encoded =  encrypted_token.encode()
            token_data = flask_crypto.decrypt_json(encrypted_token_encoded)
            redis_key = app.config['REDIS_PREFIX_USER_ACTIVATE'] + ':' + encrypted_token

            if redis_store.connection.exists(redis_key):
                user_data = redis_store.connection.get(redis_key)
                user_data = user_data.replace("\'", "\"")
                user_data = json.loads(user_data)
                if user_data['email'] != token_data['email']:
                    return { 'message': 'Invalid token' }, 409
            else:
                return { 'message': 'Invalid token' }, 409

            search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index, _es_type)
            should = [
                {'match': {'username': user_data['username']}},
                {'term': {'email': user_data['email']}}
            ]
            query_params = {'query': {'bool': {'should': should}}}

            response = rs.post(url=search_url, json=query_params, headers=_http_headers).json()

            if 'hits' in response:
                if response['hits']['total']['value'] == 1:
                    app.logger.info('Username already exists')
                    return 'Username or email already exists', 200

            skill = Skill()
            user_data['created_at'] = int(time.time())
            user_data['updated_at'] = int(time.time())
            user_data['skill_value'] = 0
            user_data['skill_title'] = skill.get_skill_title(0)
            user_data['decreased_skill_value'] = 0
            user_data['total_score'] = 0
            user_data['target_score'] = 0
            user_data['solve_count'] = 0
            user_data['contribution'] = 0
            post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type)
            response = rs.post(url=post_url, json=user_data, headers=_http_headers).json()

            if 'result' in response:
                if response['result'] == 'created':
                    app.logger.info('Create user API completed')
                    add_user_ratings(response['_id'], 0, 0)
                    return response['_id'], 201
            return response, 500

        except Exception as e:
            return { 'message': 'Invalid token' }, 409


@api.route('/changepass/<string:user_id>')
class ChangePassword(Resource):

    @access_required(access='ALL')
    @api.doc('update user password')
    def put(self, user_id):
        try:
            app.logger.info(f'Attempting to update password for user {user_id}')
            rs = requests.session()

            fields = ['old_password', 'new_password']
            user_data = request.get_json()
            for field in fields:
                if user_data.get(field, None) is None:
                    return 'bad request', 400

            old_pass = md5(user_data['old_password'].encode(encoding='utf-8')).hexdigest()
            new_pass = md5(user_data['new_password'].encode(encoding='utf-8')).hexdigest()

            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, user_id)
            response = rs.get(url=search_url, headers=_http_headers).json()

            if 'found' in response:
                if response['found']:
                    data = response['_source']
                    if data['password'] != old_pass:
                        return 'Wrong password', 409
                    data['password'] = new_pass
                    upd_response = rs.put(url=search_url, json=data, headers=_http_headers)
                    if upd_response.ok:
                        app.logger.info('Password has been updated')
                        return 'updated', 200
                else:
                    app.logger.info('User does not exist')
                    return 'user not found', 404
            app.logger.error('Elasticsearch error')
            return 'internal server error', 500
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/forgotpass')
class ForgotPassword(Resource):

    @api.doc('update user password')
    def post(self):
        try:
            rs = requests.session()
            js_body = request.get_json()
            user_email = js_body['email']
            app.logger.info(f'Attempting to update password for user {user_email}')

            search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index, _es_type)
            should = [
                {'term': {'email': user_email}}
            ]
            query_params = {'query': {'bool': {'should': should}}}
            response = rs.post(url=search_url, json=query_params, headers=_http_headers).json()
            user_data = None
            if 'hits' in response:
                if response['hits']['total']['value'] == 1:
                    user_data = response['hits']['hits'][0]['_source']
                    user_data['id'] = response['hits']['hits'][0]['_id']

            if user_data is None:
                return {'message': 'user not found'}, 409

            token_data = {
                'username': user_data['username'],
                'email': user_data['email'],
                'token': create_random_token()
            }
            app.logger.info(f'token_data: {token_data}')

            encrypted_token = flask_crypto.encrypt_json(token_data)
            app.logger.info(f'encrypted_token 1: {encrypted_token}')
            redis_key = app.config['REDIS_PREFIX_USER_PASSWORD'] + ':' + encrypted_token
            redis_store.connection.set(redis_key, str(user_data), timedelta(minutes=app.config['USER_CONFIRM_PASS_TIMEOUT']))
            activation_link = f'{app.config["WEB_HOST"]}/{app.config["WEB_HOST_USER_CONFIRM_PASS_URL"]}/{encrypted_token}'
            message_body = f'Please click the below link to update your password:\n\n{activation_link}\n\nRegards,\nCodeflares Team'
            app.logger.info(f'message_body: {message_body}')
            send_email([user_email], 'Password Change', message_body)
            return {
                'token': encrypted_token
            }

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/confirmpasstoken/<string:encrypted_token>')
class ConfirmPassToken(Resource):

    @api.doc('Confirm token')
    def post(self, encrypted_token):
        app.logger.info('Confirm password token API called')
        try:
            app.logger.info(f'encrypted_token: {encrypted_token}')
            encrypted_token_encoded =  encrypted_token.encode()
            token_data = flask_crypto.decrypt_json(encrypted_token_encoded)
            redis_key = app.config['REDIS_PREFIX_USER_PASSWORD'] + ':' + encrypted_token

            if redis_store.connection.exists(redis_key):
                user_data = redis_store.connection.get(redis_key)
                user_data = user_data.replace("\'", "\"")
                user_data = json.loads(user_data)
                if user_data['email'] != token_data['email']:
                    return { 'message': 'Invalid token' }, 409
            else:
                return { 'message': 'Invalid token' }, 409

            return {
                'username': user_data['username'],
                'user_id': user_data['id'],
                'fullname': user_data['full_name'],
                'email': user_data['email'],
                'token': encrypted_token,
                'status': 'confirmed'
            }, 200

        except Exception as e:
            return { 'message': 'Invalid token' }, 409


@api.route('/confirmpass/<string:user_id>/<string:encrypted_token>')
class ConfirmPassword(Resource):

    @api.doc('update user password')
    def put(self, user_id, encrypted_token):
        try:
            app.logger.info(f'Attempting to update password for user {user_id}')
            rs = requests.session()
            encrypted_token_encoded =  encrypted_token.encode()
            token_data = flask_crypto.decrypt_json(encrypted_token_encoded)
            redis_key = app.config['REDIS_PREFIX_USER_PASSWORD'] + ':' + encrypted_token

            if redis_store.connection.exists(redis_key):
                user_data = redis_store.connection.get(redis_key)
                user_data = user_data.replace("\'", "\"")
                user_data = json.loads(user_data)
                if user_data['email'] != token_data['email']:
                    return { 'message': 'Invalid token' }, 409
            else:
                return { 'message': 'Invalid token' }, 409

            redis_store.connection.delete(redis_key)

            fields = ['new_password']
            user_data = request.get_json()
            for field in fields:
                if user_data.get(field, None) is None:
                    return 'bad request', 400

            new_pass = md5(user_data['new_password'].encode(encoding='utf-8')).hexdigest()
            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, user_id)
            response = rs.get(url=search_url, headers=_http_headers).json()

            if 'found' in response:
                if response['found']:
                    data = response['_source']
                    data['password'] = new_pass
                    upd_response = rs.put(url=search_url, json=data, headers=_http_headers)
                    if upd_response.ok:
                        app.logger.info('Password has been updated')
                        return 'updated', 200
                else:
                    app.logger.info('User does not exist')
                    return 'user not found', 404
            app.logger.error('Elasticsearch error')
            return 'internal server error', 500
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
            logged_in_user = get_jwt_identity().get('id')
            logged_in_user_details = get_user_details(logged_in_user)
            logged_in_user_role = logged_in_user_details.get('user_role', None)
            response = add_pending_job(user_id, logged_in_user_role, 'USER_SYNC')
            return response, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/sync-administration/<string:sync_type>/<string:user_id>')
class SyncAdministration(Resource):

    @access_required(access="admin")
    @api.doc('Sync-administration user by id')
    def put(self, sync_type, user_id):
        app.logger.info('Sync-administration user API called, user_id: ' + str(user_id))
        try:
            logged_in_user = get_jwt_identity().get('id')
            logged_in_user_details = get_user_details(logged_in_user)
            logged_in_user_role = logged_in_user_details.get('user_role', None)
            response = None

            if user_id == 'all':
                if sync_type == 'sync-restore':
                    response = add_pending_job(logged_in_user, logged_in_user_role, 'RESTORE_ALL_USERS')
                elif sync_type == 'sync':
                    response = add_pending_job(logged_in_user, logged_in_user_role, 'SYNC_ALL_USERS')
            else:
                if sync_type == 'sync-restore':
                    response = add_pending_job(user_id, logged_in_user_role, 'USER_SYNC_RESTORE')
                elif sync_type == 'sync':
                    response = add_pending_job(user_id, logged_in_user_role, 'USER_SYNC')

            return response, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/sync/problem-data/<string:user_id>')
class SyncProblemData(Resource):

    @access_required(access="admin")
    @api.doc('Sync user problem data by id')
    def put(self, user_id):
        app.logger.info('Sync user problem data API called, id: ' + str(user_id))
        try:
            user_problem_data_sync(user_id)
            remove_pending_job(user_id)
            app.logger.info('user_problem_data_sync done')
            return {'message': 'success'}, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/sync/training-model/<string:user_id>')
class SyncTrainingModel(Resource):

    @access_required(access="admin")
    @api.doc('Sync user training model by id')
    def put(self, user_id):
        app.logger.info('Sync user training model API called, id: ' + str(user_id))
        try:
            user_training_model_sync(user_id)
            app.logger.info('user_training_model_sync done')
            return {'message': 'success'}, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/rating-change')
class Test(Resource):

    @access_required(access="admin")
    @api.doc('Sync user training model by id')
    def post(self):
        try:
            current_user = get_jwt_identity().get('id')
            user_details = get_user_details(current_user)
            if user_details['user_role'] != 'admin':
                return {'message': 'bad request'}, 400
            user_list_sync()
            app.logger.info('user_list_sync done')
            team_list_sync()
            app.logger.info('team_list_sync done')
            return {'message': 'success'}, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/generate-crypty-key')
class GenerateKey(Resource):

    @access_required(access="admin")
    @api.doc('generate crypto key')
    def post(self):
        try:
            app.logger.info('generate-crypty-key service called')
            current_user = get_jwt_identity().get('id')
            user_details = get_user_details(current_user)
            if user_details['user_role'] != 'admin':
                return {'message': 'bad request'}, 400
            flask_crypto.generate_key()
            return {'message': 'success'}, 200
        except Exception as e:
            return {'message': str(e)}, 500
