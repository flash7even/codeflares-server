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

api = Namespace('user_notification', description='Namespace for user_notification service')

from core.notification_services import search_notification, update_notification

_http_headers = {'Content-Type': 'application/json'}

_es_user_user_notification = 'cfs_notifications'
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


@api.route('/read/single/<string:notification_id>')
class UpdateNotification(Resource):

    @api.doc('update user_notification')
    def put(self, notification_id):
        try:
            app.logger.info('Update notification api called')
            data = {
                'status': 'READ'
            }
            update_notification(notification_id, data)
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/read/all/<string:user_id>')
class UpdateAllNotification(Resource):

    @api.doc('update all user_notification based on post parameters')
    def put(self, user_id):
        try:
            app.logger.info('Update all notification api called')
            unread_list = search_notification({'status': "UNREAD", 'user_id': user_id}, _es_size)
            for notification in unread_list:
                data = {
                    'status': 'READ'
                }
                update_notification(notification['id'], data)
        except Exception as e:
            return {'message': str(e)}, 500


@api.route('/search/<string:user_id>')
class SearchUserNotification(Resource):

    @api.doc('search user_notification based on post parameters')
    def post(self, user_id):
        try:
            app.logger.info('UserNotification search api called')
            data = request.get_json()
            size = data.get('size', _es_size)
            unread_list = search_notification({'status': "UNREAD", 'user_id': user_id}, size)
            unread_list_all = search_notification({'status': "UNREAD", 'user_id': user_id}, _es_size)
            notification_list = search_notification({'user_id': user_id}, size)
            response = {
                'notification_list': notification_list,
                'unread_length': len(unread_list_all)
            }
            if len(unread_list) > 0:
                response['UNREAD'] = True
            return response
        except Exception as e:
            return {'message': str(e)}, 500
