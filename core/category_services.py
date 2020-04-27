import time
import json
import requests
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}


_es_index_category = 'cp_training_categories'
_es_index_category_dependency = 'cp_training_category_dependencies'
_es_type = '_doc'
_es_size = 500


def get_category_details(cat_id):
    rs = requests.session()
    search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_category, _es_type, cat_id)
    response = rs.get(url=search_url, headers=_http_headers).json()
    if 'found' in response:
        if response['found']:
            data = response['_source']
            app.logger.info('Get category_details method completed')
            return data
    return None


def get_category_id_from_name(category_name):
    rs = requests.session()
    must = [
        {'match': {'category_name': category_name}}
    ]
    query_json = {'query': {'bool': {'must': must}}}
    query_json['size'] = 1
    search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_category, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

    if 'hits' in response:
        for hit in response['hits']['hits']:
            return hit['_id']
    return None


def add_category_category_dependency(data):
    app.logger.info('add_category_category_dependency method called')
    rs = requests.session()

    data['created_at'] = int(time.time())
    data['updated_at'] = int(time.time())

    post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_category_dependency, _es_type)
    response = rs.post(url=post_url, json=data, headers=_http_headers).json()

    if 'result' in response and response['result'] == 'created':
        app.logger.info('add_category_category_dependency method completed')
        return response['_id'], 201
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return response, 500


def search_category_dependency_list(category_id_1):
    rs = requests.session()
    must = [
        {'term': {'category_id_1': category_id_1}}
    ]
    query_json = {'query': {'bool': {'must': must}}}
    query_json['size'] = _es_size
    search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_category_dependency, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
    item_list = []
    if 'hits' in response:
        for hit in response['hits']['hits']:
            category = hit['_source']
            category.pop('category_id_1', None)
            category['category_info'] = get_category_details(category['category_id_2'])
            category['category_id'] = category['category_id_2']
            category.pop('category_id_2', None)
            item_list.append(category)
        return item_list
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return item_list


def search_categories(param, from_value, size_value):
    query_json = {'query': {'match_all': {}}}
    rs = requests.session()

    must = []
    keyword_fields = ['category_title', 'category_root']

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

    must.append({"range": {"category_difficulty": {"gte": minimum_difficulty, "lte": maximum_difficulty}}})

    if len(must) > 0:
        query_json = {'query': {'bool': {'must': must}}}

    query_json['from'] = from_value
    query_json['size'] = size_value
    print('query_json: ', json.dumps(query_json))
    search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_category, _es_type)
    response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
    item_list = []
    if 'hits' in response:
        for hit in response['hits']['hits']:
            category = hit['_source']
            category['category_id'] = hit['_id']
            category['problem_count'] = 100
            category['category_dependency_list'] = search_category_dependency_list(category['category_id'])
            item_list.append(category)
        app.logger.info('Category search method completed')
        return item_list
    app.logger.error('Elasticsearch down, response: ' + str(response))
    return item_list
