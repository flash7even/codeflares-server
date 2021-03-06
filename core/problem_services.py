import json
import time
import string
import re

import requests
from flask import current_app as app

from core.resource_services import search_resource
from core.comment_services import get_comment_list, get_comment_count
from core.vote_services import get_vote_count_list
from core.user_category_edge_services import get_user_category_data, add_user_category_data
from models.category_skill_model import CategorySkillGenerator
from core.user_services import get_user_details

from commons.skillset import Skill

_http_headers = {'Content-Type': 'application/json'}

_es_index_problem_user = 'cfs_user_problem_edges'
_es_index_problem = 'cfs_problems'
_es_index_category = 'cfs_categories'
_es_type = '_doc'
_es_size = 2000
_es_max_solved_problem = 2000

SOLVED = 'SOLVED'
UNSOLVED = 'UNSOLVED'
SOLVE_LATER = 'SOLVE_LATER'
FLAGGED = 'FLAGGED'


def create_problem_id(problem_name):
    regex = re.compile('[%s]' % re.escape(string.punctuation))
    problem_id = regex.sub('-', problem_name)
    return problem_id


def merge_problem_data(existing_data, new_data):
    final_categories = []
    final_categorie_map = {}

    categories_1 = existing_data['categories']
    categories_2 = new_data['categories']

    for f in new_data:
        if f == 'categories':
            continue
        if f == 'problem_difficulty':
            problem_difficulty = (float(existing_data['problem_difficulty']) + float(new_data['problem_difficulty']))/2
            existing_data[f] = problem_difficulty
        else:
            existing_data[f] = new_data[f]

    for cat in categories_1:
        category_id = cat['category_id']
        final_categorie_map[category_id] = cat

    for cat in categories_2:
        category_id = cat['category_id']
        if category_id in final_categorie_map:
            dependency_factor = (float(cat['dependency_factor']) + float(final_categorie_map[category_id]['dependency_factor']))/2
            final_categorie_map[category_id]['dependency_factor'] = dependency_factor
        else:
            final_categorie_map[category_id] = cat

    for category_id in final_categorie_map:
        final_categories.append(final_categorie_map[category_id])

    existing_data['categories'] = final_categories
    return existing_data


