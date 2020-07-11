import time
import json
import requests
import string
import re
from flask import current_app as app

_http_headers = {'Content-Type': 'application/json'}

from core.problem_services import get_problem_count_for_category
from core.user_category_edge_services import get_user_category_data
from core.comment_services import get_comment_list, get_comment_count
from core.resource_services import search_resource
from core.vote_services import get_vote_count_list

_es_index_category = 'cfs_categories'
_es_index_category_dependency = 'cfs_category_dependencies'
_es_type = '_doc'
_es_size = 2000
_bulk_size = 25


def create_category_id(category_name):
    regex = re.compile('[%s]' % re.escape(string.punctuation))
    category_id = regex.sub('-', category_name)
    return category_id


def get_category_details(cat_id, user_id = None):
    try:
        rs = requests.session()
        search_url = 'http://{}/{}/{}/{}'.format(app.config['ES_HOST'], _es_index_category, _es_type, cat_id)
        response = rs.get(url=search_url, headers=_http_headers).json()
        if 'found' in response:
            if response['found']:
                data = response['_source']
                data['category_id'] = response['_id']
                data['comment_list'] = get_comment_list(response['_id'])
                data['vote_count'] = get_vote_count_list(response['_id'])
                data['comment_count'] = get_comment_count(response['_id'])
                data['resource_list'] = search_resource({'resource_ref_id': response['_id']}, 0, _es_size)
                data['problem_count'] = 0
                if data['category_root'] == 'root':
                    data['problem_count'] = get_problem_count_for_category({'category_root': data['category_name']})
                else:
                    data['problem_count'] = get_problem_count_for_category({'category_name': data['category_name']})

                if user_id:
                    cat_info = get_user_category_data(user_id, data['category_id'])
                    if cat_info:
                        data['skill_value'] = "{:.2f}".format(float(cat_info['skill_value']))
                        data['skill_title'] = cat_info['skill_title']
                    else:
                        data['skill_value'] = 0
                        data['skill_title'] = "NA"
                return data
        return None
    except Exception as e:
        raise e


def get_category_id_from_name(category_name):
    try:
        rs = requests.session()
        must = [
            {'term': {'category_name': category_name}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = 1
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

        if 'hits' in response:
            for hit in response['hits']['hits']:
                return hit['_id']
        return None
    except Exception as e:
        raise e


def add_category_category_dependency(data):
    try:
        rs = requests.session()

        data['created_at'] = int(time.time())
        data['updated_at'] = int(time.time())

        post_url = 'http://{}/{}/{}'.format(app.config['ES_HOST'], _es_index_category_dependency, _es_type)
        response = rs.post(url=post_url, json=data, headers=_http_headers).json()

        if 'result' in response and response['result'] == 'created':
            return response['_id'], 201
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return response, 500
    except Exception as e:
        raise e


def find_category_dependency_list(category_id_1):
    try:
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
    except Exception as e:
        raise e


def find_dependent_category_list(category_id_2):
    try:
        rs = requests.session()
        must = [
            {'term': {'category_id_2': category_id_2}}
        ]
        query_json = {'query': {'bool': {'must': must}}}
        query_json['size'] = _es_size
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_category_dependency, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                category = hit['_source']
                category.pop('category_id_2', None)
                category['category_info'] = get_category_details(category['category_id_1'])
                category['category_id'] = category['category_id_1']
                category.pop('category_id_1', None)
                item_list.append(category)
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def find_category_dependency_list_for_multiple_categories(category_list):
    try:
        dependent_categories = []
        for category in category_list:
            dep_list = find_category_dependency_list(category)
            for category_data in dep_list:
                category_id = category_data['category_id']
                if category_id not in dependent_categories:
                    dependent_categories.append(category_id)
        return dependent_categories
    except Exception as e:
        raise e


def search_categories(param, from_value, size_value, heavy = False):
    try:
        query_json = {'query': {'match_all': {}}}
        rs = requests.session()

        must = []
        keyword_fields = ['category_title', 'category_root']
        user_id = param.get('user_id', None)
        print('search_categories: body: ', param)
        param.pop('user_id', None)

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

        if 'category_root' not in param:
            if 'query' in query_json and 'bool' in query_json['query']:
                query_json['query']['bool']['must_not'] = [{'term': {'category_root': 'root'}}]
            else:
                query_json = {'query': {'bool': {'must_not': [{'term': {'category_root': 'root'}}]}}}

        query_json['from'] = from_value
        query_json['size'] = size_value
        print('query_json: ', json.dumps(query_json))
        search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_category, _es_type)
        response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()
        # print('response: ', response)
        item_list = []
        if 'hits' in response:
            for hit in response['hits']['hits']:
                category = hit['_source']
                category['category_id'] = hit['_id']
                category['problem_count'] = 0
                category['solve_count'] = 0
                if category['category_root'] == 'root':
                    category['problem_count'] = get_problem_count_for_category({'category_root': category['category_name']})
                else:
                    category['problem_count'] = get_problem_count_for_category({'category_name': category['category_name']})

                if user_id:
                    cat_info = get_user_category_data(user_id, category['category_id'])
                    if cat_info is not None:
                        category['solve_count'] = cat_info.get('solve_count', 0)
                if heavy:
                    category['category_dependency_list'] = find_category_dependency_list(category['category_id'])

                item_list.append(category)
            return item_list
        app.logger.error('Elasticsearch down, response: ' + str(response))
        return item_list
    except Exception as e:
        raise e


def calculate_dependency_percentage():
    try:
        app.logger.info('calculate_dependency_percentage called')
        rs = requests.session()
        category_list = search_categories({}, 0, _es_size)
        for category in category_list:
            category_id = category['category_id']
            must = [
                {'term': {'category_id_1': category_id}}
            ]
            query_json = {'query': {'bool': {'must': must}}}
            query_json['size'] = _es_size
            search_url = 'http://{}/{}/{}/_search'.format(app.config['ES_HOST'], _es_index_category_dependency, _es_type)
            response = rs.post(url=search_url, json=query_json, headers=_http_headers).json()

            dcat_list = []
            total_factor = 0
            if 'hits' in response:
                for hit in response['hits']['hits']:
                    dcat = hit['_source']
                    dcat['id'] = hit['_id']
                    total_factor += float(dcat['dependency_factor'])
                    dcat_list.append(dcat)

            for dcat in dcat_list:
                id = dcat['id']
                dcat.pop('id', None)
                own_factor = float(dcat['dependency_factor'])
                dcat['dependency_percentage'] = own_factor*100.0/total_factor
                url = 'http://{}/{}/{}/{}/'.format(app.config['ES_HOST'], _es_index_category_dependency, _es_type, id)
                rs.put(url=url, json=dcat, headers=_http_headers).json()
        app.logger.info('calculate_dependency_percentage completed')
    except Exception as e:
        raise e
