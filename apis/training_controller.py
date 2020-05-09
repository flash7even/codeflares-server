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

from models.training_model import individual_training_problem_list, individual_training_category_list, category_skills, root_category_skills, update_team_member_skills
from core.team_services import get_team_details
from core.training_model_services import category_wise_problem_solve_for_user
from models.category_skill_model import SkillGenerator
from operator import itemgetter
from commons.skillset import Skill


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
    def get(self, user_id):
        app.logger.info('Get individual training model api called')

        category_list = category_wise_problem_solve_for_user(user_id)
        for category in category_list:
            skill_generator = SkillGenerator()
            skill_stat = skill_generator.generate_skill(category['solved_stat']['difficulty_wise_count'])
            category['relevant_score'] = skill_stat['level']
            category['skill_value'] = skill_stat['skill']
            skill_obj = Skill()
            category['skill_title'] = skill_obj.get_skill_title(skill_stat['skill'])
            category['solve_count'] = category['solved_stat']['total_count']
            category.pop('solved_stat', None)

        category_list = sorted(category_list, key=itemgetter('skill_value'), reverse=True)


        problems = individual_training_problem_list()
        categories = individual_training_category_list()
        category_skill_list = category_list
        root_category_skill_list = root_category_skills()

        return {
            'problem_stat': problems,
            'category_stat': categories,
            'category_skill_list': category_skill_list,
            'root_category_skill_list': root_category_skill_list
        }


@api.route('/team/<string:team_id>')
class TeamTrainingModel(Resource):

    @access_required(access="ALL")
    @api.doc('get training model for currently logged in user')
    def get(self, team_id):
        app.logger.info('Get individual training model api called')

        try:
            problems = individual_training_problem_list()
            categories = individual_training_category_list()
            category_skill_list = category_skills()
            root_category_skill_list = root_category_skills()
            team_details = update_team_member_skills(team_id, root_category_skill_list)

            team_details['problem_stat'] = problems
            team_details['category_stat'] = categories
            team_details['category_skill_list'] = category_skill_list
            team_details['root_category_skill_list'] = root_category_skill_list
            
            print('team_details: ', json.dumps(team_details))
            return team_details
        
        except Exception as e:
            return {'message': str(e)}, 500
