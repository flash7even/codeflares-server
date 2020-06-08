import time
import json
import requests
from flask import current_app as app

from commons.skillset import Skill
from models.category_skill_model import CategorySkillGenerator
from models.category_score_model import CategoryScoreGenerator
from models.problem_score_model import ProblemScoreGenerator

from core.category_services import search_categories, find_category_dependency_list, get_category_details, find_category_dependency_list_for_multiple_categories

from core.problem_services import get_problem_details, get_solved_problem_count_for_user, \
    find_problems_for_user_by_status_filtered, available_problems_for_user, add_user_problem_status, \
    find_problem_dependency_list, search_problems
from core.user_category_edge_services import add_user_category_data, get_user_category_data
from core.team_services import get_team_details, update_team_details
from core.user_services import get_user_details_by_handle_name, update_user_details

_http_headers = {'Content-Type': 'application/json'}


_es_index_problem_user = 'cfs_user_problem_edges'
_es_index_user_category = 'cfs_user_category_edges'
_es_index_problem = 'cfs_problems'
_es_type = '_doc'
_es_size = 500
_es_max_solved_problem = 1000
_bulk_size = 20

SOLVED = 'SOLVED'
SOLVE_LATER = 'SOLVE_LATER'
SKIP = 'SKIP'


def generate_skill_value_for_user(user_id):
    app.logger.info('generate_skill_value_for_user: ' + str(user_id))
    rs = requests.session()
    must = [
        {'term': {'category_root': 'root'}},
        {'term': {'user_id': user_id}},
    ]
    query_json = {'query': {'bool': {'must': must}}}
    query_json['size'] = _es_size

    app.logger.info('generate_skill_value_for_user query_json: ' + json.dumps(query_json))
    search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_category, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
    app.logger.info('generate_skill_value_for_user response: ' + str(response))

    if 'hits' not in response:
        raise Exception('Internal server error')

    skill_value = 0
    if 'hits' in response:
        for hit in response['hits']['hits']:
            data = hit['_source']
            skill_value += data['skill_value_by_percentage']

    app.logger.info('skill_value found: ' + str(skill_value))
    return skill_value


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
                item['relevant_score'] = "{:.2f}".format(item['relevant_score'])
                if heavy:
                    item['category_info'] = get_category_details(item['category_id'])
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
                item['relevant_score'] = "{:.2f}".format(item['relevant_score'])
                if heavy:
                    item['problem_info'] = get_problem_details(item['problem_id'])
                item_list.append(item)
        return item_list
    except Exception as e:
        raise e


def category_wise_problem_solve_for_users(user_list):
    try:
        solved_problems = []
        for user_id in user_list:
            cur_list = find_problems_for_user_by_status_filtered(['SOLVED'], user_id)
            for problem in cur_list:
                if problem not in solved_problems:
                    solved_problems.append(problem)

        cnt_dict = {}
        category_list = search_categories({}, 0, _es_size)
        for category in category_list:
            category_id = category['category_id']
            param = {"category_id": category_id}
            problem_list = search_problems(param, 0, _es_size)
            for problem in problem_list:
                problem_id = problem['id']
                problem_diff = int(float(problem['problem_difficulty']))
                if category_id not in cnt_dict:
                    cnt_dict[category_id] = {
                        'total_count': 0,
                        'difficulty_wise_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                    }
                if problem_id in solved_problems:
                    cnt_dict[category_id]['difficulty_wise_count'][problem_diff] += 1
                    cnt_dict[category_id]['total_count'] += 1
        for cat in category_list:
            cat_id = cat['category_id']
            cat['solved_stat'] = cnt_dict.get(cat_id, {'total_count': 0, 'difficulty_wise_count': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]})
        return category_list
    except Exception as e:
        raise e


