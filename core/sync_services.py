import time
import json
import requests
from flask import current_app as app

from core.problem_user_services import synch_user_problem
from core.training_model_services import sync_category_score_for_user, sync_problem_score_for_user, \
    sync_root_category_score_for_user, sync_overall_stat_for_user

from core.training_model_services import sync_category_score_for_team, sync_problem_score_for_team, \
    sync_root_category_score_for_team, sync_overall_stat_for_team

from core.notification_services import add_notification
from core.team_services import get_team_details
from core.user_services import get_user_details_by_handle_name


def user_problem_data_sync(user_id):
    app.logger.info(f'user_profile_sync service called for user: {user_id}')
    synch_user_problem(user_id)
    app.logger.info('synch_user_problem done')

    notification_data = {
        'user_id': user_id,
        'sender_id': 'System',
        'notification_type': 'System Notification',
        'redirect_url': '',
        'notification_text': 'Your problem data has been synced by',
        'status': 'UNREAD',
    }
    add_notification(notification_data)


def user_training_model_sync(user_id):
    app.logger.info(f'user_training_model_sync service called for user: {user_id}')
    for count in range(0, 4):
        sync_category_score_for_user(user_id)
    # NEED TO FIX THIS LATER, MIGHT NEED TO APPLY RECURSION IN A DAG.
    # THE CATEGORY DEPENDENCY LIST MUST FORM A DAG. NEED TO WRITE SCRIPT TO VERIFY.

    app.logger.info('sync_category_score_for_user done')
    sync_problem_score_for_user(user_id)

    app.logger.info('sync_problem_score_for_user done')
    sync_root_category_score_for_user(user_id)

    app.logger.info('sync_root_category_score_for_user done')
    sync_overall_stat_for_user(user_id)

    app.logger.info('sync_overall_stat_for_user done')

    notification_data = {
        'user_id': user_id,
        'sender_id': 'System',
        'notification_type': 'System Notification',
        'redirect_url': '',
        'notification_text': 'Your training model has been synced by',
        'status': 'UNREAD',
    }
    add_notification(notification_data)


def team_training_model_sync(team_id):
    app.logger.info(f'team_training_model_sync service called for team: {team_id}')
    sync_category_score_for_team(team_id)
    app.logger.debug('sync sync_problem_score_for_team')
    sync_problem_score_for_team(team_id)
    app.logger.debug('sync sync_root_category_score_for_team')
    sync_root_category_score_for_team(team_id)
    app.logger.debug('sync sync_overall_stat_for_team')
    sync_overall_stat_for_team(team_id)

    team_details = get_team_details(team_id)
    member_list = team_details.get('member_list', [])
    for member in member_list:
        member_details = get_user_details_by_handle_name(member['user_handle'])
        notification_data = {
            'user_id': member_details['id'],
            'sender_id': 'System',
            'notification_type': 'System Notification',
            'redirect_url': '',
            'notification_text': 'Training model for your team ' + team_details['team_name'] + ' has been synced by',
            'status': 'UNREAD',
        }
        add_notification(notification_data)