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

api = Namespace('contest', description='Namespace for contest service')

from core.contest_services import create_contest, create_problem_set, search_contests, find_problem_set_for_contest, \
    reupload_problem_set_for_contest, get_contest_details, contest_standings
from core.user_services import get_user_details

_http_headers = {'Content-Type': 'application/json'}

_es_index = 'cfs_contests'
_es_type = '_doc'
_es_size = 500

mandatory_fields = ['contest_name', 'setter_id', 'contest_ref_id', 'contest_type', 'contest_level',
                    'problem_count', 'description', 'start_date', 'end_date']

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


@api.route('/<string:contest_id>')
class ContestByID(Resource):

    @api.doc('get contest details by id')
    def get(self, contest_id):
        try:
            app.logger.info('Get contest_details api called')
            contest_details = get_contest_details(contest_id)
            return contest_details, 200
        except Exception as e:
            return {'message': str(e)}, 500

    @api.doc('update contest by id')
    def put(self, contest_id):
        try:
            app.logger.info('Update contest_details api called')
            rs = requests.session()
            post_data = request.get_json()

            app.logger.debug('post_data for contest update: ' + json.dumps(post_data))

            if 'problem_list' in post_data:
                reupload_problem_set_for_contest(contest_id, post_data['problem_list'])

            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, contest_id)
            response = rs.get(url=search_url, headers=_http_headers).json()
            print(response)
            if 'found' in response:
                if response['found']:
                    data = response['_source']
                    for key, value in post_data.items():
                        if key in mandatory_fields:
                            data[key] = value
                    data['updated_at'] = int(time.time())
                    response = rs.put(url=search_url, json=data, headers=_http_headers).json()
                    if 'result' in response:
                        app.logger.info('Update contest_details api completed')
                        return response['result'], 200
                    else:
                        app.logger.error('Elasticsearch down, response: ' + str(response))
                        return response, 500
                app.logger.warning('Contest not found')
                return {'message': 'not found'}, 404
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500
        except Exception as e:
            return {'message': str(e)}, 500

    @api.doc('delete contest by id')
    def delete(self, contest_id):
        try:
            app.logger.info('Delete contest_details api called')
            rs = requests.session()
            search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index, _es_type, contest_id)
            response = rs.delete(url=search_url, headers=_http_headers).json()
            print(response)
            if 'result' in response:
                if response['result'] == 'deleted':
                    app.logger.info('Delete contest_details api completed')
                    return response['result'], 200
                else:
                    return response['result'], 400
            app.logger.error('Elasticsearch down, response: ' + str(response))
            return response, 500
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/')
class CreateContest(Resource):

    @api.doc('create contest')
    def post(self):
        try:
            app.logger.info('Create contest api called')
            data = request.get_json()

            contest_data = {}
            for f in mandatory_fields:
                if f not in data:
                    return {'message': 'bad request'}, 409
                contest_data[f] = data[f]

            contest_data['status'] = 'pending'
            contest_id = create_contest(contest_data)
            problem_set = create_problem_set(data, contest_id)
            return contest_id
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search', defaults={'page': 0})
@api.route('/search/<int:page>')
class SearchContest(Resource):

    @api.doc('search contest based on post parameters')
    def post(self, page=0):
        try:
            app.logger.info('Contest search api called')
            param = request.get_json()
            result = search_contests(param, page*_es_size, _es_size)
            app.logger.info('Contest search api completed')
            print(result)
            return {
                "contest_list": result
            }
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/standings/<string:contest_id>')
class Standings(Resource):

    @api.doc('Get Contest Standings')
    def get(self, contest_id):
        try:
            app.logger.info(f'Contest standings api called: {str(contest_id)}')
            standings = contest_standings(contest_id)
            return {
                "standings": standings
            }
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/standings/<string:contest_id>/<string:user_id>')
class StandingsUser(Resource):

    @api.doc('Get Contest Standings')
    def get(self, contest_id, user_id):
        try:
            app.logger.info(f'Contest standings api called: {str(contest_id)} , {str(user_id)}')
            standings = contest_standings(contest_id, user_id)
            return {
                "standings": standings
            }
        except Exception as e:
            return {'message': str(e)}, 500
