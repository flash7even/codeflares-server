import math
import requests
from flask import current_app as app
import time
import json

from commons.skillset import Skill
from core.problem_services import get_total_problem_score_for_user
from core.rating_services import add_user_ratings
from core.sync_services import user_problem_data_sync, user_training_model_sync, team_training_model_sync
from core.team_services import search_teams, get_team_details, update_team_details
from core.user_services import search_user, get_user_details, update_user_details


def user_list_sync():
    user_list = search_user({'username': 'flash_7'}, 0, 500)
    for user in user_list:
        id = user['id']
        user_problem_data_sync(id)
        user_training_model_sync(id)

        details_info = get_user_details(id)
        skill_value = details_info.get('skill_value', 0)
        solve_count = details_info.get('solve_count', 0)
        previous_problem_score = details_info['total_score']
        current_problem_score = get_total_problem_score_for_user([id])

        updated_data = {
            'total_score': current_problem_score
        }
        decrease_factor = 0
        if current_problem_score < previous_problem_score + details_info['target_score']:
            decrease_amount = previous_problem_score + details_info['target_score'] - current_problem_score
            decrease_factor = math.sqrt(decrease_amount)

        updated_data['decreased_skill_value'] = details_info['decreased_skill_value'] + decrease_factor
        current_skill = skill_value - updated_data['decreased_skill_value']
        current_skill_level = Skill.get_skill_level_from_skill(current_skill)
        updated_data['target_score'] = Skill.generate_next_week_prediction(current_skill_level)
        add_user_ratings(id, current_skill, solve_count)
        update_user_details(id, updated_data)


def team_list_sync():
    team_list = search_teams({'team_name': 'nsu_vendetta'}, 0, 500)
    for team in team_list:
        team_id = team['id']
        team_training_model_sync(team_id)

        details_info = get_team_details(id)
        member_id_list = []
        for member in details_info['member_list']:
            member_id_list.append(member['member_id'])

        skill_value = details_info.get('skill_value', 0)
        solve_count = details_info.get('solve_count', 0)
        previous_problem_score = details_info['total_score']
        current_problem_score = get_total_problem_score_for_user(member_id_list)

        updated_data = {
            'total_score': current_problem_score
        }
        decrease_factor = 0
        if current_problem_score < previous_problem_score + details_info['target_score']:
            decrease_amount = previous_problem_score + details_info['target_score'] - current_problem_score
            decrease_factor = math.sqrt(decrease_amount)

        updated_data['decreased_skill_value'] = details_info['decreased_skill_value'] + decrease_factor
        current_skill = skill_value - updated_data['decreased_skill_value']
        current_skill_level = Skill.get_skill_level_from_skill(current_skill)
        updated_data['target_score'] = Skill.generate_next_week_prediction(current_skill_level)
        add_user_ratings(id, current_skill, solve_count)
        update_team_details(id, updated_data)