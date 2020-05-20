import requests
from flask import current_app as app

from core.problem_category_services import find_problem_dependency_list

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


def get_problem_details(problem_id):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem, _es_type, problem_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['id'] = response['_id']
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
            app.logger.info('Problem search method completed')
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e
