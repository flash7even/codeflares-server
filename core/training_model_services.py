import time
import json
import requests
from flask import current_app as app
from operator import itemgetter

from commons.skillset import Skill
from models.category_skill_model import SkillGenerator
from models.category_score_model import CategoryScoreGenerator
from models.problem_score_model import ProblemScoreGenerator

from core.category_services import search_categories
from core.problem_services import get_problem_details, find_problems_for_user_by_status_filtered, available_problems_for_user, \
    find_problem_dependency_list, add_user_problem_status
from core.user_model_sync_services import add_user_category_data, get_user_category_data

_http_headers = {'Content-Type': 'application/json'}


_es_index_category_problem = 'cp_training_problem_category_edges'
_es_index_problem_category = 'cp_training_problem_category_edges'
_es_index_problem_user = 'cp_training_user_problem_edges'
_es_index_problem = 'cp_training_problems'
_es_type = '_doc'
_es_size = 500
_es_max_solved_problem = 1000
_bulk_size = 20

SOLVED = 'SOLVED'
SOLVE_LATER = 'SOLVE_LATER'
SKIP = 'SKIP'


"""
def process_bulk_query(bulk_list, cnt_dict, problem_solved_list):
    app.logger.info('process_bulk_query called')
    app.logger.info('bulk_list: ' + json.dumps(bulk_list))
    try:
        rs = requests.session()
        bulk_query = ""
        for cat in bulk_list:
            current_query = {"from": 0, "size": 200, "query": { "bool": { "must": [ { "term": { "category_id": cat["category_id"]}}]}}}
            query_str = "{}" + "\n" + str(current_query) + "\n"
            bulk_query += str(query_str)

        bulk_query += "\n"
        app.logger.debug('body: ' + json.dumps(bulk_query))
        url = 'http://{}/{}/_msearch'.format(app.config['ES_HOST'], _es_index_category_problem)
        response_list = rs.post(url=url, json=bulk_query, headers=_http_headers).json()
        app.logger.debug('response_list: ' + json.dumps(response_list))

        if 'responses' in response_list:
            for idx, response in enumerate(response_list['responses']):
                for hit in response['hits']['hits']:
                    edge = hit['_source']
                    problem_id = edge['problem_id']
                    cat_id = edge['problem_id']
                    if cat_id not in cnt_dict:
                        cnt_dict[cat_id] = 0
                    if problem_id in problem_solved_list:
                        cnt_dict[cat_id] += 1
        raise Exception('Internal server error')
    except Exception as e:
        raise e
"""


def category_wise_problem_solve_for_user(user_id):
    try:
        category_list = search_categories({}, 0, _es_size)
        solved_problems = find_problems_for_user_by_status_filtered(['SOLVED'], user_id)
        cnt_dict = {}
        for category in category_list:
            rs = requests.session()
            query = {"from": 0, "size": 200, "query": { "bool": { "must": [ { "term": { "category_id": category["category_id"]}}]}}}
            url = 'http://{}/{}/_search'.format(app.config['ES_HOST'], _es_index_category_problem)
            response = rs.post(url=url, json=query, headers=_http_headers).json()
            if 'hits' in response:
                for hit in response['hits']['hits']:
                    edge = hit['_source']
                    problem_id = edge['problem_id']
                    problem_details = get_problem_details(problem_id)
                    problem_diff = int(problem_details['problem_difficulty'])
                    cat_id = edge['category_id']
                    if cat_id not in cnt_dict:
                        cnt_dict[cat_id] = {
                            'total_count': 0,
                            'difficulty_wise_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                        }
                    if problem_id in solved_problems:
                        cnt_dict[cat_id]['difficulty_wise_count'][problem_diff] += 1
                        cnt_dict[cat_id]['total_count'] += 1
                        print(cnt_dict[cat_id])
        for cat in category_list:
            cat_id = cat['category_id']
            cat['solved_stat'] = cnt_dict.get(cat_id, {'total_count': 0, 'difficulty_wise_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]})
        return category_list
    except Exception as e:
        raise e


def sync_category_score_for_user(user_id):
    category_list = category_wise_problem_solve_for_user(user_id)

    for category in category_list:
        skill_generator = SkillGenerator()
        skill_stat = skill_generator.generate_skill(category['solved_stat']['difficulty_wise_count'])
        category_score_generator = CategoryScoreGenerator()
        skill_obj = Skill()
        cat_score = category_score_generator.generate_score()

        data = {
            'relevant_score': cat_score['score'],
            'skill_value': skill_stat['skill'],
            'skill_level': skill_stat['level'],
            'skill_title': skill_obj.get_skill_title(skill_stat['skill']),
            'solve_count': category['solved_stat']['total_count'],
        }
        add_user_category_data(user_id, category['id'], data)


def sync_problem_score_for_user(user_id):
    problem_list = available_problems_for_user(user_id)

    for problem in problem_list:
        dependent_categories = find_problem_dependency_list(problem['id'])
        for category in dependent_categories:
            category_id = category['category_id']
            category_details = get_user_category_data(user_id, category_id)
            category_level = 0
            if category_details:
                category_level = category_details.get('skill_level', 0)

            problem_score_generator = ProblemScoreGenerator()
            relevant_score = problem_score_generator.generate_score(problem['problem_difficulty'], category_level)
            data = {
                'problem_id': problem['id'],
                'relevant_score': relevant_score,
                'user_id': user_id,
                'status': 'UNSOLVED'
            }
            add_user_problem_status(user_id, problem['id'], data)
