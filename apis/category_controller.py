import time

import requests
from flask import current_app as app
from flask import request
from flask_restplus import Namespace, Resource
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended.exceptions import *
from flask_jwt_extended import jwt_required
from jwt.exceptions import *
from commons.jwt_helpers import access_required

api = Namespace('category', description='Namespace for category service')

from core.category_services import add_category_category_dependency, get_category_id_from_name, search_categories
from core.training_model_services import category_wise_problem_solve_for_user

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cp_training_categories'
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


@api.route('/<string:category_id>')
class CategoryByID(Resource):

    @api.doc('get category details by id')
    def get(self, category_id):
        try:
            app.logger.info('Get category_details api called')
            rs = requests.session()
            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, category_id)
            response = rs.get(url=search_url, headers=_http_headers).json()
            print(response)
            if 'found' in response:
                if response['found']:
                    data = response['_source']
                    data['id'] = response['_id']
                    app.logger.info('Get category_details api completed')
                    return data, 200
                app.logger.warning('Category not found')
                return {'found': response['found']}, 404
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500
        except Exception as e:
            return {'message': str(e)}, 500

    @access_required(access="ALL")
    @api.doc('update category by id')
    def put(self, category_id):
        try:
            app.logger.info('Update category_details api called')
            rs = requests.session()
            post_data = request.get_json()

            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, category_id)
            response = rs.get(url=search_url, headers=_http_headers).json()
            print(response)
            if 'found' in response:
                if response['found']:
                    data = response['_source']
                    for key, value in post_data.items():
                        data[key] = value
                    data['updated_at'] = int(time.time())
                    response = rs.put(url=search_url, json=data, headers=_http_headers).json()
                    if 'result' in response:
                        app.logger.info('Update category_details api completed')
                        return response['result'], 200
                    else:
                        app.logger.error('Elasticsearch down, response: ' + str(response))
                        return response, 500
                app.logger.warning('Category not found')
                return {'message': 'not found'}, 404
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500
        except Exception as e:
            return {'message': str(e)}, 500

    @access_required(access="ALL")
    @api.doc('delete category by id')
    def delete(self, category_id):
        try:
            app.logger.info('Delete category_details api called')
            rs = requests.session()
            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, category_id)
            response = rs.delete(url=search_url, headers=_http_headers).json()
            print(response)
            if 'result' in response:
                if response['result'] == 'deleted':
                    app.logger.info('Delete category_details api completed')
                    return response['result'], 200
                else:
                    return response['result'], 400
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/')
class CreateCategory(Resource):

    #@access_required(access="ALL")
    @api.doc('create category')
    def post(self):
        try:
            app.logger.info('Create category api called')
            rs = requests.session()
            data = request.get_json()

            data['created_at'] = int(time.time())
            data['updated_at'] = int(time.time())

            category_dependency_list = []
            if 'category_dependency_list' in data:
                category_dependency_list = data['category_dependency_list']
                data.pop('category_dependency_list', None)

            post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type)
            response = rs.post(url=post_url, json=data, headers=_http_headers).json()

            if 'result' in response and response['result'] == 'created':
                for cat in category_dependency_list:
                    category_id_2 = cat.get('category_id', None)
                    if category_id_2 is None:
                        category_id_2 = get_category_id_from_name(cat['category_name'])
                    edge = {
                        'category_id_1': response['_id'],
                        'category_id_2': category_id_2,
                        'dependency_factor': cat['factor']
                    }
                    add_category_category_dependency(edge)
                app.logger.info('Create category api completed')
                return response['_id'], 201
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/dependency')
class CreateCategory(Resource):

    #@access_required(access="ALL")
    @api.doc('add category dependency')
    def post(self):
        try:
            app.logger.info('Add category dependency api called')
            rs = requests.session()
            data = request.get_json()

            category_id_1 = data.get('category_id', None)
            if category_id_1 is None:
                category_id_1 = get_category_id_from_name(data['category_name'])

            cat_list = data['category_dependency_list']
            for cat in cat_list:
                category_id_2 = cat.get('category_id', None)
                if category_id_2 is None:
                    category_id_2 = get_category_id_from_name(cat['category_name'])
                edge = {
                    'category_id_1': category_id_1,
                    'category_id_2': category_id_2,
                    'dependency_factor': cat['factor']
                }
                add_category_category_dependency(edge)
            app.logger.info('Add category dependency api completed')
            return {'message': 'success'}, 201
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchCategory(Resource):

    @api.doc('search category based on post parameters')
    def post(self, page=0):
        try:
            app.logger.info('Category search api called')
            param = request.get_json()
            result = search_categories(param, page*_es_size, _es_size)
            app.logger.info('Category search api completed')
            print(result)
            return {
                "category_list": result
            }
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/heavy', defaults={'page': 0})
@api.route('/search/heavy/<int:page>')
class SearchCategory(Resource):

    @api.doc('search category based on post parameters')
    def post(self, page=0):
        try:
            app.logger.info('Category search api called')
            param = request.get_json()
            result = search_categories(param, page*_es_size, _es_size, heavy=True)
            app.logger.info('Category search api completed')
            print(result)
            return {
                "category_list": result
            }
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/solved/search/user/<string:user_id>')
class CategoryWiseSolvedUser(Resource):

    @api.doc('search category based on post parameters')
    def get(self, user_id):
        try:
            app.logger.info('Category search api called')
            result = category_wise_problem_solve_for_user(user_id)
            app.logger.info('Category search api completed')
            return {
                "category_list": result
            }
        except Exception as e:
            return {'message': str(e)}, 500
