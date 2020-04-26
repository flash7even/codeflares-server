import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

from core.category_services import get_category_details

_es_index_problem_category = 'cp_training_problem_category_edges'
_es_index_problem = 'cp_training_problems'
_es_type = '_doc'
_es_size = 100


def get_problem_details(problem_id):
    rs = requests.session()
    search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem, _es_type, problem_id)
    response = rs.get(url=search_url, headers=_http_headers).json()
    if 'found' in response:
        if response['found']:
            data = response['_source']
            return data
    return None


def add_problem_category_dependency(data):
    app.logger.info('add_problem_category_dependency method called')
    rs = requests.session()

    data['created_at'] = int(time.time())
    data['updated_at'] = int(time.time())

    post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_problem_category, _es_type)
    response = rs.post(url=post_url, json=data, headers=_http_headers).json()

    if 'result' in response and response['result'] == 'created':
        app.logger.info('add_problem_category_dependency method completed')
        return response['_id'], 201
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return response, 500


def search_problem_dependency_list(problem_id):
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
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return item_list


def search_problems(param, from_value, size_value):
    query_json = {'query': {'match_all': {}}}
    rs = requests.session()

    must = []
    keyword_fields = ['problem_title', 'oj_name']

    for f in param:
        if f in keyword_fields:
            must.append({'term': {f: param[f]}})
        else:
            must.append({'match': {f: param[f]}})

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
            data['problem_id'] = hit['_id']
            data['category_dependency_list'] = search_problem_dependency_list(data['problem_id'])
            item_list.append(data)
        app.logger.info('Problem search method completed')
        return item_list
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return item_list