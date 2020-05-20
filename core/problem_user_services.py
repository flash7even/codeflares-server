import time
import json
import requests
from flask import current_app as app

from core.problem_services import get_problem_details, search_problems

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
        app.logger.info('find_solved_problems_of_user method called')
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
        app.logger.info('available_problems_for_user method called')
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
        app.logger.info('add_user_problem_status method called')
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
            app.logger.info('add_user_problem_status method completed')
            return response['result']
        raise Exception('Internal server error')
    except Exception as e:
        raise Exception('Internal server error')


def get_solved_count_per_category_for_user(param):
    try:
        rs = requests.session()
        must = []
        for f in param:
            must.append({'term': {f: param[f]}},)
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 0
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_user, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            return response['hits']['total']['value']
        return 0
    except Exception as e:
        raise e
