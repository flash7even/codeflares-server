import time

import requests
from flask import current_app as app
from flask import request
from flask_restplus import Namespace, Resource
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended.exceptions import *
from flask_jwt_extended import jwt_required
from jwt.exceptions import *

api = Namespace('training', description='Namespace for training service')

from models.training_model import individual_training_problem_list, individual_training_category_list, category_skills

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


@api.route('/individual/')
class IndividualTrainingModel(Resource):

    #@jwt_required
    @api.doc('get training model for currently logged in user')
    def get(self):
        app.logger.info('Get individual training model api called')
        rs = requests.session()
        problems = individual_training_problem_list()
        categories = individual_training_category_list()
        category_skill_list = category_skills()

        return {
            'problem_stat': problems,
            'category_stat': categories,
            'category_skill_list': category_skill_list
        }


@api.route('/team/')
class IndividualTrainingModel(Resource):

    # @jwt_required
    @api.doc('get training model for currently logged in user')
    def get(self):
        app.logger.info('Get individual training model api called')
        rs = requests.session()
        problems = individual_training_problem_list()
        categories = individual_training_category_list()

        return {
            'problem_stat': problems,
            'category_stat': categories
        }