def get_solved_count_for_problem(problem_id):
    try:
        rs = requests.session()
        must = [
            {'term': {'problem_id': problem_id}},
            {'term': {'status': SOLVED}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 0
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            return response['hits']['total']['value']
        return 0
    except Exception as e:
        raise e


def get_problem_details_es_fields(problem_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem, _es_type, problem_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                return data
        return None
    except Exception as e:
        raise e


def get_problem_details(problem_id, user_id = None):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem, _es_type, problem_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
                data['comment_list'] = get_comment_list(response['_id'])
                data['vote_count'] = get_vote_count_list(response['_id'])
                data['solve_count'] = get_solved_count_for_problem(response['_id'])
                data['comment_count'] = get_comment_count(response['_id'])
                data['resource_list'] = search_resource({'resource_ref_id': response['_id']}, 0, _es_size)
                if user_id:
                    edge = get_user_problem_status(user_id, problem_id)
                    if edge:
                        data['user_status'] = edge['status']
                return data
        return None
    except Exception as e:
        raise e


def search_problems_by_category(param, heavy = False):
    user_id = param.get('user_id', None)
    param.pop('user_id', None)
    try:
        problem_list = search_problem_list_simplified(param)
        item_list = []
        for problem_id in problem_list:
            problem_details = get_problem_details(problem_id)
            problem_details['solved'] = 'no'
            if user_id:
                edge = get_user_problem_status(user_id, problem_id)
                if edge and edge['status'] == SOLVED:
                    problem_details['solved'] = 'yes'

            if heavy:
                dependency_list = find_problem_dependency_list(problem_id)
                problem_details['category_dependency_list'] = dependency_list

            problem_details['solve_count'] = get_solved_count_for_problem(problem_id)

            item_list.append(problem_details)
        return item_list
    except Exception as e:
        raise e


def search_problems_by_category_dt_search(param, start, length, sort_by, sort_order):
    user_id = param.get('user_id', None)
    param.pop('user_id', None)
    try:
        problem_stat = search_problem_list_simplified_dtsearch(param, start, length, sort_by, sort_order)
        item_list = []
        for problem_id in problem_stat['problem_list']:
            problem_details = get_problem_details(problem_id)
            problem_details['solved'] = 'no'
            if user_id:
                edge = get_user_problem_status(user_id, problem_id)
                if edge and edge['status'] == SOLVED:
                    problem_details['solved'] = 'yes'

            dependency_list = find_problem_dependency_list(problem_id)
            problem_details['category_dependency_list'] = dependency_list

            problem_details['solve_count'] = get_solved_count_for_problem(problem_id)

            item_list.append(problem_details)
        return {
            'problem_list': item_list,
            'total': problem_stat['total']
        }
    except Exception as e:
        raise e


def get_user_problem_status(user_id, problem_id):
    try:
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'problem_id': problem_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            for hit in response['hits']['hits']:
                edge = hit['_source']
                edge['id'] = hit['_id']
                return edge
        return None

    except Exception as e:
        raise e


def get_solved_problem_count_for_user(user_id):
    try:
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'status': SOLVED}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            return response['hits']['total']['value']
        return 0
    except Exception as e:
        raise e


def get_total_problem_score_for_user(user_list):
    try:
        rs = requests.session()
        score_sum = 0
        marked_problem = {}
        for user_id in user_list:
            app.logger.info(f'check for user: {user_id}')
            must = [
                {'term': {'user_id': user_id}},
                {'term': {'status': SOLVED}}
            ]
            query_json = {'query': {'bool': {'must': must}}}
            query_json['size'] = _es_size
            search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
            response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
            if 'hits' in response:
                for hit in response['hits']['hits']:
                    edge = hit['_source']
                    problem_id = edge['problem_id']
                    if problem_id not in marked_problem:
                        marked_problem[problem_id] = 1
                        url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem, _es_type, problem_id)
                        presponse = rs.get(url=url, headers=_http_headers).json()
                        if 'found' in presponse and presponse['found']:
                            problem_details = presponse['_source']
                            skill = Skill()
                            score_sum += skill.get_problem_score(problem_details['problem_difficulty'])
        return score_sum
    except Exception as e:
        raise e


def find_problems_for_user_by_status_filtered(status, user_id, heavy=False):
    try:
        rs = requests.session()

        should = []
        for s in status:
            should.append({'term': {'status': s}})

        must = [
            {'term': {'user_id': user_id}},
            {"bool": {"should": should}}
        ]

        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_max_solved_problem
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        problem_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                edge = hit['_source']
                if heavy:
                    problem = get_problem_details(edge['problem_id'])
                    problem['user_status'] = edge['status']
                    if problem['user_status'] == FLAGGED:
                        problem['user_status_title'] = 'Blacklisted'
                    if problem['user_status'] == SOLVE_LATER:
                        problem['user_status_title'] = 'Flagged for 3 Days'
                    problem_list.append(problem)
                else:
                    problem_list.append(edge['problem_id'])
        return problem_list
    except Exception as e:
        raise e


def find_problems_by_status_filtered_for_user_list(status, user_list, heavy=False):
    try:
        data_list = []
        for user_id in user_list:
            item_list = find_problems_for_user_by_status_filtered(status, user_id, heavy)
            data_list = data_list + item_list
        return data_list
    except Exception as e:
        raise e


def available_problems_for_user(user_id):
    try:
        problem_list = search_problems({}, 0, _es_size)
        available_list = []
        for problem in problem_list:
            edge = get_user_problem_status(user_id, problem['id'])
            if edge is None:
                available_list.append(problem)
            else:
                status = edge.get('status', None)
                if status == UNSOLVED:
                    available_list.append(problem)
        return available_list
    except Exception as e:
        raise e


def add_user_problem_status(user_id, problem_id, data):
    try:
        rs = requests.session()
        edge = get_user_problem_status(user_id, problem_id)

        if edge is None:
            data['created_at'] = int(time.time())
            data['updated_at'] = int(time.time())
            post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
            response = rs.post(url=post_url, json=data, headers=_http_headers).json()
            if 'result' in response:
                return response['_id']
            raise Exception('Internal server error')

        edge_id = edge['id']
        edge.pop('id', None)

        for f in data:
            edge[f] = data[f]

        edge['updated_at'] = int(time.time())

        url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type, edge_id)
        response = rs.put(url=url, json=edge, headers=_http_headers).json()

        if 'result' in response:
            return response['result']
        raise Exception('Internal server error')
    except Exception as e:
        raise Exception('Internal server error')


