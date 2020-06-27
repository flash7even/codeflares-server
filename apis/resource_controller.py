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

api = Namespace('resource', description='Namespace for resource service')

from core.resource_services import add_resources, search_resource

from core.user_services import get_user_details
from core.vote_services import get_vote_count_list

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cfs_resources'
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


@api.route('/<string:resource_id>')
class ResourceByID(Resource):

    @api.doc('get resource details by id')
    def get(self, resource_id):
        app.logger.info('Get resource_details method called')
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, resource_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print(response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                data['resource_id'] = response['_id']
                data['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(data['updated_at']))
                user_details = get_user_details(data['resource_writer'])
                data['resource_writer_handle'] = user_details['username']
                data['resource_writer_skill_color'] = user_details['skill_color']
                data['vote_count'] = get_vote_count_list(data['resource_id'])
                app.logger.info('Get resource_details method completed')
                return data, 200
            app.logger.warning('Resource not found')
            return {'found': response['found']}, 404
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500

    @access_required(access="ALL")
    @api.doc('update resource by id')
    def put(self, resource_id):
        app.logger.info('Update resource_details method called')
        rs = requests.session()
        post_data = request.get_json()

        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, resource_id)
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
                    app.logger.info('Update resource_details method completed')
                    return response['result'], 200
                else:
                    app.logger.error('Elasticsearch down, response: ' + str(response))
                    return response, 500
            app.logger.warning('Resource not found')
            return {'message': 'not found'}, 404
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500

    @access_required(access="ALL")
    @api.doc('delete resource by id')
    def delete(self, resource_id):
        app.logger.info('Delete resource_details method called')
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, resource_id)
        response = rs.delete(url=search_url, headers=_http_headers).json()
        print(response)
        if 'result' in response:
            if response['result'] == 'deleted':
                app.logger.info('Delete resource_details method completed')
                return response['result'], 200
            else:
                return response['result'], 400
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500


@api.route('/')
class CreateResource(Resource):

    @access_required(access="ALL")
    @api.doc('create resource')
    def post(self):
        try:
            app.logger.info('Create resource method called')
            rs = requests.session()
            data = request.get_json()
            response = add_resources(data)
            return response
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchResource(Resource):

    @api.doc('search resource based on post parameters')
    def post(self, page=0):
        try:
            app.logger.info('Resource search method called')
            rs = requests.session()
            param = request.get_json()
            resource_list = search_resource(param, 0, _es_size)
            return {
                'resource_list': resource_list
            }

        except Exception as e:
            return {'message': str(e)}, 500
