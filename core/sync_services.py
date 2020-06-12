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
from commons.skillset import Skill


def user_problem_data_sync(user_id):
    synch_user_problem(user_id)

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
    for count in range(0, 3):
        sync_category_score_for_user(user_id)
    # FIXITLATER:
    # NEED TO FIX THIS LATER, MIGHT NEED TO APPLY RECURSION IN A DAG.
    # THE CATEGORY DEPENDENCY LIST MUST FORM A DAG. NEED TO WRITE SCRIPT TO VERIFY.

    app.logger.info('sync_category_score_for_user done')

    skill_value = sync_root_category_score_for_user(user_id)
    app.logger.info('sync_root_category_score_for_user done')

    app.logger.info('sync_overall_stat_for_user done')
    sync_overall_stat_for_user(user_id, skill_value)

    skill = Skill()
    user_skill_level = skill.get_skill_level_from_skill(skill_value)
    sync_problem_score_for_user(user_id, user_skill_level)
    app.logger.info('sync_problem_score_for_user done')

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
    app.logger.debug('sync sync_category_score_for_team')
    sync_category_score_for_team(team_id)
    app.logger.debug('sync sync_root_category_score_for_team')
    skill_value = sync_root_category_score_for_team(team_id)
    app.logger.debug('sync sync_overall_stat_for_team')
    sync_overall_stat_for_team(team_id, skill_value)
    skill = Skill()
    user_skill_level = skill.get_skill_level_from_skill(skill_value)
    app.logger.debug('sync get_skill_level_from_skill done')
    sync_problem_score_for_team(team_id, user_skill_level)
    app.logger.debug('sync sync_problem_score_for_team done')

    team_details = get_team_details(team_id)
    app.logger.debug(f' end team_details{team_details}')
    member_list = team_details.get('member_list', [])
    for member in member_list:
        member_details = get_user_details_by_handle_name(member['user_handle'])
        app.logger.debug(f' member_details {member_details}')
        notification_data = {
            'user_id': member_details['id'],
            'sender_id': 'System',
            'notification_type': 'System Notification',
            'redirect_url': '',
            'notification_text': 'Training model for your team ' + team_details['team_name'] + ' has been synced by',
            'status': 'UNREAD',
        }
        app.logger.debug(f' add_notification {notification_data}')
        add_notification(notification_data)
    app.logger.info(f'team_training_model_sync service completed')