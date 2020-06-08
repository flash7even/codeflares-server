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

api = Namespace('problem', description='Namespace for problem service')

from core.problem_services import search_problems, search_problems_by_category, get_problem_details, search_problems_by_category_dt_search
from core.category_services import get_category_id_from_name, get_category_details

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cfs_problems'
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


@api.route('/<string:problem_id>')
class ProblemByID(Resource):

    @api.doc('get problem details by id')
    def get(self, problem_id):
        try:
            app.logger.info('Get problem_details api called')
            response = get_problem_details(problem_id)
            return response
        except Exception as e:
            return {'message': str(e)}, 500

    @access_required(access="ALL")
    @api.doc('update problem by id')
    def put(self, problem_id):
        try:
            app.logger.info('Update problem_details api called')
            rs = requests.session()
            post_data = request.get_json()

            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, problem_id)
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
                        app.logger.info('Update problem_details api completed')
                        return response['result'], 200
                    else:
                        app.logger.error('Elasticsearch down, response: ' + str(response))
                        return response, 500
                app.logger.warning('Problem not found')
                return {'message': 'not found'}, 404
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500
        except Exception as e:
            return {'message': str(e)}, 500

    @access_required(access="ALL")
    @api.doc('delete problem by id')
    def delete(self, problem_id):
        try:
            app.logger.info('Delete problem_details api called')
            rs = requests.session()
            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, problem_id)
            response = rs.delete(url=search_url, headers=_http_headers).json()
            print(response)
            if 'result' in response:
                if response['result'] == 'deleted':
                    app.logger.info('Delete problem_details api completed')
                    return response['result'], 200
                else:
                    return response['result'], 400
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/')
class CreateProblem(Resource):

    #@access_required(access="ALL")
    @api.doc('create problem')
    def post(self):
        try:
            app.logger.info('Create problem api called')
            rs = requests.session()
            data = request.get_json()
            categories = []
            if 'category_dependency_list' in data:
                category_dependency_list = data['category_dependency_list']
                data.pop('category_dependency_list', None)
                for cat in category_dependency_list:
                    category_id = cat.get('category_id', None)
                    if category_id is None:
                        category_id = get_category_id_from_name(cat['category_name'])
                    category_details = get_category_details(category_id)
                    edge = {
                        'category_id': category_id,
                        'dependency_factor': cat['factor'],
                        'category_root': category_details['category_root'],
                        'category_name': category_details['category_name'],
                    }
                    categories.append(edge)

            data['categories'] = categories
            data['created_at'] = int(time.time())
            data['updated_at'] = int(time.time())

            post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type)
            response = rs.post(url=post_url, json=data, headers=_http_headers).json()
            app.logger.info('Problem Created Successfully')

            if 'result' in response and response['result'] == 'created':
                app.logger.info('Create problem api completed')
                return response['_id'], 201
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchProblem(Resource):

    @api.doc('search problem based on post parameters')
    def post(self, page=0):
        try:
            app.logger.info('Problem search api called')
            param = request.get_json()
            result = search_problems_by_category(param, heavy=False)
            app.logger.info('Problem search api completed')
            return {
                "problem_list": result
            }
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/raw', defaults={'page': 0})
@api.route('/search/raw/<int:page>')
class SearchRowProblems(Resource):

    @api.doc('search problem based on post parameters')
    def post(self, page=0):
        try:
            app.logger.info('Problem search api called')
            param = request.get_json()
            result = search_problems(param, page*_es_size, _es_size)
            app.logger.info('Problem search api completed')
            return {
                "problem_list": result
            }
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/heavy', defaults={'page': 0})
@api.route('/search/heavy/<int:page>')
class SearchProblem(Resource):

    @api.doc('search problem based on post parameters')
    def post(self, page=0):
        try:
            app.logger.info('Problem search api called')
            param = request.get_json()
            result = search_problems_by_category(param, heavy=True)
            app.logger.info('Problem search api completed')
            return {
                "problem_list": result
            }
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/dtsearch/heavy')
class SearchProblemDTSearch(Resource):

    @api.doc('dtsearch problem based on post parameters')
    def post(self):
        try:
            app.logger.info('Problem dtsearch api called')
            param = request.get_json()
            draw = param['draw']
            start = param['start']
            length = param['length']
            search = param['search']['value']

            print(json.dumps(param))

            param_body = {}
            if len(search) > 0:
                param_body['filter'] = search

            print('custom_param: ', param['custom_param'])

            for f in param['custom_param']:
                param_body[f] = param['custom_param'][f]

            sort_by = 'problem_difficulty'
            sort_order = 'asc'

            if 'sort_by' in param:
                if param['sort_by'] == 'problem_name':
                    sort_by = 'problem_name.keyword'
                else:
                    sort_by = param['sort_by']
                sort_order = param['sort_order']

            proble_stat = search_problems_by_category_dt_search(param_body, start, length, sort_by, sort_order)
            resp = {
                'draw': draw,
                'recordsTotal': proble_stat['total'],
                'recordsFiltered': proble_stat['total'],
                'data': proble_stat['problem_list'],
            }
            print(resp)
            return resp
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/<string:problem_id>/<string:user_id>')
class UserProblemByID(Resource):

    @api.doc('get problem details by id')
    def get(self, problem_id, user_id):
        try:
            app.logger.info('Get problem_details api called')
            response = get_problem_details(problem_id, user_id)
            return response
        except Exception as e:
            return {'message': str(e)}, 500
