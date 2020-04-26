import time

import requests
from flask import current_app as app
from flask import request
from flask_restplus import Namespace, Resource
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended.exceptions import *
from flask_jwt_extended import jwt_required
from jwt.exceptions import *

api = Namespace('team', description='Namespace for team service')

from core.team_services import add_team_member, delete_team_member, delete_all_users_from_team, get_all_users_from_team

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cp_training_teams'
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


@api.route('/<string:team_id>')
class TeamByID(Resource):

    #@jwt_required
    @api.doc('get team details by id')
    def get(self, team_id):
        app.logger.info('Get team_details method called')
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, team_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        print(response)
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                data['user_list'] = get_all_users_from_team(team_id)
                app.logger.info('Get team_details method completed')
                return data, 200
            app.logger.warning('Team not found')
            return {'found': response['found']}, 404
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500

    #@jwt_required
    @api.doc('update team by id')
    def put(self, team_id):
        app.logger.info('Update team_details method called')
        rs = requests.session()
        post_data = request.get_json()

        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, team_id)
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
                    app.logger.info('Update team_details method completed')
                    return response['result'], 200
                else:
                    app.logger.error('Elasticsearch down, response: ' + str(response))
                    return response, 500
            app.logger.warning('Team not found')
            return {'message': 'not found'}, 404
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500

    #@jwt_required
    @api.doc('delete team by id')
    def delete(self, team_id):
        app.logger.info('Delete team_details method called')
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, team_id)
        response = rs.delete(url=search_url, headers=_http_headers).json()
        print(response)
        if 'result' in response:
            if response['result'] == 'deleted':
                delete_all_users_from_team(team_id)
                app.logger.info('Delete team_details method completed')
                return response['result'], 200
            else:
                return response['result'], 400
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500


@api.route('/')
class CreateTeam(Resource):

    #@jwt_required
    @api.doc('create team')
    def post(self):
        app.logger.info('Create team method called')
        rs = requests.session()
        data = request.get_json()

        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        member_list = []
        if 'member_list' in data:
            member_list = data['member_list']
            data.pop('member_list', None)

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()

        if 'result' in response and response['result'] == 'created':
            for member in member_list:
                edge = {
                    'team_id': response['_id'],
                    'user_id': member['user_id'],
                    'remarks': member['remarks']
                }
                add_team_member(edge)
            app.logger.info('Create team method completed')
            return response['_id'], 201
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500


@api.route('/member/')
class CreateTeam(Resource):

    #@jwt_required
    @api.doc('add team member')
    def post(self):
        app.logger.info('Add team member method called')
        data = request.get_json()
        response = add_team_member(data)
        app.logger.info('Add team member method completed')
        return response, 201

    #@jwt_required
    @api.doc('delete team member')
    def delete(self):
        app.logger.info('Delete team member method called')
        data = request.get_json()
        response = delete_team_member(data['team_id'], data['user_id'])
        app.logger.info('Delete team member method completed')
        return response, 201


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchTeam(Resource):

    #@jwt_required
    @api.doc('search team based on post parameters')
    def post(self, page=0):
        app.logger.info('Team search method called')
        rs = requests.session()
        param = request.get_json()
        query_json = {'query': {'match_all': {}}}

        must = []
        keyword_fields = ['team_leader_id', 'team_type']

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
        if 'hits' in response:
            item_list = []
            for hit in response['hits']['hits']:
                team = hit['_source']
                team['id'] = hit['_id']
                item_list.append(team)
            app.logger.info('Team search method completed')
            return item_list, 200
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return {'message': 'internal server error'}, 500
