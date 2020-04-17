import time

import requests
from flask import current_app as app
from flask import request
from flask_restplus import Namespace, Resource
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended.exceptions import *
from flask_jwt_extended import jwt_required
from jwt.exceptions import *

api = Namespace('onlinejudge', description='Namespace for onlinejudge service')

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cp_training_online_judges'
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


@api.route('/<string:onlinejudge_id>')
class OnlinejudgeByID(Resource):

    #@jwt_required
    @api.doc('get onlinejudge details by id')
    def get(self, onlinejudge_id):
        app.logger.info('Get onlinejudge_details method called')
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, onlinejudge_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print(response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                app.logger.info('Get onlinejudge_details method completed')
                return data, 200
            app.logger.warning('Onlinejudge not found')
            return {'found': response['found']}, 404
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500

    #@jwt_required
    @api.doc('update onlinejudge by id')
    def put(self, onlinejudge_id):
        app.logger.info('Update onlinejudge_details method called')
        rs = requests.session()
        post_data = request.get_json()

        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, onlinejudge_id)
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
                    app.logger.info('Update onlinejudge_details method completed')
                    return response['result'], 200
                else:
                    app.logger.error('Elasticsearch down, response: ' + str(response))
                    return response, 500
            app.logger.warning('Onlinejudge not found')
            return {'message': 'not found'}, 404
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500

    #@jwt_required
    @api.doc('delete onlinejudge by id')
    def delete(self, onlinejudge_id):
        app.logger.info('Delete onlinejudge_details method called')
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, onlinejudge_id)
        response = rs.delete(url=search_url, headers=_http_headers).json()
        print(response)
        if 'result' in response:
            if response['result'] == 'deleted':
                app.logger.info('Delete onlinejudge_details method completed')
                return response['result'], 200
            else:
                return response['result'], 400
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500


@api.route('/')
class CreateOnlinejudge(Resource):

    #@jwt_required
    @api.doc('create onlinejudge')
    def post(self):
        app.logger.info('Create onlinejudge method called')
        rs = requests.session()
        data = request.get_json()

        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()
        print(response)

        if 'result' in response and response['result'] == 'created':
            app.logger.info('Create onlinejudge method completed')
            return response['_id'], 201
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchOnlinejudge(Resource):

    #@jwt_required
    @api.doc('search onlinejudge based on post parameters')
    def post(self, page=0):
        app.logger.info('Onlinejudge search method called')
        rs = requests.session()
        param = request.get_json()
        query_json = {'query': {'match_all': {}}}

        must = []
        keyword_fields = ['onlinejudge_title', 'onlinejudge_root']

        for f in param:
            if f in keyword_fields:
                must.append({'term': {f: param[f]}})
            else:
                must.append({'match': {f: param[f]}})

        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

        query_json['from'] = page*_es_size
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        print(response)
        if 'hits' in response:
            item_list = []
            for hit in response['hits']['hits']:
                onlinejudge = hit['_source']
                onlinejudge['id'] = hit['_id']
                item_list.append(onlinejudge)
            app.logger.info('Onlinejudge search method completed')
            return item_list, 200
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return {'message': 'internal server error'}, 500
