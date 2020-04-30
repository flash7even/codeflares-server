import time
import json
import requests
import random
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

from core.problem_services import search_problems_light
from core.category_services import search_categories_light
from core.team_services import get_team_details

_es_size = 500


def individual_training_problem_list():
    problem_list = search_problems_light({}, 0, 5)
    for problem in problem_list:
        problem['relevant_score'] = random.randint(50, 100)
    return problem_list


def individual_training_category_list():
    category_list = search_categories_light({}, 0, 5)
    for category in category_list:
        category['relevant_score'] = random.randint(50, 100)
        category['skill_value'] = random.randint(50, 2200)
        category['skill_title'] = 'EXPERT'
        category['solve_count'] = random.randint(500, 1000)
    return category_list


def category_skills():
    category_list = search_categories_light({}, 0, _es_size)
    for category in category_list:
        category['relevant_score'] = random.randint(50, 100)
        category['skill_value'] = random.randint(50, 2200)
        category['skill_title'] = 'EXPERT'
        category['solve_count'] = random.randint(500, 1000)
    return category_list



def root_category_skills():
    category_list = search_categories_light({'category_root': 'root'}, 0, _es_size)
    for category in category_list:
        category['skill_value'] = random.randint(50, 2200)
        category['skill_title'] = 'EXPERT'
        category['solve_count'] = random.randint(500, 1000)
    return category_list


def update_team_member_skills(team_id, root_categories):
    team_details = get_team_details(team_id)
    team_details['skill_info'] = []
    member_list = team_details.get('member_list', [])
    for member in member_list:
        id = member['id']
        skill_list = []
        for algo in root_categories:
            skill_list.append(
                {
                    "algo_name": algo['category_name'],
                    "solve_count": random.randint(50, 200),
                    "skill_value": random.randint(50, 2500)
                }
            )
        team_details['skill_info'].append(
            {
                'skill_list': skill_list
            }
        )
    return team_details
