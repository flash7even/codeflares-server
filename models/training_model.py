import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

from core.problem_services import search_problems_light
from core.category_services import search_categories_light

_es_size = 20


def individual_training_problem_list():
    problem_list = search_problems_light({}, 0, 20)
    score = 95
    for problem in problem_list:
        problem['relevant_score'] = score
        score -= 2.7
    return problem_list


def individual_training_category_list():
    category_list = search_categories_light({}, 0, 20)
    score = 95
    for category in category_list:
        category['relevant_score'] = score
        category['skill_value'] = 1533
        category['skill_title'] = 'EXPERT'
        category['solve_count'] = 55
        score -= 1.7
    return category_list
