import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

_es_index_category = 'cfs_categories'
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


def add_problem_category_dependency(data):
    try:
        rs = requests.session()

        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem_category, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()

        if 'result' in response and response['result'] == 'created':
            return response['_id'], 201
        app.logger.error('Elasticsearch down, response: ' + str(response))
        raise Exception('Internal server error')
    except Exception as e:
        raise e


def find_problem_dependency_list(problem_id):
    try:
        rs = requests.session()
        must = [
            {'term': {'problem_id': problem_id}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                category = hit['_source']
                category['category_info'] = get_category_details(category['category_id'])
                item_list.append(category)
        return item_list
    except Exception as e:
        raise e


def search_problem_list_simplified(param, sort_by = 'problem_difficulty', sort_order = 'asc'):
    print('search_problem_list_simplified called: ', param)
    try:
        query_json = {'query': {'match_all': {}}}
        rs = requests.session()

        must = []
        keyword_fields = ['problem_id', 'problem_difficulty', 'category_id', 'category_name', 'category_root']

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

        query_json['size'] = _es_size
        query_json['sort'] = [{sort_by: {'order': sort_order}}]

        print('query_json: ', json.dumps(query_json))

        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []

        if 'hits' in response:
            for hit in response['hits']['hits']:
                data = hit['_source']
                item_list.append(data['problem_id'])

        print('item_list: ', item_list)
        return item_list
    except Exception as e:
        raise e


def get_problem_count_for_category(param):
    try:
        rs = requests.session()
        must = []
        for f in param:
            must.append({'term': {f: param[f]}},)
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 0
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_problem_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        if 'hits' in response:
            return response['hits']['total']['value']
        return 0
    except Exception as e:
        raise e
