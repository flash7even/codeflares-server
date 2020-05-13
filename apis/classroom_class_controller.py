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

from core.classroom_services import search_class_lists

api = Namespace('classroom_class', description='Namespace for classroom_class service')

_http_headers = {'Content-Type': 'application/json'}

_es_index_classroom_classes = 'cp_training_classroom_classes'
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


@api.route('/<string:classroom_class_id>')
class ClassroomClassByID(Resource):

    @api.doc('get classroom_class details by id')
    def get(self, classroom_class_id):
        app.logger.info('Get classroom_class_details method called')
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_classroom_classes, _es_type, classroom_class_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print(response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                app.logger.info('Get classroom_class_details method completed')
                return data, 200
            app.logger.warning('classroom_class not found')
            return {'found': response['found']}, 404
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500

    @access_required(access="ALL")
    @api.doc('update classroom_class by id')
    def put(self, classroom_class_id):
        app.logger.info('Update classroom_class_details method called')
        rs = requests.session()
        post_data = request.get_json()

        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_classroom_classes, _es_type, classroom_class_id)
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
                    app.logger.info('Update classroom_class_details method completed')
                    return response['result'], 200
                else:
                    app.logger.error('Elasticsearch down, response: ' + str(response))
                    return response, 500
            app.logger.warning('classroom_class not found')
            return {'message': 'not found'}, 404
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500

    @access_required(access="ALL")
    @api.doc('delete classroom_class by id')
    def delete(self, classroom_class_id):
        app.logger.info('Delete classroom_class_details method called')
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_classroom_classes, _es_type, classroom_class_id)
        response = rs.delete(url=search_url, headers=_http_headers).json()
        print(response)
        if 'result' in response:
            if response['result'] == 'deleted':
                app.logger.info('Delete classroom_class_details method completed')
                return response['result'], 200
            else:
                return response['result'], 400
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500


@api.route('/')
class CreateClassroomClass(Resource):

    @access_required(access="ALL")
    @api.doc('create classroom_class')
    def post(self):
        app.logger.info('Create classroom_class method called')
        rs = requests.session()
        data = request.get_json()
        print('data: ', data)

        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_classroom_classes, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        print(response)

        if 'result' in response and response['result'] == 'created':
            app.logger.info('Create classroom_class method completed')
            return response['_id'], 201
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchClassroomClass(Resource):

    @api.doc('search classroom_class based on post parameters')
    def post(self, page=0):
        try:
            app.logger.info('Classroom class search method called')
            param = request.get_json()
            class_list = search_class_lists(param, page, _es_size)
            return {
                'class_list': class_list
            }
        except Exception as e:
            return {'message': str(e)}, 500