def apply_solved_problem_for_user(user_id, problem_id, problem_details, submission_list, updated_categories, root_category_solve_count):
    app.logger.info(f'apply_solved_problem_for_user for user_id: {user_id}, problem_id: {problem_id}')
    app.logger.info('current updated_categories: ' + json.dumps(updated_categories))
    try:
        skill_info = Skill()
        up_edge = get_user_problem_status(user_id, problem_id)
        if up_edge is not None and up_edge['status'] == SOLVED:
            return
        rs = requests.session()
        data = {
            'user_id': user_id,
            'problem_id': problem_id,
            'submission_list': submission_list,
            'status': SOLVED
        }
        # Insert User Problem Solved Status Here
        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()

        if 'result' not in response:
            raise Exception('Internal server error')

        # Update dependent category skill
        problem_difficulty = problem_details['problem_difficulty']
        app.logger.info(f'problem_difficulty: {problem_difficulty}')
        dep_cat_list = problem_details.get('categories', [])
        cat_skill_model = CategorySkillGenerator()
        marked_roots = {}
        for cat in dep_cat_list:
            app.logger.info(f'dept cat: {cat}')
            category_id = cat['category_id']
            category_details = get_category_details(category_id)
            category_root = category_details['category_root']
            app.logger.info(f'category_root: {category_root}')
            if category_root not in marked_roots:
                if category_root not in root_category_solve_count:
                    root_category_solve_count[category_root] = 0
                root_category_solve_count[category_root] += 1
                marked_roots[category_root] = 1
            if category_id in updated_categories:
                uc_edge = updated_categories[category_id]
            else:
                uc_edge = get_user_category_data(user_id, category_id)
                if uc_edge:
                    uc_edge['old_skill_level'] = uc_edge['skill_level']
                    uc_edge.pop('id', None)
            app.logger.info(f'uc_edge from es: {uc_edge}')
            if uc_edge is None:
                uc_edge = {
                    "category_id": category_id,
                    "category_root": category_root,
                    "user_id": user_id,
                    "skill_value": 0,
                    "skill_level": 0,
                    "old_skill_level": 0,
                    "relevant_score": 0,
                    "solve_count": 0,
                    "skill_value_by_percentage": 0,
                }
                for d in range(1, 11):
                    key = 'scd_' + str(d)
                    uc_edge[key] = 0

            app.logger.info(f'current uc_edge: {uc_edge}')
            dif_key = 'scd_' + str(int(problem_difficulty))
            uc_edge[dif_key] += 1
            problem_factor = category_details.get('factor', 1)
            added_skill = cat_skill_model.get_score_for_latest_solved_problem(problem_difficulty, uc_edge[dif_key], problem_factor)
            uc_edge['skill_value'] += added_skill
            uc_edge['solve_count'] += 1
            uc_edge['skill_title'] = skill_info.get_skill_title(uc_edge['skill_value'])
            uc_edge['skill_level'] = skill_info.get_skill_level_from_skill(uc_edge['skill_value'])
            score_percentage = float(category_details['score_percentage'])
            uc_edge['skill_value_by_percentage'] = uc_edge['skill_value']*score_percentage/100
            app.logger.info(f'add uc_edge: {uc_edge}')
            updated_categories[category_id] = uc_edge
            app.logger.info(f'saved at category_id: {category_id}')
    except Exception as e:
        app.logger.error(f'Exception occurred: {e}')
        raise Exception('Internal server error')


