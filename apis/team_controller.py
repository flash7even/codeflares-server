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
from commons.skillset import Skill

api = Namespace('team', description='Namespace for team service')

from core.team_services import add_team_member, delete_team_member, \
    delete_all_users_from_team,\
    search_teams_for_user, get_team_details, update_team_member, search_teams, get_rating_history_codeforces, add_team_members_bulk

from core.sync_services import team_training_model_sync
from core.job_services import add_pending_job
from core.rating_services import add_user_ratings

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cfs_teams'
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

    @api.doc('get team details by id')
    def get(self, team_id):
        app.logger.info('Get team_details method called')
        print('team_id: ', team_id)
        try:
            team_info = get_team_details(team_id)
            return team_info, 200
        
        except Exception as e:
            return {'message': str(e)}, 500

    @access_required(access="ALL")
    @api.doc('update team by id')
    def put(self, team_id):
        try:
            app.logger.info('Update team_details method called')
            current_user = get_jwt_identity().get('id')
            rs = requests.session()
            post_data = request.get_json()
            app.logger.info('Update team_details post_data: ' + json.dumps(post_data))
            member_list = []
            if 'member_list' in post_data:
                member_list = post_data['member_list']
                post_data.pop('member_list', None)

            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, team_id)
            response = rs.get(url=search_url, headers=_http_headers).json()
            if 'found' in response:
                if response['found']:
                    data = response['_source']
                    for key, value in post_data.items():
                        data[key] = value
                    data['updated_at'] = int(time.time())
                    response = rs.put(url=search_url, json=data, headers=_http_headers).json()
                    if 'result' in response:
                        add_team_members_bulk(member_list, team_id, data['team_type'], current_user)
                        app.logger.info('Update team_details method completed')
                        return response['result'], 200
                    else:
                        app.logger.error('Elasticsearch down, response: ' + str(response))
                        return response, 500
                app.logger.warning('Team not found')
                return {'message': 'not found'}, 404
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500

        except Exception as e:
            return {'message': str(e)}, 500

    @access_required(access="ALL")
    @api.doc('delete team by id')
    def delete(self, team_id):
        try:
            app.logger.info('Delete team_details method called')
            rs = requests.session()
            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, team_id)
            response = rs.delete(url=search_url, headers=_http_headers).json()
            if 'result' in response:
                if response['result'] == 'deleted':
                    delete_all_users_from_team(team_id)
                    app.logger.info('Delete team_details method completed')
                    return response['result'], 200
                else:
                    return response['result'], 400
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/')
class CreateTeam(Resource):

    @access_required(access="ALL")
    @api.doc('create team')
    def post(self):
        try:
            app.logger.info('Create team method called')
            current_user = get_jwt_identity().get('id')
            print('current_user: ', current_user)
            rs = requests.session()
            data = request.get_json()

            skill = Skill()
            data['created_at'] = int(time.time())
            data['updated_at'] = int(time.time())
            data['skill_value'] = 0
            data['skill_title'] = skill.get_skill_title(0)
            data['decreased_skill_value'] = 0
            data['total_score'] = 0
            data['target_score'] = 0
            data['solve_count'] = 0

            member_list = []
            if 'member_list' in data:
                member_list = data['member_list']
                data.pop('member_list', None)
            
            data['team_leader_id'] = current_user

            post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type)
            response = rs.post(url=post_url, json=data, headers=_http_headers).json()

            if 'result' in response and response['result'] == 'created':
                add_team_members_bulk(member_list, response['_id'], data['team_type'], current_user)
                app.logger.info('Create team method completed')
                add_user_ratings(response['_id'], 0, 0)
                return response['_id'], 201
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/member/')
class CreateTeam(Resource):

    @access_required(access="ALL")
    @api.doc('add team member')
    def post(self):
        try:
            app.logger.info('Add team member method called')
            data = request.get_json()
            response = add_team_member(data)
            app.logger.info('Add team member method completed')
            return response, 201

        except Exception as e:
            return {'message': str(e)}, 500

    @access_required(access="ALL")
    @api.doc('update team member')
    def put(self):
        try:
            app.logger.info('Update team member method called')
            data = request.get_json()
            print('provided data: ', data)
            response = update_team_member(data)
            app.logger.info('Update team member method completed')
            return response, 201

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/member/<string:team_id>/<string:user_handle>')
class CreateTeam(Resource):

    @access_required(access="ALL")
    @api.doc('delete team member')
    def delete(self, team_id, user_handle):
        try:
            app.logger.info('Delete team member method called')
            print('team_id: ', team_id, ' user_handle: ', user_handle)
            response = delete_team_member(team_id, user_handle)
            app.logger.info('Delete team member method completed')
            return response, 201

        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchTeam(Resource):

    @api.doc('search team based on post parameters')
    def post(self, page=0):
        app.logger.info('Team search method called')
        try:
            param = request.get_json()
            team_list = search_teams(param, page*_es_size, _es_size)
            print('team_list: ', team_list)
            return {
                'team_list': team_list
            }, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/user/<string:user_handle>')
class SearchTeamForUser(Resource):

    @access_required(access="ALL")
    @api.doc('search team based on post parameters')
    def post(self, user_handle):
        app.logger.info('Team search method called')
        try:
            param = request.get_json()
            print('param given: ', param)
            team_list = search_teams_for_user(user_handle, param)
            return {
                'team_list': team_list
            }, 200
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/rating-history/<string:team_id>/<string:platform>')
class RatingHistoryOnlineJudge(Resource):

    # @access_required(access="ALL")
    @api.doc('get rating history')
    def get(self, team_id, platform):
        app.logger.info('Team search method called')
        try:
            if platform == "codeforces":
                result = get_rating_history_codeforces(team_id)
                return result
            return {}
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/sync/<string:team_id>')
class Sync(Resource):

    @access_required(access="ALL")
    @api.doc('Sync team by id')
    def put(self, team_id):
        app.logger.info('Sync team API called, id: ' + str(team_id))
        try:
            app.logger.debug('team_training_model_sync')
            add_pending_job(team_id, 'TEAM_SYNC')
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/sync/training-model/<string:team_id>')
class SyncTrainingModel(Resource):

    @access_required(access="ALL")
    @api.doc('Sync team training model by id')
    def put(self, team_id):
        app.logger.info('Sync team training model API called, id: ' + str(team_id))
        try:
            team_training_model_sync(team_id)
            app.logger.debug('team_training_model_sync done')
        except Exception as e:
            return {'message': str(e)}, 500