def generate_sync_data_for_root_category(user_id, category, root_solved_count):
    try:
        rs = requests.session()
        skill_obj = Skill()
        must = [
            {'term': {'category_root': category['category_name']}},
            {'term': {'user_id': user_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        aggregate = {
            "skill_value_by_percentage": {"sum": {"field": "skill_value_by_percentage"}}
        }
        query_json['aggs'] = aggregate
        query_json['size'] = 0

        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_user_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        if 'aggregations' not in response:
            raise Exception('Internal server error')

        skill_value = response['aggregations']['skill_value_by_percentage']['value']
        root_category_percentage = float(category.get('score_percentage', 100))
        skill_value_by_percentage_sum = skill_value*root_category_percentage/100
        skill_level = skill_obj.get_skill_level_from_skill(skill_value)

        data = {
            'relevant_score': -1,
            'skill_value': skill_value,
            'skill_value_by_percentage': skill_value_by_percentage_sum,
            'skill_level': skill_level,
            'skill_title': skill_obj.get_skill_title(skill_level),
            'solve_count': root_solved_count.get(category['category_name'], 0),
            'category_root': 'root',
        }
        return data
    except Exception as e:
        raise e


def root_category_solved_count_by_solved_problem_list(solve_problems):
    try:
        root_solved_count = {}
        for problem in solve_problems:
            dependent_categories = find_problem_dependency_list(problem)
            for category in dependent_categories:
                if 'category_info' in category and category['category_info']:
                    category_root = category['category_info']['category_root']
                    if category_root not in root_solved_count:
                        root_solved_count[category_root] = 0
                    root_solved_count[category_root] += 1
        return root_solved_count
    except Exception as e:
        raise e


def sync_root_category_score_for_user(user_id):
    try:
        app.logger.debug(f'sync_root_category_score_for_user called for user_id: {user_id}')
        solved_problems = find_problems_for_user_by_status_filtered(['SOLVED'], user_id)
        root_solved_count = root_category_solved_count_by_solved_problem_list(solved_problems)
        app.logger.info('root_solved_count: ' + json.dumps(root_solved_count))
        category_list = search_categories({'category_root': 'root'}, 0, _es_size)
        skill_value = 0
        for category in category_list:
            data = generate_sync_data_for_root_category(user_id, category, root_solved_count)
            skill_value += data['skill_value_by_percentage']
            app.logger.debug(f'Insert root category synced data: {json.dumps(data)}')
            add_user_category_data(user_id, category['category_id'], data)

        app.logger.debug(f'sync_root_category_score_for_user completed for user_id: {user_id}')
        return skill_value
    except Exception as e:
        raise e


def generate_sync_data_for_category(user_id, category):
    try:
        app.logger.info(f'generate_sync_data_for_category for user_id: {user_id}, category: {category}')
        category_skill_generator = CategorySkillGenerator()
        factor = float(category.get('factor', 1))
        skill_stat = category_skill_generator.generate_skill(category['solved_stat']['difficulty_wise_count'], factor)

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
        skill_obj = Skill()

        category_percentage = float(category.get('score_percentage', 100))

        data = {
            'relevant_score': cat_score['score'],
            'skill_value': skill_stat['skill'],
            'skill_value_by_percentage': float(skill_stat['skill'])*category_percentage/100.0,
            'skill_level': skill_stat['level'],
            'skill_title': skill_obj.get_skill_title(skill_stat['skill']),
            'solve_count': category['solved_stat']['total_count'],
            'category_root': category['category_root'],
        }

        return data
    except Exception as e:
        raise e


def sync_category_score_for_user(user_id):
    try:
        app.logger.debug(f'sync_category_score_for_user called for user_id: {user_id}')
        category_list = category_wise_problem_solve_for_users([user_id])
        app.logger.debug(f'category wise solve problem stat: {json.dumps(category_list)}')

        for category in category_list:
            if category['category_root'] == 'root':
                continue
            data = generate_sync_data_for_category(user_id, category)
            print('after sync data: ', data)
            add_user_category_data(user_id, category['category_id'], data)
    except Exception as e:
        raise e


def generate_sync_data_for_problem(user_id, user_skill_level, problem):
    try:
        dependent_categories = find_problem_dependency_list(problem['id'])
        problem_score_generator = ProblemScoreGenerator()
        if problem['problem_type'] == 'classical':
            app.logger.info(f'CLASSICAL_CASE, problem data: {json.dumps(problem)}')
            dependent_category_id_list = []
            app.logger.info('dependent_categories: ' + str(dependent_categories))
            for category in dependent_categories:
                category_id = category['category_id']
                dependent_category_id_list.append(category_id)

            app.logger.info('dependent_category_id_list: ' + str(dependent_category_id_list))
            dependent_dependent_category_list = find_category_dependency_list_for_multiple_categories(dependent_category_id_list)
            app.logger.info('dependent_dependent_category_list: ' + str(dependent_dependent_category_list))
            category_level_list = []
            for category_id in dependent_dependent_category_list:
                category_details = get_user_category_data(user_id, category_id)
                category_level = 0
                if category_details:
                    category_level = category_details.get('skill_level', 0)
                category_level_list.append(category_level)
            relevant_score = problem_score_generator.generate_score(int(float(problem['problem_difficulty'])),
                                                                    category_level_list, user_skill_level)
            app.logger.debug(f'CLASSICAL_CASE relevant_score: {str(relevant_score)}')
        else:
            category_level_list = []
            for category in dependent_categories:
                category_id = category['category_id']
                category_details = get_user_category_data(user_id, category_id)
                category_level = 0
                if category_details:
                    category_level = category_details.get('skill_level', 0)
                category_level_list.append(category_level)
            relevant_score = problem_score_generator.generate_score(int(float(problem['problem_difficulty'])),
                                                                    category_level_list, user_skill_level)
        data = {
            'problem_id': problem['id'],
            'relevant_score': relevant_score['score'],
            'user_id': user_id,
            'status': 'UNSOLVED'
        }
        return data
    except Exception as e:
        raise e


def sync_problem_score_for_user(user_id, user_skill_level):
    try:
        app.logger.debug(f'sync_problem_score_for_user called for user: {user_id}')
        problem_list = available_problems_for_user(user_id)
        for problem in problem_list:
            data = generate_sync_data_for_problem(user_id, user_skill_level, problem)
            add_user_problem_status(user_id, problem['id'], data)
    except Exception as e:
        raise e


def sync_overall_stat_for_user(user_id, skill_value = None):
    try:
        app.logger.debug(f'sync_overall_stat_for_user, user: {user_id}')
        solve_count = get_solved_problem_count_for_user(user_id)
        if skill_value is None:
            skill_value = generate_skill_value_for_user(user_id)
        skill_obj = Skill()
        skill_title = skill_obj.get_skill_title(skill_value)
        user_data = {
            'skill_value': int(skill_value),
            'solve_count': int(solve_count),
            'skill_title': skill_title,
        }
        app.logger.debug('User final stat to update: ' + json.dumps(user_data))
        update_user_details(user_id, user_data)
    except Exception as e:
        raise e


def sync_problem_score_for_team(team_id, user_skill_level):
    try:
        app.logger.debug(f'sync_problem_score_for_team called for team_id: {team_id}')
        team_details = get_team_details(team_id)
        marked_list = {}
        for member in team_details['member_list']:
            user_details = get_user_details_by_handle_name(member['user_handle'])
            if user_details is None:
                continue
            user_id = user_details['id']
            problem_list = available_problems_for_user(user_id)
            for problem in problem_list:
                problem_id = problem['id']
                if problem_id in marked_list:
                    continue
                marked_list[problem_id] = 1
                data = generate_sync_data_for_problem(team_id, user_skill_level, problem)
                add_user_problem_status(team_id, problem['id'], data)
    except Exception as e:
        raise e


def sync_category_score_for_team(team_id):
    try:
        app.logger.debug(f'sync_category_score_for_team called for team_id: {team_id}')
        team_details = get_team_details(team_id)
        user_list = []
        for member in team_details['member_list']:
            user_details = get_user_details_by_handle_name(member['user_handle'])
            if user_details is None:
                continue
            user_list.append(user_details['id'])

        category_list = category_wise_problem_solve_for_users(user_list)
        for category in category_list:
            if category['category_root'] == 'root':
                continue
            data = generate_sync_data_for_category(team_id, category)
            add_user_category_data(team_id, category['category_id'], data)
    except Exception as e:
        raise e


def sync_root_category_score_for_team(team_id):
    try:
        app.logger.debug(f'sync_root_category_score_for_team called for team_id: {team_id}')
        team_details = get_team_details(team_id)
        solved_problems = []
        for member in team_details['member_list']:
            user_details = get_user_details_by_handle_name(member['user_handle'])
            if user_details is None:
                continue
            user_id = user_details['id']
            problem_list = find_problems_for_user_by_status_filtered(['SOLVED'], user_id)
            for problem in problem_list:
                if problem not in solved_problems:
                    solved_problems.append(problem)

        root_solved_count = root_category_solved_count_by_solved_problem_list(solved_problems)
        category_list = search_categories({'category_root': 'root'}, 0, 100)
        skill_value = 0
        for category in category_list:
            data = generate_sync_data_for_root_category(team_id, category, root_solved_count)
            add_user_category_data(team_id, category['category_id'], data)
            skill_value += data['skill_value_by_percentage']

        return skill_value
    except Exception as e:
        raise e


def sync_overall_stat_for_team(team_id, skill_value = None):
    try:
        app.logger.debug(f'sync_overall_stat_for_team, team: {team_id}')
        team_details = get_team_details(team_id)
        mark_problem = {}
        solve_count = 0
        for member in team_details['member_list']:
            user_details = get_user_details_by_handle_name(member['user_handle'])
            if user_details is None:
                continue
            user_id = user_details['id']
            problem_list = find_problems_for_user_by_status_filtered(['SOLVED'], user_id)
            for problem in problem_list:
                if problem not in mark_problem:
                    mark_problem[problem] = 1
                    solve_count += 1

        if skill_value is None:
            skill_value = generate_skill_value_for_user(team_id)
        skill_obj = Skill()
        skill_title = skill_obj.get_skill_title(skill_value)
        skill_data = {
            'skill_value': int(skill_value),
            'solve_count': int(solve_count),
            'skill_title': skill_title,
        }
        app.logger.debug('Team final stat to update: ' + json.dumps(skill_data))
        update_team_details(team_id, skill_data)
    except Exception as e:
        raise e