def get_category_details(cat_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_category, _es_type, cat_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                return data
        return None
    except Exception as e:
        raise e


def find_problem_dependency_list(problem_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem, _es_type, problem_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        item_list = []
        if 'found' in response:
            if response['found']:
                data = response['_source']
                categories = data.get('categories', [])
                for category in categories:
                    category['category_info'] = get_category_details(category['category_id'])
                    item_list.append(category)
        return item_list
    except Exception as e:
        raise e


def generate_query_params(param):
    if 'filter' in param and param['filter']:
        should = []
        nested_should = []
        nested_should.append({'term': {'categories.category_id': param['filter']}})
        nested_should.append({'term': {'categories.category_name': param['filter']}})
        nested_should.append({'term': {'categories.category_root': param['filter']}})
        should.append({'term': {'problem_title': param['filter']}})
        should.append({'match': {'problem_name': param['filter']}})
        should.append({'term': {'oj_name': param['filter']}})
        should.append({'nested': {'path': 'categories', 'query': {'bool': {'should': nested_should}}}})
        query_json = {'query': {'bool': {'should': should}}}
        return query_json
    else:
        must = []
        nested_must = []
        nested_fields = ['category_id', 'category_name', 'category_root']
        keyword_fields = ['problem_title', 'problem_id', 'problem_difficulty', 'oj_name', 'active_status']
        text_fields = ['problem_name']

        if 'category_id' in param:
            nested_must.append({'term': {'categories.category_id': param['category_id']}})
        if 'category_name' in param:
            nested_must.append({'term': {'categories.category_name': param['category_name']}})
        if 'category_root' in param:
            nested_must.append({'term': {'categories.category_root': param['category_root']}})

        minimum_difficulty = 0
        maximum_difficulty = 100

        if 'minimum_difficulty' in param and param['minimum_difficulty']:
            minimum_difficulty = int(param['minimum_difficulty'])

        if 'maximum_difficulty' in param and param['maximum_difficulty']:
            maximum_difficulty = int(param['maximum_difficulty'])

        if minimum_difficulty > 0 or maximum_difficulty < 100:
            must.append({"range": {"problem_difficulty": {"gte": minimum_difficulty, "lte": maximum_difficulty}}})

        if len(nested_must) > 0:
            must.append({'nested': {'path': 'categories', 'query': {'bool': {'must': nested_must}}}})

        for f in keyword_fields:
            if f in param:
                must.append({'term': {f: param[f]}})

        for f in text_fields:
            if f in param:
                must.append({'match': {f: param[f]}})

        query_json = {'query': {'match_all': {}}}
        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}
        return query_json


def search_problem_list_simplified(param, sort_by='problem_difficulty', sort_order='asc'):
    try:
        rs = requests.session()
        query_json = generate_query_params(param)
        query_json['_source'] = "{}"
        query_json['size'] = _es_size
        query_json['sort'] = [{sort_by: {'order': sort_order}}]
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                item_list.append(hit['_id'])
        return item_list
    except Exception as e:
        raise e


def search_problem_list_simplified_dtsearch(param, start, length, sort_by, sort_order):
    try:
        rs = requests.session()
        query_json = generate_query_params(param)
        query_json['_source'] = "{}"
        query_json['from'] = start
        query_json['size'] = length
        query_json['sort'] = [{sort_by: {'order': sort_order}}]
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                item_list.append(hit['_id'])
        return {
            'problem_list': item_list,
            'total': response['hits']['total']['value']
        }
    except Exception as e:
        raise e


def search_problems(param, from_value, size_value, heavy = False):
    try:
        rs = requests.session()
        query_json = generate_query_params(param)
        query_json['from'] = from_value
        query_json['size'] = size_value
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                dependency_list = find_problem_dependency_list(data['id'])
                if heavy:
                    data['category_dependency_list'] = dependency_list
                    data['solve_count'] = get_solved_count_for_problem(data['id'])
                item_list.append(data)
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def search_problems_filtered_by_categories(categories):
    app.logger.info('search_problems_filtered_by_categories called')
    try:
        rs = requests.session()
        should = []
        for category_id in categories:
            uc_edge = categories[category_id]
            dif_level = float(uc_edge['skill_level'])
            level_min = max(0.0, dif_level-1.5)
            level_max = min(10.0, dif_level+1.5)
            must = [
                {'nested': {'path': 'categories', 'query': {'bool': {'must': [{'term': {'categories.category_id': category_id}}]}}}},
                {"range": {"problem_difficulty": {"gte": level_min, "lte": level_max}}}
            ]
            item = {"bool": {"must": must}}
            should.append(item)

        query_json = {'query': {'match_all': {}}}
        if len(should) > 0:
            query_json = {'query': {'bool': {'should': should}}}

        query_json['from'] = 0
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                data['id'] = hit['_id']
                item_list.append(data)
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def get_problem_count_for_category(param):
    try:
        rs = requests.session()
        query_json = generate_query_params(param)
        query_json['size'] = 0
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            return response['hits']['total']['value']
        return 0
    except Exception as e:
        raise e


def get_problem_submission_history(problem_id, start, size):
    try:
        rs = requests.session()
        must = [
            {'term': {'problem_id': problem_id}},
            {'term': {'status': SOLVED}},
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['from'] = start
        query_json['size'] = size
        query_json['sort'] = [{'updated_at': {'order': 'desc'}}]
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        submission_list = []
        resp = {}
        if 'hits' in response:
            order = 1
            resp['total'] = response['hits']['total']['value']
            for hit in response['hits']['hits']:
                edge = hit['_source']
                user_id = edge['user_id']
                user_data = get_user_details(user_id)
                edge['user_handle'] = user_data['username']
                edge['user_skill_color'] = user_data['skill_color']
                edge['order'] = order+start
                submission_list.append(edge)
                order += 1
            resp['submission_list'] = submission_list
            return resp
        raise Exception('Elasticsearch down')
    except Exception as e:
        raise e


def get_user_problem_submission_history(user_id, start, size):
    try:
        rs = requests.session()
        must = [
            {'term': {'user_id': user_id}},
            {'term': {'status': SOLVED}},
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['from'] = start
        query_json['size'] = size
        query_json['sort'] = [{'updated_at': {'order': 'desc'}}]
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        submission_list = []
        resp = {}
        if 'hits' in response:
            order = 1
            resp['total'] = response['hits']['total']['value']
            for hit in response['hits']['hits']:
                edge = hit['_source']
                user_id = edge['user_id']
                user_data = get_user_details(user_id)
                edge['user_handle'] = user_data['username']
                edge['user_skill_color'] = user_data['skill_color']
                edge['order'] = order+start
                edge['problem_details'] = get_problem_details(edge['problem_id'])
                submission_list.append(edge)
                order += 1
            resp['submission_list'] = submission_list
            return resp
        raise Exception('Elasticsearch down')
    except Exception as e:
        raise e
