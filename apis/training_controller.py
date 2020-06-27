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

api = Namespace('training', description='Namespace for training service')

from core.training_model_services import search_top_skilled_categoires_for_user, search_top_skilled_problems_for_user
from core.team_services import get_all_users_from_team, get_team_details
from core.user_services import get_user_details_by_handle_name, get_user_details_public


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


@api.route('/individual/<string:user_id>')
class IndividualTrainingModel(Resource):

    @access_required(access="ALL")
    @api.doc('get training model for currently logged in user')
    def post(self, user_id):
        app.logger.info('Get individual training model api called')
        param = request.get_json()
        response = {}
        if 'training_problems' in param and param['training_problems']:
            response['problem_stat'] = search_top_skilled_problems_for_user(user_id, 'relevant_score', 10, True)
        if 'training_categories' in param and param['training_categories']:
            response['category_stat'] = search_top_skilled_categoires_for_user(user_id, 'ALL', 'relevant_score', 10, True)
        if 'category_skill' in param and param['category_skill']:
            response['category_skill_list'] = search_top_skilled_categoires_for_user(user_id, 'ALL', 'skill_value', 200, True)
        if 'root_category_skill' in param and param['root_category_skill']:
            response['root_category_skill_list'] = search_top_skilled_categoires_for_user(user_id, 'root', 'skill_value', 20, True)
        return response


@api.route('/team/<string:team_id>')
class TeamTrainingModel(Resource):

    @access_required(access="ALL")
    @api.doc('get training model for currently logged in user')
    def post(self, team_id):
        app.logger.info('Get individual training model api called')
        param = request.get_json()
        team_details = get_team_details(team_id)
        if 'training_problems' in param and param['training_problems']:
            team_details['problem_stat'] = search_top_skilled_problems_for_user(team_id, 'relevant_score', 10, True)
        if 'training_categories' in param and param['training_categories']:
            team_details['category_stat'] = search_top_skilled_categoires_for_user(team_id, 'ALL', 'relevant_score', 10, True)
        if 'category_skill' in param and param['category_skill']:
            team_details['category_skill_list'] = search_top_skilled_categoires_for_user(team_id, 'ALL', 'skill_value', 200, True)
        if 'root_category_skill' in param and param['root_category_skill']:
            team_details['root_category_skill_list'] = search_top_skilled_categoires_for_user(team_id, 'root', 'category_id', 20, True)
        if 'skill_comparison_info' in param and param['skill_comparison_info']:
            team_details['skill_info'] = []
            member_list = team_details.get('member_list', [])
            for member in member_list:
                user_details = get_user_details_by_handle_name(member['user_handle'])
                if user_details is None:
                    continue
                skill_list = search_top_skilled_categoires_for_user(user_details['id'], 'root', 'category_id', 15, True)
                team_details['skill_info'].append({'skill_list': skill_list})
        return team_details


@api.route('/classroom/<string:team_id>')
class TeamTrainingModel(Resource):

    @access_required(access="ALL")
    @api.doc('get classroom model ')
    def get(self, team_id):
        app.logger.info('Get classroom training model api called')
        team_details = get_team_details(team_id)
        member_stat = []
        member_list = team_details.get('member_list', [])
        for member in member_list:
            user_details = get_user_details_by_handle_name(member['user_handle'])
            if user_details is None:
                continue
            user_public_info = get_user_details_public(user_details['id'])
            skill_list = search_top_skilled_categoires_for_user(user_details['id'], 'root', 'category_id', 15, True)
            user_public_info['status'] = 'pending'
            for f in user_public_info:
                member[f] = user_public_info[f]
            store = {
                'user_handle': member['user_handle'],
                'skill_color': member['skill_color'],
                'skill_list': skill_list
            }
            member_stat.append(store)
        team_details['member_stat'] = member_stat

        category_list = []
        for cat in member_stat[0]['skill_list']:
            category_list.append(cat['category_info'])

        team_details['category_list'] = category_list

        return team_details
