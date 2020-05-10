import time
import json
import requests
from flask import current_app as app
from operator import itemgetter

from commons.skillset import Skill
from models.category_skill_model import CategorySkillGenerator
from models.category_score_model import CategoryScoreGenerator
from models.problem_score_model import ProblemScoreGenerator

from core.category_services import search_categories, find_category_dependency_list, get_category_details
from core.problem_services import get_problem_details, find_problems_for_user_by_status_filtered, available_problems_for_user, \
    find_problem_dependency_list, add_user_problem_status
from core.user_model_sync_services import add_user_category_data, get_user_category_data

_http_headers = {'Content-Type': 'application/json'}


_es_index_category_problem = 'cp_training_problem_category_edges'
_es_index_problem_category = 'cp_training_problem_category_edges'
_es_index_problem_user = 'cp_training_user_problem_edges'
_es_index_user_category = 'cp_training_user_category_edges'
_es_index_problem = 'cp_training_problems'
_es_type = '_doc'
_es_size = 500
_es_max_solved_problem = 1000
_bulk_size = 20

SOLVED = 'SOLVED'
SOLVE_LATER = 'SOLVE_LATER'
SKIP = 'SKIP'


def search_top_skilled_categoires_for_user(user_id, category_root, sort_field, size, heavy=False):
    try:
        rs = requests.session()
        must = [{'term': {'user_id': user_id}}]

        if category_root == 'root':
            must.append({'term': {'category_root': 'root'}})
        else:
            must.append({'bool': {'must_not': [{'term': {'category_root': 'root'}}]}})

        query_json = {'query': {'bool': {'must': must}}}

        query_json['from'] = 0
        query_json['size'] = size
        query_json['sort'] = [{sort_field: {'order': 'desc'}}]
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                item = hit['_source']
                if heavy:
                    item['problem_info'] = get_category_details(item['category_id'])
                item_list.append(item)
        return item_list
    except Exception as e:
        raise e


def search_top_skilled_problems_for_user(user_id, sort_field, size, heavy=False):
    try:
        rs = requests.session()
        must = [{'term': {'user_id': user_id}}]
        must.append({'term': {'status': 'UNSOLVED'}})
        query_json = {'query': {'bool': {'must': must}}}

        query_json['from'] = 0
        query_json['size'] = size
        query_json['sort'] = [{sort_field: {'order': 'desc'}}]
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                item = hit['_source']
                if heavy:
                    item['category_info'] = get_problem_details(item['problem_id'])
                item_list.append(item)
        return item_list
    except Exception as e:
        raise e


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


def sync_root_category_score_for_user(user_id):
    skill_obj = Skill()
    rs = requests.session()

    solve_problems = find_problems_for_user_by_status_filtered(['SOLVED'], user_id)
    root_solved_count = {}

    for problem in solve_problems:
        dependent_categories = find_problem_dependency_list(problem)
        for category in dependent_categories:
            if 'category_info' in category and category['category_info']:
                category_root = category['category_info']['category_root']
                if category_root not in root_solved_count:
                    root_solved_count[category_root] = 0
                root_solved_count[category_root] += 1

    category_list = search_categories({'category_root': 'root'}, 0, 100)

    for category in category_list:

        query_json = {'query': {'bool': {'must': [{'term': {'category_root': category['category_name']}}]}}}
        aggregate = {
            "skill_level": {"sum": {"field": "skill_level"}},
            "skill_value": {"sum": {"field": "skill_value"}}
        }
        query_json['aggs'] = aggregate
        query_json['size'] = 0

        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        if 'aggregations' not in response:
            continue

        total_data = response['hits']['total']['value']
        skill_level_sum = response['aggregations']['skill_level']['value']
        skill_value_sum = response['aggregations']['skill_value']['value']

        skill_value = skill_value_sum/total_data
        skill_level = skill_level_sum/total_data

        data = {
            'relevant_score': -1,
            'skill_value': skill_value,
            'skill_level': skill_level,
            'skill_title': skill_obj.get_skill_title(skill_level),
            'solve_count': root_solved_count.get(category['category_name'], 0),
            'category_root': 'root',
        }
        add_user_category_data(user_id, category['category_id'], data)


def sync_category_score_for_user(user_id):
    skill_obj = Skill()
    category_list = category_wise_problem_solve_for_user(user_id)

    for category in category_list:
        if category['category_root'] == 'root':
            continue
        category_skill_generator = CategorySkillGenerator()
        skill_stat = category_skill_generator.generate_skill(category['solved_stat']['difficulty_wise_count'])

        dependent_skill_level = []
        dependent_categories = find_category_dependency_list(category['category_id'])
        for dcat in dependent_categories:
            category_details = get_user_category_data(user_id, dcat['category_id'])
            category_level = 0
            if category_details:
                category_level = category_details.get('skill_level', 0)
            dependent_skill_level.append(category_level)

        category_score_generator = CategoryScoreGenerator()
        cat_score = category_score_generator.generate_score(dependent_skill_level, skill_stat['level'])

        data = {
            'relevant_score': cat_score['score'],
            'skill_value': skill_stat['skill'],
            'skill_level': skill_stat['level'],
            'skill_title': skill_obj.get_skill_title(skill_stat['skill']),
            'solve_count': category['solved_stat']['total_count'],
            'category_root': category['category_root'],
        }
        add_user_category_data(user_id, category['category_id'], data)


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
                'relevant_score': relevant_score['score'],
                'user_id': user_id,
                'status': 'UNSOLVED'
            }
            add_user_problem_status(user_id, problem['id'], data)
