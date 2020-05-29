import time

import requests
from flask import current_app as app

from core.problem_category_services import find_problem_dependency_list, search_problem_list_simplified
from core.resource_services import search_resource
from core.comment_services import get_comment_list, get_comment_count
from core.vote_services import get_vote_count_list

_http_headers = {'Content-Type': 'application/json'}

_es_index_problem_category = 'cfs_problem_category_edges'
_es_index_problem_user = 'cfs_user_problem_edges'
_es_index_problem = 'cfs_problems'
_es_type = '_doc'
_es_size = 100
_es_max_solved_problem = 1000

SOLVED = 'SOLVED'
UNSOLVED = 'UNSOLVED'
SOLVE_LATER = 'SOLVE_LATER'
FLAGGED = 'FLAGGED'


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
                    data['user_status'] = edge['status']
                return data
        return None
    except Exception as e:
        raise e


def search_problems(param, from_value, size_value, heavy = False):
    try:
        query_json = {'query': {'match_all': {}}}
        rs = requests.session()

        must = []
        keyword_fields = ['problem_title', 'oj_name', 'problem_id']

        minimum_difficulty = 0
        maximum_difficulty = 100

        if 'minimum_difficulty' in param and param['minimum_difficulty']:
            minimum_difficulty = int(param['minimum_difficulty'])

        if 'maximum_difficulty' in param and param['maximum_difficulty']:
            maximum_difficulty = int(param['maximum_difficulty'])

        param.pop('minimum_difficulty', None)
        param.pop('maximum_difficulty', None)

        for f in param:
            if f in keyword_fields:
                if param[f]:
                    must.append({'term': {f: param[f]}})
            else:
                if param[f]:
                    must.append({'match': {f: param[f]}})

        must.append({"range": {"problem_difficulty": {"gte": minimum_difficulty, "lte": maximum_difficulty}}})

        if len(must) > 0:
            query_json = {'query': {'bool': {'must': must}}}

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
                    data['category_dependency_list'] = dependency_list['dependency_list']
                    data['category_list_light'] = dependency_list['light_data']
                item_list.append(data)
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
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
                print('EDGE: ', edge)
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
        print('query_json: ', query_json)
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        print('response: ', response)

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
        print('problem_list found')
        available_list = []
        for problem in problem_list:
            edge = get_user_problem_status(user_id, problem['id'])
            if edge is None:
                available_list.append(problem)
            else:
                status = edge.get('status', None)
                if status == UNSOLVED:
                    available_list.append(problem)
        print('available_list found')
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